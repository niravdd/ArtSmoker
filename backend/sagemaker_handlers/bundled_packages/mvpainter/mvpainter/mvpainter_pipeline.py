import inspect
from typing import Any, Dict, Optional
from typing import Any, Dict, List, Optional, Tuple, Union

import os
import torch
import numpy as np
from PIL import Image
from collections import OrderedDict

import diffusers
from diffusers.image_processor import VaeImageProcessor
from diffusers.utils.import_utils import is_xformers_available
from diffusers.schedulers import KarrasDiffusionSchedulers
from diffusers.utils.torch_utils import randn_tensor
from diffusers.utils.import_utils import is_xformers_available

from diffusers.models.attention_processor import (
    Attention, 
    AttnProcessor, 
    XFormersAttnProcessor, 
    AttnProcessor2_0
)
from diffusers import (
    AutoencoderKL, 
    DDPMScheduler,
    DiffusionPipeline, 
    EulerAncestralDiscreteScheduler, 
    UNet2DConditionModel, 
    ImagePipelineOutput
)
import transformers
from transformers import (
    CLIPImageProcessor, 
    CLIPTextModel, 
    CLIPTokenizer, 
    CLIPVisionModelWithProjection, 
    CLIPTextModelWithProjection
)

from torchvision.transforms import v2
from torchvision import transforms
from huggingface_hub import hf_hub_download

from PIL import Image
def to_rgb_image(maybe_rgba: Image.Image):
    '''
        convert a PIL.Image to rgb mode with white background
        maybe_rgba: PIL.Image
        return: PIL.Image
    '''
    if maybe_rgba.mode == 'RGB':
        return maybe_rgba
    elif maybe_rgba.mode == 'RGBA':
        rgba = maybe_rgba
        img = np.random.randint(255, 256, size=[rgba.size[1], rgba.size[0], 3], dtype=np.uint8)
        img = Image.fromarray(img, 'RGB')
        img.paste(rgba, mask=rgba.getchannel('A'))
        return img
    else:
        raise ValueError("Unsupported image type.", maybe_rgba.mode)
        
def white_out_background(pil_img, is_gray_fg=True):
    data = pil_img.getdata()
    new_data = []
    #  convert fore-ground white to gray
    for r, g, b, a in data:
        if a < 16: 
            new_data.append((255, 255, 255, 0))  # back-ground to be black
        else:
            is_white = is_gray_fg and (r>235) and (g>235) and (b>235)
            new_r = 235 if is_white else r
            new_g = 235 if is_white else g
            new_b = 235 if is_white else b
            new_data.append((new_r, new_g, new_b, a))
    pil_img.putdata(new_data)
    return pil_img
    
def recenter_img(img, size=512, color=(255,255,255)):
    img = white_out_background(img)
    mask = np.array(img)[..., 3]
    image = np.array(img)[..., :3]
    
    H, W, C = image.shape
    coords = np.nonzero(mask)
    x_min, x_max = coords[0].min(), coords[0].max()
    y_min, y_max = coords[1].min(), coords[1].max()
    h = x_max - x_min
    w = y_max - y_min
    if h == 0 or w == 0: raise ValueError
    roi = image[x_min:x_max, y_min:y_max]

    border_ratio = 0.15 # 0.2
    pad_h = int(h * border_ratio)
    pad_w = int(w * border_ratio)

    result_tmp = np.full((h + pad_h, w + pad_w, C), color, dtype=np.uint8)
    result_tmp[pad_h // 2: pad_h // 2 + h, pad_w // 2: pad_w // 2 + w] = roi

    cur_h, cur_w = result_tmp.shape[:2]
    side = max(cur_h, cur_w)
    result = np.full((side, side, C), color, dtype=np.uint8)
    result[(side-cur_h)//2:(side-cur_h)//2+cur_h, (side-cur_w)//2:(side - cur_w)//2+cur_w,:] = result_tmp
    result = Image.fromarray(result)
    return result.resize((size, size), Image.LANCZOS) if size else result





def scale_latents(latents):   return (latents - 0.22) * 0.75
def unscale_latents(latents): return (latents / 0.75) + 0.22
def scale_image(image):       return (image - 0.5) / 0.5
def scale_image_2(image):     return (image * 0.5) / 0.8
def unscale_image(image):     return (image * 0.5) + 0.5
def unscale_image_2(image):   return (image * 0.8) / 0.5



class ReferenceOnlyAttnProc(torch.nn.Module):
    def __init__(self, chained_proc, enabled=False, name=None):
        super().__init__()
        self.enabled = enabled
        self.chained_proc = chained_proc
        self.name = name

    def __call__(self, attn, hidden_states, encoder_hidden_states=None, attention_mask=None, mode="w", ref_dict=None):
        encoder_hidden_states = hidden_states if encoder_hidden_states is None else encoder_hidden_states
        if self.enabled:
            if   mode == 'w': ref_dict[self.name]   = encoder_hidden_states
            elif mode == 'r': encoder_hidden_states = torch.cat([encoder_hidden_states, ref_dict.pop(self.name)], dim=1)
            else:             raise Exception(f"mode should not be {mode}")
        return self.chained_proc(attn, hidden_states, encoder_hidden_states, attention_mask)


class RefOnlyNoisedUNet(torch.nn.Module):
    def __init__(self, unet, train_scheduler,val_scheduler = None) -> None:
        super().__init__()
        self.unet = unet
        self.train_sched = train_scheduler
        if val_scheduler == None:
            self.val_sched = train_scheduler

        unet_attn_procs = dict()
        for name, _ in unet.attn_processors.items():
            if torch.__version__ >= '2.0': default_attn_proc = AttnProcessor2_0()
            elif is_xformers_available():  default_attn_proc = XFormersAttnProcessor()
            else:                          default_attn_proc = AttnProcessor()
            unet_attn_procs[name] = ReferenceOnlyAttnProc(
                default_attn_proc, enabled=name.endswith("attn1.processor"), name=name
            )
        unet.set_attn_processor(unet_attn_procs)

    def __getattr__(self, name: str):
        try:
            return super().__getattr__(name)
        except AttributeError:
            return getattr(self.unet, name)

    def forward(
        self,
        sample: torch.FloatTensor,
        timestep: Union[torch.Tensor, float, int],
        encoder_hidden_states: torch.Tensor,
        cross_attention_kwargs: Optional[Dict[str, Any]] = None,
        class_labels: Optional[torch.Tensor] = None,
        down_block_res_samples: Optional[Tuple[torch.Tensor]] = None,
        mid_block_res_sample: Optional[Tuple[torch.Tensor]] = None,
        added_cond_kwargs: Optional[Dict[str, torch.Tensor]] = None,
        return_dict: bool = True,
        is_training = False,
        **kwargs
    ):

        dtype = self.unet.dtype

        # cond_lat add same level noise
        cond_lat = cross_attention_kwargs['cond_lat']
        noise = torch.randn_like(cond_lat)
        if is_training:
            noisy_cond_lat = self.train_sched.add_noise(cond_lat, noise, timestep.reshape(-1))
            noisy_cond_lat = self.train_sched.scale_model_input(noisy_cond_lat, timestep.reshape(-1))
        else:
            noisy_cond_lat = self.val_sched.add_noise(cond_lat, noise, timestep.reshape(-1))
            noisy_cond_lat = self.val_sched.scale_model_input(noisy_cond_lat, timestep.reshape(-1))

        ref_dict = {}
        
        _ = self.unet(
            noisy_cond_lat, 
            timestep, 
            encoder_hidden_states = encoder_hidden_states, 
            class_labels = class_labels,
            cross_attention_kwargs = dict(mode="w", ref_dict=ref_dict),
            added_cond_kwargs = added_cond_kwargs,
            return_dict = return_dict,
            **kwargs
        )

        res = self.unet(
            sample, 
            timestep, 
            encoder_hidden_states, 
            class_labels=class_labels,
            cross_attention_kwargs = dict(mode="r", ref_dict=ref_dict),
            down_block_additional_residuals = [
                sample.to(dtype=dtype) for sample in down_block_res_samples
            ] if down_block_res_samples is not None else None,
            mid_block_additional_residual = (
                mid_block_res_sample.to(dtype=dtype) 
                if mid_block_res_sample is not None else None),
            added_cond_kwargs = added_cond_kwargs,
            return_dict = return_dict,
            **kwargs
        )
        return res
        
class SuperNet(torch.nn.Module):
    def __init__(self, state_dict: Dict[str, torch.Tensor]):
        super().__init__()
        state_dict = OrderedDict((k, state_dict[k]) for k in sorted(state_dict.keys()))
        self.layers = torch.nn.ModuleList(state_dict.values())
        self.mapping = dict(enumerate(state_dict.keys()))
        self.rev_mapping = {v: k for k, v in enumerate(state_dict.keys())}

        # .processor for unet, .self_attn for text encoder
        self.split_keys = [".processor", ".self_attn"]

        # we add a hook to state_dict() and load_state_dict() so that the
        # naming fits with `unet.attn_processors`
        def map_to(module, state_dict, *args, **kwargs):
            new_state_dict = {}
            for key, value in state_dict.items():
                num = int(key.split(".")[1])  # 0 is always "layers"
                new_key = key.replace(f"layers.{num}", module.mapping[num])
                new_state_dict[new_key] = value

            return new_state_dict

        def remap_key(key, state_dict):
            for k in self.split_keys:
                if k in key:
                    return key.split(k)[0] + k
            return key.split('.')[0]

        def map_from(module, state_dict, *args, **kwargs):
            all_keys = list(state_dict.keys())
            for key in all_keys:
                replace_key = remap_key(key, state_dict)
                new_key = key.replace(replace_key, f"layers.{module.rev_mapping[replace_key]}")
                state_dict[new_key] = state_dict[key]
                del state_dict[key]

        self._register_state_dict_hook(map_to)
        self._register_load_state_dict_pre_hook(map_from, with_module=True)

class DepthControlUNet(torch.nn.Module):
    def __init__(self, unet: RefOnlyNoisedUNet, controlnet: Optional[diffusers.ControlNetModel] = None,
                 conditioning_scale=1.0) -> None:
        super().__init__()
        self.unet = unet
        if controlnet is None:
            self.controlnet = diffusers.ControlNetModel.from_unet(unet.unet)
        else:
            self.controlnet = controlnet
        DefaultAttnProc = AttnProcessor2_0
        if is_xformers_available():
            DefaultAttnProc = XFormersAttnProcessor
        self.controlnet.set_attn_processor(DefaultAttnProc())


        self.conditioning_scale = conditioning_scale

    def __getattr__(self, name: str):
        try:
            return super().__getattr__(name)
        except AttributeError:
            return getattr(self.unet, name)

    def forward(self, sample, timestep, encoder_hidden_states, 
                class_labels=None, 
                *args, 
                cross_attention_kwargs: dict,
                added_cond_kwargs: dict,
                is_training = False,
                **kwargs):
        cross_attention_kwargs = dict(cross_attention_kwargs)
        control_depth = cross_attention_kwargs.pop('control_depth')
        control_type =  cross_attention_kwargs.pop('control_type')
        added_cond_kwargs['control_type'] = control_type
        controlnet_cond_list = [control_depth]
        
        

        if 'control_depth_2' in cross_attention_kwargs:
            control_depth_2 =  cross_attention_kwargs.pop('control_depth_2')
            controlnet_cond_list.append(control_depth_2)



        down_block_res_samples, mid_block_res_sample = self.controlnet(
            sample,
            timestep,
            encoder_hidden_states=encoder_hidden_states,
            controlnet_cond_list=controlnet_cond_list,
            conditioning_scale=self.conditioning_scale,
            added_cond_kwargs = added_cond_kwargs,
            return_dict=False,
        )
            
        return self.unet(
            sample,
            timestep,
            encoder_hidden_states=encoder_hidden_states,
            down_block_res_samples=down_block_res_samples,
            mid_block_res_sample=mid_block_res_sample,
            cross_attention_kwargs=cross_attention_kwargs,
            added_cond_kwargs = added_cond_kwargs,
            is_training = is_training,
        )


class MVPainter_Pipeline(diffusers.DiffusionPipeline):
    def __init__(
        self,
        vae: AutoencoderKL,
        unet: UNet2DConditionModel,
        scheduler: KarrasDiffusionSchedulers,
        feature_extractor_vae: CLIPImageProcessor,
        vision_processor: CLIPImageProcessor,
        vision_encoder: CLIPVisionModelWithProjection,
        vision_encoder_2: CLIPVisionModelWithProjection,
        ramping_coefficients: Optional[list] = None,
        add_watermarker: Optional[bool] = None,
        safety_checker = None,
    ):
        DiffusionPipeline.__init__(self)

        self.register_modules(
            vae=vae, unet=unet, scheduler=scheduler, safety_checker=None, feature_extractor_vae=feature_extractor_vae,
            vision_processor=vision_processor, vision_encoder=vision_encoder, vision_encoder_2=vision_encoder_2, 
        )
        self.register_to_config( ramping_coefficients = ramping_coefficients)
        self.vae_scale_factor = 2 ** (len(self.vae.config.block_out_channels) - 1)
        self.image_processor = VaeImageProcessor(vae_scale_factor=self.vae_scale_factor)
        self.default_sample_size = self.unet.config.sample_size 
        self.watermark = None 
        self.prepare_init = False



        self.depth_transforms_multi = transforms.Compose([
        transforms.ToTensor(),
        # transforms.Normalize([0.5], [0.5])

    ])


    def prepare(self):
        assert isinstance(self.unet, UNet2DConditionModel), "unet should be UNet2DConditionModel"
        self.unet = RefOnlyNoisedUNet(self.unet, self.scheduler).eval()
        self.prepare_init = True

    def add_controlnet(self, controlnet: Optional[diffusers.ControlNetModel] = None, conditioning_scale=1.0):
        self.prepare()
        self.unet = DepthControlUNet(self.unet, controlnet, conditioning_scale)
        return SuperNet(OrderedDict([('controlnet', self.unet.controlnet)]))
    

    def encode_image(self, image: torch.Tensor, scale_factor: bool = False):
        latent = self.vae.encode(image).latent_dist.sample()
        return (latent * self.vae.config.scaling_factor) if scale_factor else latent
    def get_prompt_embeds_train(self,is_drop,cond_image):

        device = self._execution_device
        here = dict(device=self.vae.device, dtype=self.vae.dtype)

        image_pil = [v2.functional.to_pil_image(cond_image[i]) for i in range(cond_image.shape[0])]
        image_clip = self.vision_processor(images=image_pil, return_tensors="pt").pixel_values.to(**here)

        # hw: get visual global embedding using clip
        global_embeds_1 = self.vision_encoder(image_clip, output_hidden_states=False).image_embeds.unsqueeze(-2)
        global_embeds_2 = self.vision_encoder_2(image_clip, output_hidden_states=False).image_embeds.unsqueeze(-2)
        global_embeds = torch.concat([global_embeds_1, global_embeds_2], dim=-1)


        ramp = global_embeds.new_tensor(self.config.ramping_coefficients).unsqueeze(-1)
        prompt_embeds = self.uc_text_emb.to(**here)

        prompt_embeds = prompt_embeds + global_embeds * ramp


        if is_drop:
            negative_prompt_embeds = torch.zeros_like(prompt_embeds)
            prompt_embeds = negative_prompt_embeds
        prompt_embeds = prompt_embeds.to(device)

        return prompt_embeds
    


    def get_added_cond_kwargs_train(self,batch_size,is_drop,crops_coords_top_left: Tuple[int, int] = (0, 0),):
        width, height = 512 * 2,  512 * 3
        target_size = original_size = (height, width)
        text_encoder_projection_dim = 1280          
        num_images_per_prompt = 1


        device = self._execution_device
        here = dict(device=self.vae.device, dtype=self.vae.dtype)
        pooled_prompt_embeds =  self.uc_text_emb_2.to(**here)
        add_text_embeds = pooled_prompt_embeds

        add_time_ids = self._get_add_time_ids(
            original_size,
            crops_coords_top_left,
            target_size,
            dtype=self.vae.dtype,
            text_encoder_projection_dim=text_encoder_projection_dim,
        )
        negative_add_time_ids = add_time_ids

        if is_drop:
            negative_pooled_prompt_embeds = torch.zeros_like(pooled_prompt_embeds)
            add_text_embeds = negative_pooled_prompt_embeds
            add_time_ids = negative_add_time_ids
        add_text_embeds = add_text_embeds.to(device)
        add_time_ids = add_time_ids.to(device).repeat(batch_size * num_images_per_prompt, 1)

        added_cond_kwargs = {"text_embeds": add_text_embeds, "time_ids": add_time_ids}

        return added_cond_kwargs


    # Copied from diffusers.pipelines.stable_diffusion.pipeline_stable_diffusion.StableDiffusionPipeline.prepare_latents
    def prepare_latents(self, batch_size, num_channels_latents, height, width, dtype, device, generator, latents=None):
        shape = (
            batch_size,
            num_channels_latents,
            int(height) // self.vae_scale_factor,
            int(width) // self.vae_scale_factor,
        )
        if isinstance(generator, list) and len(generator) != batch_size:
            raise ValueError(
                f"You have passed a list of generators of length {len(generator)}, but requested an effective batch"
                f" size of {batch_size}. Make sure the batch size matches the length of the generators."
            )

        if latents is None:
            latents = randn_tensor(shape, generator=generator, device=device, dtype=dtype) 
        else:
            latents = latents.to(device)

        # scale the initial noise by the standard deviation required by the scheduler
        latents = latents * self.scheduler.init_noise_sigma
        return latents

    def _get_add_time_ids(
        self, original_size, crops_coords_top_left, target_size, dtype, text_encoder_projection_dim=None
    ):
        add_time_ids = list(original_size + crops_coords_top_left + target_size)

        passed_add_embed_dim = (
            self.unet.config.addition_time_embed_dim * len(add_time_ids) + text_encoder_projection_dim
        )
        expected_add_embed_dim = self.unet.add_embedding.linear_1.in_features

        if expected_add_embed_dim != passed_add_embed_dim:
            raise ValueError(
                f"Model expects an added time embedding vector of length {expected_add_embed_dim}, " \
                f"but a vector of {passed_add_embed_dim} was created. The model has an incorrect config." \
                f" Please check `unet.config.time_embedding_type` and `text_encoder_2.config.projection_dim`."
            )

        add_time_ids = torch.tensor([add_time_ids], dtype=dtype)
        return add_time_ids
    

    def prepare_extra_step_kwargs(self, generator, eta):
        # prepare extra kwargs for the scheduler step, since not all schedulers have the same signature
        # eta (η) is only used with the DDIMScheduler, it will be ignored for other schedulers.
        # eta corresponds to η in DDIM paper: https://arxiv.org/abs/2010.02502
        # and should be between [0, 1]

        accepts_eta = "eta" in set(inspect.signature(self.scheduler.step).parameters.keys())
        extra_step_kwargs = {}
        if accepts_eta:  extra_step_kwargs["eta"] = eta

        # check if the scheduler accepts generator
        accepts_generator = "generator" in set(inspect.signature(self.scheduler.step).parameters.keys())
        if accepts_generator: extra_step_kwargs["generator"] = generator
        return extra_step_kwargs

    @property
    def guidance_scale(self):
        return self._guidance_scale

    @property
    def interrupt(self):
        return self._interrupt

    @property
    def do_classifier_free_guidance(self):
        return self._guidance_scale > 1 and self.unet.config.time_cond_proj_dim is None
        
    @torch.no_grad()
    def __call__(
        self,
        image: Image.Image = None,
        guidance_scale = 2.0,
        output_type: Optional[str] = "pil",
        num_inference_steps: int = 50,
        return_dict: bool = True,
        eta: float = 0.0,
        generator: Optional[Union[torch.Generator, List[torch.Generator]]] = None,
        crops_coords_top_left: Tuple[int, int] = (0, 0),
        cross_attention_kwargs: Optional[Dict[str, Any]] = None,
        latent: torch.Tensor = None,
        guidance_curve = None,
        depth_image: Image.Image = None, # 用于controlnet
        depth_image_2: Image.Image = None,
        **kwargs
    ):
        if not self.prepare_init:
            self.prepare()

        here = dict(device=self.vae.device, dtype=self.vae.dtype)
            
        batch_size = 1
        num_images_per_prompt = 1
        width, height = 512 * 2,  512 * 3
        target_size = original_size = (height, width)

        self._guidance_scale = guidance_scale
        self._cross_attention_kwargs = cross_attention_kwargs
        self._interrupt = False

        device = self._execution_device

        # Prepare timesteps
        self.scheduler.set_timesteps(num_inference_steps, device=device)
        timesteps = self.scheduler.timesteps
        
        # Prepare latent variables
        num_channels_latents = self.unet.config.in_channels
        latents = self.prepare_latents(
            batch_size * num_images_per_prompt,
            num_channels_latents,
            height,
            width,
            self.vae.dtype,
            device,
            generator,
            latents=latent,
        )
        
        # Prepare extra step kwargs. TODO: Logic should ideally just be moved out of the pipeline
        extra_step_kwargs = self.prepare_extra_step_kwargs(generator, eta)


        # Prepare added time ids & embeddings
        # text_encoder_projection_dim = 1280     
        # add_time_ids = self._get_add_time_ids(
        #     original_size,
        #     crops_coords_top_left,
        #     target_size,
        #     dtype=self.vae.dtype,
        #     text_encoder_projection_dim=text_encoder_projection_dim,
        # )
        add_time_ids=torch.tensor([[1536., 1024.,    0.,    0., 1536., 1024.]],dtype=self.unet.dtype,device=self.unet.device)
        print("add_time_ids:",add_time_ids)
        negative_add_time_ids = add_time_ids


        # 处理control image
        if depth_image is not None and hasattr(self.unet, "controlnet"):
            depth_image = to_rgb_image(depth_image)
            depth_image = self.depth_transforms_multi(depth_image).to(
                            device=self.unet.controlnet.device, dtype=self.unet.controlnet.dtype
                        )
            depth_image = depth_image.unsqueeze(0).repeat(2,1,1,1)
            if depth_image_2 is not None:
                depth_image_2 = to_rgb_image(depth_image_2)
                depth_image_2 = self.depth_transforms_multi(depth_image_2).to(
                device=self.unet.controlnet.device, dtype=self.unet.controlnet.dtype
                )
                depth_image_2 = depth_image_2.unsqueeze(0).repeat(2,1,1,1)
                # depth_image = torch.stack((depth_image,depth_image_2),dim = 0)
                # depth_image = torch.cat((depth_image,depth_image_2),dim=0)
    
           




        # hw: preprocess
        cond_image = recenter_img(image)
        cond_image = to_rgb_image(image)
        image_vae = self.feature_extractor_vae(images=cond_image, return_tensors="pt").pixel_values.to(**here)
        image_clip = self.vision_processor(images=cond_image, return_tensors="pt").pixel_values.to(**here)

        # hw: get cond_lat from cond_img using vae
        cond_lat = self.encode_image(image_vae, scale_factor=False)
        negative_lat = self.encode_image(torch.zeros_like(image_vae), scale_factor=False) 
        cond_lat = torch.cat([negative_lat, cond_lat])

        # hw: get visual global embedding using clip
        global_embeds_1 = self.vision_encoder(image_clip, output_hidden_states=False).image_embeds.unsqueeze(-2)
        global_embeds_2 = self.vision_encoder_2(image_clip, output_hidden_states=False).image_embeds.unsqueeze(-2)
        global_embeds = torch.concat([global_embeds_1, global_embeds_2], dim=-1)
        print("global_embeds:",global_embeds.shape)
        ramp = global_embeds.new_tensor(self.config.ramping_coefficients).unsqueeze(-1)
        print("ramp:",global_embeds.shape)
        prompt_embeds = self.uc_text_emb.to(**here)
        pooled_prompt_embeds =  self.uc_text_emb_2.to(**here)
        
        prompt_embeds = prompt_embeds + global_embeds * ramp
        add_text_embeds = pooled_prompt_embeds
        
        if self.do_classifier_free_guidance:
            negative_prompt_embeds = torch.zeros_like(prompt_embeds)
            negative_pooled_prompt_embeds = torch.zeros_like(pooled_prompt_embeds)
            prompt_embeds = torch.cat([negative_prompt_embeds, prompt_embeds], dim=0)
            add_text_embeds = torch.cat([negative_pooled_prompt_embeds, add_text_embeds], dim=0)
            add_time_ids = torch.cat([negative_add_time_ids, add_time_ids], dim=0)

        prompt_embeds = prompt_embeds.to(device)
        add_text_embeds = add_text_embeds.to(device)
        add_time_ids = add_time_ids.to(device).repeat(batch_size * num_images_per_prompt, 1)

        # Denoising loop
        num_warmup_steps = max(len(timesteps) - num_inference_steps * self.scheduler.order, 0)
        timestep_cond = None
        self._num_timesteps = len(timesteps)

        if guidance_curve is None:
            guidance_curve = lambda t: guidance_scale
        
        with self.progress_bar(total=num_inference_steps) as progress_bar:
            for i, t in enumerate(timesteps):
                if self.interrupt:
                    continue
                    
                 # expand the latents if we are doing classifier free guidance
                latent_model_input = torch.cat([latents] * 2) if self.do_classifier_free_guidance else latents

                latent_model_input = self.scheduler.scale_model_input(latent_model_input, t)

                # predict the noise residual
                added_cond_kwargs = {"text_embeds": add_text_embeds, "time_ids": add_time_ids}
                
                if hasattr(self.unet, "controlnet"):
                    
                    cross_attention_kwargs = {'cond_lat':cond_lat,'control_depth':depth_image}
                    # import pdb;pdb.set_trace()
                    # for v8:
                    cross_attention_kwargs['control_depth_2'] = depth_image_2
                    cross_attention_kwargs['control_type'] = torch.Tensor([1,1]).to(depth_image).unsqueeze(0).repeat(2,1)
                else:
                    cross_attention_kwargs = {'cond_lat':cond_lat}
                noise_pred = self.unet(
                    latent_model_input,
                    t,
                    encoder_hidden_states=prompt_embeds,
                    timestep_cond=timestep_cond,
                    cross_attention_kwargs=cross_attention_kwargs,
                    added_cond_kwargs=added_cond_kwargs,
                    return_dict=False,
                )[0]

                # perform guidance
                
                # cur_guidance_scale = self.guidance_scale
                cur_guidance_scale = guidance_curve(t)  # 1.5 + 2.5 * ((t/1000)**2)
                
                if self.do_classifier_free_guidance:
                    noise_pred_uncond, noise_pred_text = noise_pred.chunk(2)
                    noise_pred = noise_pred_uncond + cur_guidance_scale * (noise_pred_text - noise_pred_uncond)

                    # cur_guidance_scale_topleft = (cur_guidance_scale - 1.0) * 4 + 1.0
                    # noise_pred_top_left = noise_pred_uncond + 
                    #    cur_guidance_scale_topleft * (noise_pred_text - noise_pred_uncond)
                    # _, _, h, w = noise_pred.shape
                    # noise_pred[:, :, :h//3, :w//2] = noise_pred_top_left[:, :, :h//3, :w//2]

                # compute the previous noisy sample x_t -> x_t-1
                latents_dtype = latents.dtype
                latents = self.scheduler.step(noise_pred, t, latents, **extra_step_kwargs, return_dict=False)[0]

                # call the callback, if provided
                if i == len(timesteps) - 1 or ((i + 1) > num_warmup_steps and (i + 1) % self.scheduler.order == 0):
                    progress_bar.update()
        
        latents = unscale_latents(latents)

        if output_type=="latent":
            image = latents
        else:
            image = self.vae.decode(latents / self.vae.config.scaling_factor, return_dict=False)[0]
            image = unscale_image(unscale_image_2(image)).clamp(0, 1)
            image = [
                Image.fromarray((image[0]*255+0.5).clamp_(0, 255).permute(1, 2, 0).cpu().numpy().astype("uint8")),
                # self.image_processor.postprocess(image, output_type=output_type)[0],
                cond_image.resize((512, 512))
            ]

        return image

    def save_pretrained(self, save_directory):
        # uc_text_emb.pt and uc_text_emb_2.pt are inferenced and saved in advance
        super().save_pretrained(save_directory)
        torch.save(self.uc_text_emb, os.path.join(save_directory, "uc_text_emb.pt"))
        torch.save(self.uc_text_emb_2, os.path.join(save_directory, "uc_text_emb_2.pt"))

    @classmethod
    def from_pretrained(cls, pretrained_model_name_or_path, *model_args, **kwargs):
        # uc_text_emb.pt and uc_text_emb_2.pt are inferenced and saved in advance
        pipeline = super().from_pretrained(pretrained_model_name_or_path, *model_args, **kwargs)
        uc_text_emb_path = hf_hub_download(repo_id="shaomq/MVPainter",filename="uc_text_emb.pt")
        uc_text_emb_2_path = hf_hub_download(repo_id="shaomq/MVPainter",filename="uc_text_emb_2.pt")

        # pipeline.uc_text_emb = torch.load(os.path.join(pretrained_model_name_or_path, "uc_text_emb.pt"))
        # pipeline.uc_text_emb_2 = torch.load(os.path.join(pretrained_model_name_or_path, "uc_text_emb_2.pt"))
        pipeline.uc_text_emb = torch.load(uc_text_emb_path)
        pipeline.uc_text_emb_2 = torch.load(uc_text_emb_2_path)
        return pipeline
