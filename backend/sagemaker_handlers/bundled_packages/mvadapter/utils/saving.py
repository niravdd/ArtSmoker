import json
import math
import os
import re
import shutil
from typing import Any, List, Optional, Union

import cv2
import numpy as np
import torch

try:
    import imageio
except ImportError:
    imageio = None

try:
    import matplotlib.pyplot as plt
    from matplotlib import cm
    from matplotlib.colors import LinearSegmentedColormap
except ImportError:
    plt = None
    cm = None
    LinearSegmentedColormap = None

from PIL import Image, ImageDraw

from .typing import *


def image_to_tensor(
    images: List[Image.Image], device: str = "cuda"
) -> torch.FloatTensor:
    tensors = []
    for image in images:
        tensor = torch.from_numpy(np.array(image)).float() / 255.0
        tensor = tensor.to(device)
        tensors.append(tensor)
    return torch.stack(tensors)


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


def largest_factor_near_sqrt(n: int) -> int:
    sqrt_n = int(math.sqrt(n))
    if sqrt_n * sqrt_n == n:
        return sqrt_n
    for i in range(sqrt_n, 0, -1):
        if n % i == 0:
            return i
    return 1


def make_image_grid(
    images: List[Image.Image],
    rows: Optional[int] = None,
    cols: Optional[int] = None,
    resize: Optional[int] = None,
) -> Image.Image:
    """Prepares a single grid of images. Useful for visualization purposes."""
    if rows is None and cols is not None:
        assert len(images) % cols == 0
        rows = len(images) // cols
    elif cols is None and rows is not None:
        assert len(images) % rows == 0
        cols = len(images) // rows
    elif rows is None and cols is None:
        rows = largest_factor_near_sqrt(len(images))
        cols = len(images) // rows

    assert len(images) == rows * cols

    if resize is not None:
        images = [img.resize((resize, resize)) for img in images]

    w, h = images[0].size
    grid = Image.new("RGB", size=(cols * w, rows * h))

    for i, img in enumerate(images):
        grid.paste(img, box=(i % cols * w, i // cols * h))
    return grid


class SaverMixin:
    _save_dir: Optional[str] = None
    _wandb_logger: Optional[Any] = None

    def set_save_dir(self, save_dir: str):
        self._save_dir = save_dir

    def get_save_dir(self):
        if self._save_dir is None:
            raise ValueError("Save dir is not set")
        return self._save_dir

    def convert_data(self, data):
        if data is None:
            return None
        elif isinstance(data, np.ndarray):
            return data
        elif isinstance(data, torch.Tensor):
            if data.dtype in [torch.float16, torch.bfloat16]:
                data = data.float()
            return data.detach().cpu().numpy()
        elif isinstance(data, list):
            return [self.convert_data(d) for d in data]
        elif isinstance(data, dict):
            return {k: self.convert_data(v) for k, v in data.items()}
        else:
            raise TypeError(
                "Data must be in type numpy.ndarray, torch.Tensor, list or dict, getting",
                type(data),
            )

    def get_save_path(self, filename):
        save_path = os.path.join(self.get_save_dir(), filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        return save_path

    DEFAULT_RGB_KWARGS = {"data_format": "HWC", "data_range": (0, 1)}
    DEFAULT_UV_KWARGS = {
        "data_format": "HWC",
        "data_range": (0, 1),
        "cmap": "checkerboard",
    }
    DEFAULT_GRAYSCALE_KWARGS = {"data_range": None, "cmap": "jet"}
    DEFAULT_GRID_KWARGS = {"align": "max"}

    def get_rgb_image_(self, img, data_format, data_range, rgba=False):
        img = self.convert_data(img)
        assert data_format in ["CHW", "HWC"]
        if data_format == "CHW":
            img = img.transpose(1, 2, 0)
        if img.dtype != np.uint8:
            img = img.clip(min=data_range[0], max=data_range[1])
            img = (
                (img - data_range[0]) / (data_range[1] - data_range[0]) * 255.0
            ).astype(np.uint8)
        nc = 4 if rgba else 3
        imgs = [img[..., start : start + nc] for start in range(0, img.shape[-1], nc)]
        imgs = [
            (
                img_
                if img_.shape[-1] == nc
                else np.concatenate(
                    [
                        img_,
                        np.zeros(
                            (img_.shape[0], img_.shape[1], nc - img_.shape[2]),
                            dtype=img_.dtype,
                        ),
                    ],
                    axis=-1,
                )
            )
            for img_ in imgs
        ]
        img = np.concatenate(imgs, axis=1)
        if rgba:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img

    def _save_rgb_image(self, filename, img, data_format, data_range,
                        name=None, step=None):
        img = self.get_rgb_image_(img, data_format, data_range)
        cv2.imwrite(filename, img)

    def save_rgb_image(self, filename, img,
                       data_format=DEFAULT_RGB_KWARGS["data_format"],
                       data_range=DEFAULT_RGB_KWARGS["data_range"],
                       name=None, step=None) -> str:
        save_path = self.get_save_path(filename)
        self._save_rgb_image(save_path, img, data_format, data_range, name, step)
        return save_path

    def save_image(self, filename, img) -> str:
        save_path = self.get_save_path(filename)
        img = self.convert_data(img)
        assert img.dtype == np.uint8 or img.dtype == np.uint16
        if img.ndim == 3 and img.shape[-1] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif img.ndim == 3 and img.shape[-1] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
        cv2.imwrite(save_path, img)
        return save_path
