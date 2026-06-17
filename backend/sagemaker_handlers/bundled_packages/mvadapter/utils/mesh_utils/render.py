import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Union

import numpy as np
import nvdiffrast.torch as dr
import torch
import torch.nn.functional as F
import trimesh
from PIL import Image
from torch import BoolTensor, FloatTensor

from .camera import Camera
from .mesh import TexturedMesh
from .utils import get_clip_space_position, transform_points_homo


@dataclass
class RenderOutput:
    attr: Optional[torch.FloatTensor] = None
    mask: Optional[torch.BoolTensor] = None
    depth: Optional[torch.FloatTensor] = None
    normal: Optional[torch.FloatTensor] = None
    tangent: Optional[torch.FloatTensor] = None
    pos: Optional[torch.FloatTensor] = None


class NVDiffRastContextWrapper:
    def __init__(self, device: str, context_type: str = "gl"):
        if context_type == "gl":
            self.ctx = dr.RasterizeGLContext(device=device)
        elif context_type == "cuda":
            self.ctx = dr.RasterizeCudaContext(device=device)
        else:
            raise NotImplementedError

    def rasterize(self, pos, tri, resolution, ranges=None, grad_db=True):
        """
        Rasterize triangles.

        All input tensors must be contiguous and reside in GPU memory except for the ranges tensor that, if specified, has to reside in CPU memory. The output tensors will be contiguous and reside in GPU memory.

        Arguments:
        glctx	Rasterizer context of type RasterizeGLContext or RasterizeCudaContext.
        pos	Vertex position tensor with dtype torch.float32. To enable range mode, this tensor should have a 2D shape [num_vertices, 4]. To enable instanced mode, use a 3D shape [minibatch_size, num_vertices, 4].
        tri	Triangle tensor with shape [num_triangles, 3] and dtype torch.int32.
        resolution	Output resolution as integer tuple (height, width).
        ranges	In range mode, tensor with shape [minibatch_size, 2] and dtype torch.int32, specifying start indices and counts into tri. Ignored in instanced mode.
        grad_db	Propagate gradients of image-space derivatives of barycentrics into pos in backward pass. Ignored if using an OpenGL context that was not configured to output image-space derivatives.
        Returns:
        A tuple of two tensors. The first output tensor has shape [minibatch_size, height, width, 4] and contains the main rasterizer output in order (u, v, z/w, triangle_id). If the OpenGL context was configured to output image-space derivatives of barycentrics, the second output tensor will also have shape [minibatch_size, height, width, 4] and contain said derivatives in order (du/dX, du/dY, dv/dX, dv/dY). Otherwise it will be an empty tensor with shape [minibatch_size, height, width, 0].
        """
        return dr.rasterize(
            self.ctx,
            pos.float().contiguous(),
            tri.int().contiguous(),
            resolution,
            ranges,
            grad_db,
        )

    def interpolate(self, attr, rast, tri, rast_db=None, diff_attrs=None):
        """
        Interpolate vertex attributes.

        All input tensors must be contiguous and reside in GPU memory. The output tensors will be contiguous and reside in GPU memory.

        Arguments:
        attr	Attribute tensor with dtype torch.float32. Shape is [num_vertices, num_attributes] in range mode, or [minibatch_size, num_vertices, num_attributes] in instanced mode. Broadcasting is supported along the minibatch axis.
        rast	Main output tensor from rasterize().
        tri	Triangle tensor with shape [num_triangles, 3] and dtype torch.int32.
        rast_db	(Optional) Tensor containing image-space derivatives of barycentrics, i.e., the second output tensor from rasterize(). Enables computing image-space derivatives of attributes.
        diff_attrs	(Optional) List of attribute indices for which image-space derivatives are to be computed. Special value 'all' is equivalent to list [0, 1, ..., num_attributes - 1].
        Returns:
        A tuple of two tensors. The first output tensor contains interpolated attributes and has shape [minibatch_size, height, width, num_attributes]. If rast_db and diff_attrs were specified, the second output tensor contains the image-space derivatives of the selected attributes and has shape [minibatch_size, height, width, 2 * len(diff_attrs)]. The derivatives of the first selected attribute A will be on channels 0 and 1 as (dA/dX, dA/dY), etc. Otherwise, the second output tensor will be an empty tensor with shape [minibatch_size, height, width, 0].
        """
        return dr.interpolate(
            attr.float().contiguous(), rast, tri.int().contiguous(), rast_db, diff_attrs
        )

    def texture(
        self,
        tex,
        uv,
        uv_da=None,
        mip_level_bias=None,
        mip=None,
        filter_mode="auto",
        boundary_mode="wrap",
        max_mip_level=None,
    ):
        """
        Perform texture sampling.

        All input tensors must be contiguous and reside in GPU memory. The output tensor will be contiguous and reside in GPU memory.

        Arguments:
        tex	Texture tensor with dtype torch.float32. For 2D textures, must have shape [minibatch_size, tex_height, tex_width, tex_channels]. For cube map textures, must have shape [minibatch_size, 6, tex_height, tex_width, tex_channels] where tex_width and tex_height are equal. Note that boundary_mode must also be set to 'cube' to enable cube map mode. Broadcasting is supported along the minibatch axis.
        uv	Tensor containing per-pixel texture coordinates. When sampling a 2D texture, must have shape [minibatch_size, height, width, 2]. When sampling a cube map texture, must have shape [minibatch_size, height, width, 3].
        uv_da	(Optional) Tensor containing image-space derivatives of texture coordinates. Must have same shape as uv except for the last dimension that is to be twice as long.
        mip_level_bias	(Optional) Per-pixel bias for mip level selection. If uv_da is omitted, determines mip level directly. Must have shape [minibatch_size, height, width].
        mip	(Optional) Preconstructed mipmap stack from a texture_construct_mip() call, or a list of tensors specifying a custom mipmap stack. When specifying a custom mipmap stack, the tensors in the list must follow the same format as tex except for width and height that must follow the usual rules for mipmap sizes. The base level texture is still supplied in tex and must not be included in the list. Gradients of a custom mipmap stack are not automatically propagated to base texture but the mipmap tensors will receive gradients of their own. If a mipmap stack is not specified but the chosen filter mode requires it, the mipmap stack is constructed internally and discarded afterwards.
        filter_mode	Texture filtering mode to be used. Valid values are 'auto', 'nearest', 'linear', 'linear-mipmap-nearest', and 'linear-mipmap-linear'. Mode 'auto' selects 'linear' if neither uv_da or mip_level_bias is specified, and 'linear-mipmap-linear' when at least one of them is specified, these being the highest-quality modes possible depending on the availability of the image-space derivatives of the texture coordinates or direct mip level information.
        boundary_mode	Valid values are 'wrap', 'clamp', 'zero', and 'cube'. If tex defines a cube map, this must be set to 'cube'. The default mode 'wrap' takes fractional part of texture coordinates. Mode 'clamp' clamps texture coordinates to the centers of the boundary texels. Mode 'zero' virtually extends the texture with all-zero values in all directions.
        max_mip_level	If specified, limits the number of mipmaps constructed and used in mipmap-based filter modes.
        Returns:
        A tensor containing the results of the texture sampling with shape [minibatch_size, height, width, tex_channels]. Cube map fetches with invalid uv coordinates (e.g., zero vectors) output all zeros and do not propagate gradients.
        """
        return dr.texture(
            tex.float(),
            uv.float(),
            uv_da,
            mip_level_bias,
            mip,
            filter_mode,
            boundary_mode,
            max_mip_level,
        )

    def antialias(
        self, color, rast, pos, tri, topology_hash=None, pos_gradient_boost=1.0
    ):
        """
        Perform antialiasing.

        All input tensors must be contiguous and reside in GPU memory. The output tensor will be contiguous and reside in GPU memory.

        Note that silhouette edge determination is based on vertex indices in the triangle tensor. For it to work properly, a vertex belonging to multiple triangles must be referred to using the same vertex index in each triangle. Otherwise, nvdiffrast will always classify the adjacent edges as silhouette edges, which leads to bad performance and potentially incorrect gradients. If you are unsure whether your data is good, check which pixels are modified by the antialias operation and compare to the example in the documentation.

        Arguments:
        color	Input image to antialias with shape [minibatch_size, height, width, num_channels].
        rast	Main output tensor from rasterize().
        pos	Vertex position tensor used in the rasterization operation.
        tri	Triangle tensor used in the rasterization operation.
        topology_hash	(Optional) Preconstructed topology hash for the triangle tensor. If not specified, the topology hash is constructed internally and discarded afterwards.
        pos_gradient_boost	(Optional) Multiplier for gradients propagated to pos.
        Returns:
        A tensor containing the antialiased image with the same shape as color input tensor.
        """
        return dr.antialias(
            color.float(),
            rast,
            pos.float(),
            tri.int(),
            topology_hash,
            pos_gradient_boost,
        )


class KaolinContextWrapper:
    """Apache-2.0 (commercial-safe) drop-in for NVDiffRastContextWrapper, backed
    by kaolin.render.mesh (NOT kaolin/non_commercial). nvdiffrast is NVIDIA
    Source-Code-Licensed (non-commercial); this lets the bake ship commercially.

    Contract: produces the SAME nvdiffrast-format `rast` tensor
    [mb, H, W, 4] = (u, v, z/w, triangle_id_plus_1) — so all downstream code
    (rast[...,0/1/3] reads in warp.py, mask = rast[...,3] > 0, and repeated
    ctx.interpolate(attr, rast, tri) calls) works UNCHANGED. We recover the
    per-pixel barycentrics from Kaolin via the one-hot-feature trick (Kaolin
    fuses rasterize+interpolate and doesn't expose barycentrics directly).
    """

    def __init__(self, device: str = "cuda", context_type: str = "cuda"):
        self.device = device
        import kaolin as _kal  # noqa: F401 — import here so the dep is lazy
        self._kal = _kal

    def rasterize(self, pos, tri, resolution, ranges=None, grad_db=True):
        # pos: clip-space [V,4] or [mb,V,4]; tri: [F,3] int. resolution=(H,W).
        H, W = int(resolution[0]), int(resolution[1])
        if pos.dim() == 2:
            pos = pos[None]
        mb = pos.shape[0]
        tri_i = tri.long().contiguous()
        F_ = tri_i.shape[0]
        dev = pos.device
        rasterize = self._kal.render.mesh.rasterize
        rast_list = []
        eye3 = torch.eye(3, device=dev, dtype=torch.float32)
        for b in range(mb):
            p = pos[b]
            ndc = p[:, :3] / p[:, 3:4].clamp(min=1e-8)   # perspective divide
            img_xy = ndc[:, :2].clone()
            img_xy[:, 1] = -img_xy[:, 1]                  # OpenGL y-up → image y-down
            z = ndc[:, 2]
            fv_image = img_xy[tri_i][None]                # (1,F,3,2)
            fv_z = z[tri_i][None]                         # (1,F,3)
            # One-hot corner features → rasterized output IS the barycentric map.
            bary_feat = eye3.expand(1, F_, 3, 3).contiguous()  # (1,F,3,3)
            (bary,), face_idx = rasterize(
                H, W, fv_z, fv_image, [bary_feat], backend="cuda")
            # bary: (1,H,W,3) weights (w0,w1,w2); face_idx: (1,H,W) 0-indexed, -1 empty
            valid = (face_idx >= 0)                       # (1,H,W)
            u = bary[..., 1]                              # nvdiffrast u = weight of v1
            v = bary[..., 2]                              # nvdiffrast v = weight of v2
            tri_id_p1 = (face_idx + 1).to(torch.float32)  # 1-indexed, 0 = empty
            # z/w channel: interpolate ndc z by barycentric (only the mask + the
            # raw value matter downstream; sign/scale isn't consumed for the bake).
            zw = (bary * fv_z[0][face_idx.clamp(min=0)]).sum(-1)  # (1,H,W)
            zw = torch.where(valid, zw, torch.zeros_like(zw))
            rast_b = torch.stack([u, v, zw, tri_id_p1], dim=-1)   # (1,H,W,4)
            rast_b = torch.where(valid[..., None], rast_b,
                                 torch.zeros_like(rast_b))         # empty → all 0
            rast_list.append(rast_b)
        rast = torch.cat(rast_list, dim=0)                 # (mb,H,W,4)
        # Stash for interpolate() — it needs the bary+face_idx, recoverable from rast.
        empty_db = torch.zeros((mb, H, W, 0), device=dev, dtype=torch.float32)
        return rast, empty_db

    def interpolate(self, attr, rast, tri, rast_db=None, diff_attrs=None):
        # Reconstruct from the nvdiffrast-format rast: tri_id, barycentric (u,v,w0).
        tri_i = tri.long()
        if attr.dim() == 3:   # [mb,V,C] → use batch 0's vertex set (matches usage)
            attr0 = attr[0]
        else:
            attr0 = attr
        face_id = rast[..., 3].long() - 1                  # (mb,H,W), -1 empty
        valid = (face_id >= 0)
        u = rast[..., 0]; v = rast[..., 1]; w0 = 1.0 - u - v
        bary = torch.stack([w0, u, v], dim=-1)             # (mb,H,W,3)
        fv = attr0[tri_i]                                  # (F,3,C)
        gathered = fv[face_id.clamp(min=0)]                # (mb,H,W,3,C)
        out = (bary[..., None] * gathered).sum(dim=-2)     # (mb,H,W,C)
        out = torch.where(valid[..., None], out, torch.zeros_like(out))
        empty_db = torch.zeros((*out.shape[:-1], 0), device=out.device, dtype=out.dtype)
        return out, empty_db

    def texture(self, tex, uv, uv_da=None, mip_level_bias=None, mip=None,
                filter_mode="auto", boundary_mode="wrap", max_mip_level=None):
        # Bilinear texture sampling via grid_sample (matches dr.texture).
        mode = "nearest" if filter_mode == "nearest" else "bilinear"
        grid = uv.float() * 2.0 - 1.0
        grid = grid.clone()
        grid[..., 1] = -grid[..., 1]                       # match nvdiffrast v-flip
        if boundary_mode == "wrap":
            # grid_sample has no true wrap; emulate by wrapping uv into [0,1) first.
            wrapped = (uv.float() % 1.0) * 2.0 - 1.0
            wrapped = wrapped.clone(); wrapped[..., 1] = -wrapped[..., 1]
            grid = wrapped
            pad = "border"
        else:
            pad = "border" if boundary_mode in ("clamp", "auto") else "zeros"
        tex_nchw = tex.float().permute(0, 3, 1, 2).contiguous()
        out = F.grid_sample(tex_nchw, grid, mode=mode, padding_mode=pad, align_corners=False)
        return out.permute(0, 2, 3, 1).contiguous()

    def antialias(self, color, rast, pos, tri, topology_hash=None, pos_gradient_boost=1.0):
        # nvdiffrast's silhouette AA is a gradient/edge-polish feature; for a
        # NON-differentiable bake it's not correctness-critical. No-op.
        return color


def make_raster_context(device: str = "cuda"):
    """Return the texture-bake rasterization context. Default = Kaolin
    (Apache-2.0, commercial-safe). Set ARTSMOKER_RASTERIZER=nvdiffrast to use the
    original nvdiffrast path (NVIDIA non-commercial license) — retained as a
    fallback so it can be reinstated if NVIDIA's terms change."""
    import os as _os
    choice = (_os.environ.get("ARTSMOKER_RASTERIZER", "kaolin") or "kaolin").lower().strip()
    if choice == "nvdiffrast":
        return NVDiffRastContextWrapper(device=device, context_type="cuda")
    return KaolinContextWrapper(device=device, context_type="cuda")


class DepthNormalizationStrategy(ABC):
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def __call__(
        self, depth: torch.FloatTensor, mask: torch.BoolTensor
    ) -> torch.FloatTensor:
        pass


class DepthControlNetNormalization(DepthNormalizationStrategy):
    def __init__(
        self, far_clip: float = 0.25, near_clip: float = 1.0, bg_value: float = 0.0
    ):
        self.far_clip = far_clip
        self.near_clip = near_clip
        self.bg_value = bg_value

    def __call__(
        self, depth: torch.FloatTensor, mask: torch.BoolTensor
    ) -> torch.FloatTensor:
        batch_size = depth.shape[0]
        min_depth = depth.view(batch_size, -1).min(dim=-1)[0][:, None, None]
        max_depth = depth.view(batch_size, -1).max(dim=-1)[0][:, None, None]
        depth = 1.0 - ((depth - min_depth) / (max_depth - min_depth + 1e-5)).clamp(
            0.0, 1.0
        )
        depth = depth * (self.near_clip - self.far_clip) + self.far_clip
        depth[~mask] = self.bg_value
        return depth


class Zero123PlusPlusNormalization(DepthNormalizationStrategy):
    def __init__(self, bg_value: float = 0.8):
        self.bg_value = bg_value

    def __call__(self, depth: FloatTensor, mask: BoolTensor) -> FloatTensor:
        batch_size = depth.shape[0]
        min_depth = depth.view(batch_size, -1).min(dim=-1)[0][:, None, None]
        max_depth = depth.view(batch_size, -1).max(dim=-1)[0][:, None, None]
        depth = ((depth - min_depth) / (max_depth - min_depth + 1e-5)).clamp(0.0, 1.0)
        depth[~mask] = self.bg_value
        return depth


class SimpleNormalization(DepthNormalizationStrategy):
    def __init__(
        self,
        scale: float = 1.0,
        offset: float = -1.0,
        clamp: bool = True,
        bg_value: float = 1.0,
    ):
        self.scale = scale
        self.offset = offset
        self.clamp = clamp
        self.bg_value = bg_value

    def __call__(self, depth: FloatTensor, mask: BoolTensor) -> FloatTensor:
        depth = depth * self.scale + self.offset
        if self.clamp:
            depth = depth.clamp(0.0, 1.0)
        depth[~mask] = self.bg_value
        return depth


def render(
    ctx: NVDiffRastContextWrapper,
    mesh: TexturedMesh,
    cam: Camera,
    height: int,
    width: int,
    render_attr: bool = True,
    render_depth: bool = True,
    render_normal: bool = True,
    render_tangent: bool = False,
    depth_normalization_strategy: DepthNormalizationStrategy = DepthControlNetNormalization(),
    attr_background: Union[float, torch.FloatTensor] = 0.5,
    antialias_attr=False,
    normal_background: Union[float, torch.FloatTensor] = 0.0,
    tangent_background: Union[float, torch.FloatTensor] = 0.0,
    texture_override=None,
    texture_filter_mode: str = "linear",
) -> RenderOutput:
    output_dict = {}

    v_pos_clip = get_clip_space_position(mesh.v_pos, cam.mvp_mtx)
    rast, _ = ctx.rasterize(v_pos_clip, mesh.t_pos_idx, (height, width), grad_db=True)
    mask = rast[..., 3] > 0

    gb_pos, _ = ctx.interpolate(mesh.v_pos[None], rast, mesh.t_pos_idx)
    output_dict.update({"mask": mask, "pos": gb_pos})

    if render_depth:
        gb_pos_vs = transform_points_homo(gb_pos, cam.w2c)
        gb_depth = -gb_pos_vs[..., 2]
        # set background pixels to min depth value for correct min/max calculation
        gb_depth = torch.where(
            mask,
            gb_depth,
            gb_depth.view(gb_depth.shape[0], -1).min(dim=-1)[0][:, None, None],
        )
        gb_depth = depth_normalization_strategy(gb_depth, mask)
        output_dict["depth"] = gb_depth

    if render_attr:
        tex_c, _ = ctx.interpolate(mesh.v_tex[None], rast, mesh.t_tex_idx)
        texture = (
            texture_override[None]
            if texture_override is not None
            else mesh.texture[None]
        )
        gb_rgb_fg = ctx.texture(texture, tex_c, filter_mode=texture_filter_mode)
        gb_rgb_bg = torch.ones_like(gb_rgb_fg) * attr_background
        gb_rgb = torch.where(mask[..., None], gb_rgb_fg, gb_rgb_bg)
        if antialias_attr:
            gb_rgb = ctx.antialias(gb_rgb, rast, v_pos_clip, mesh.t_pos_idx)
        output_dict["attr"] = gb_rgb

    if render_normal:
        gb_nrm, _ = ctx.interpolate(mesh.v_nrm[None], rast, mesh.stitched_t_pos_idx)
        gb_nrm = F.normalize(gb_nrm, dim=-1, p=2)
        gb_nrm[~mask] = normal_background
        output_dict["normal"] = gb_nrm

    if render_tangent:
        gb_tang, _ = ctx.interpolate(mesh.v_tang[None], rast, mesh.stitched_t_pos_idx)
        gb_tang = F.normalize(gb_tang, dim=-1, p=2)
        gb_tang[~mask] = tangent_background
        output_dict["tangent"] = gb_tang

    return RenderOutput(**output_dict)


def tensor_to_image(
    data: Union[Image.Image, torch.Tensor, np.ndarray],
    batched: bool = False,
    format: str = "HWC",
) -> Union[Image.Image, List[Image.Image]]:
    if isinstance(data, Image.Image):
        return data
    if isinstance(data, torch.Tensor):
        data = data.detach().cpu().numpy()
    if data.dtype == np.float32 or data.dtype == np.float16:
        data = (data * 255).astype(np.uint8)
    elif data.dtype == np.bool_:
        data = data.astype(np.uint8) * 255
    assert data.dtype == np.uint8
    if format == "CHW":
        if batched and data.ndim == 4:
            data = data.transpose((0, 2, 3, 1))
        elif not batched and data.ndim == 3:
            data = data.transpose((1, 2, 0))

    if batched:
        return [Image.fromarray(d) for d in data]
    return Image.fromarray(data)
