"""OpenCV-based replacement for cvcuda operations.

The original MV-Adapter uses NVIDIA's cvcuda package for inpainting and
morphological operations. cvcuda is a heavy dependency requiring the full
NVIDIA video pipeline SDK. This module provides equivalent functionality
using standard OpenCV (cv2) which is lightweight and available everywhere.

Functions:
    inpaint_cvc: Inpaint image regions using Telea's algorithm
    batch_inpaint_cvc: Batched version of inpaint_cvc
    batch_erode: Morphological erosion on a batch of masks
    batch_dilate: Morphological dilation on a batch of masks
"""

from typing import Optional

import cv2
import numpy as np
import torch


def inpaint_cvc(
    image: torch.Tensor,
    mask: torch.Tensor,
    padding_size: int,
    return_dtype: Optional[torch.dtype] = None,
):
    """Inpaint image regions specified by mask using OpenCV's Telea algorithm.

    Args:
        image: Input image tensor (H, W, C) in [0, 1] float or uint8.
        mask: Binary mask tensor (H, W) where non-zero = inpaint region.
        padding_size: Inpainting radius (pixels).
        return_dtype: Optional output dtype. Defaults to input dtype.

    Returns:
        Inpainted image tensor with same shape as input.
    """
    input_dtype = image.dtype
    input_device = image.device

    # Convert to numpy uint8 for OpenCV
    if image.dtype != torch.uint8:
        image_np = (image.detach().cpu().float() * 255).clamp(0, 255).to(torch.uint8).numpy()
    else:
        image_np = image.detach().cpu().numpy()

    if mask.dtype != torch.uint8:
        mask_np = (mask.detach().cpu().float() * 255).clamp(0, 255).to(torch.uint8).numpy()
    else:
        mask_np = mask.detach().cpu().numpy()

    # OpenCV inpaint expects BGR or grayscale input, mask as single-channel uint8
    # Use Telea's algorithm (fast marching method) — good balance of speed and quality
    result_np = cv2.inpaint(image_np, mask_np, padding_size, cv2.INPAINT_TELEA)

    # Convert back to tensor
    result = torch.from_numpy(result_np).to(input_device)

    if return_dtype == torch.uint8 or input_dtype == torch.uint8:
        return result
    return result.to(dtype=input_dtype) / 255.0


def batch_inpaint_cvc(
    images: torch.Tensor,
    masks: torch.Tensor,
    padding_size: int,
    return_dtype: Optional[torch.dtype] = None,
):
    """Batch inpainting — applies inpaint_cvc to each image/mask pair.

    Args:
        images: Batch of images (N, H, W, C).
        masks: Batch of masks (N, H, W).
        padding_size: Inpainting radius.
        return_dtype: Optional output dtype.

    Returns:
        Batch of inpainted images (N, H, W, C).
    """
    output = torch.stack(
        [
            inpaint_cvc(image, mask, padding_size, return_dtype)
            for (image, mask) in zip(images, masks)
        ],
        dim=0,
    )
    return output


def batch_erode(
    masks: torch.Tensor, kernel_size: int, return_dtype: Optional[torch.dtype] = None
):
    """Morphological erosion on a batch of masks using OpenCV.

    Args:
        masks: Batch of masks (N, H, W).
        kernel_size: Size of the erosion kernel (square).
        return_dtype: Optional output dtype.

    Returns:
        Eroded masks tensor (N, H, W).
    """
    input_dtype = masks.dtype
    input_device = masks.device

    # Convert to numpy uint8
    masks_detached = masks.detach().cpu()
    if masks_detached.dtype != torch.uint8:
        masks_np = (masks_detached.float() * 255).clamp(0, 255).to(torch.uint8).numpy()
    else:
        masks_np = masks_detached.numpy()

    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    results = []
    for mask_np in masks_np:
        eroded = cv2.erode(mask_np, kernel, iterations=1)
        results.append(eroded)

    result_np = np.stack(results, axis=0)
    result = torch.from_numpy(result_np).to(input_device)

    if return_dtype == torch.uint8 or input_dtype == torch.uint8:
        return result
    return (result > 0).to(dtype=input_dtype)


def batch_dilate(
    masks: torch.Tensor, kernel_size: int, return_dtype: Optional[torch.dtype] = None
):
    """Morphological dilation on a batch of masks using OpenCV.

    Args:
        masks: Batch of masks (N, H, W).
        kernel_size: Size of the dilation kernel (square).
        return_dtype: Optional output dtype.

    Returns:
        Dilated masks tensor (N, H, W).
    """
    input_dtype = masks.dtype
    input_device = masks.device

    # Convert to numpy uint8
    masks_detached = masks.detach().cpu()
    if masks_detached.dtype != torch.uint8:
        masks_np = (masks_detached.float() * 255).clamp(0, 255).to(torch.uint8).numpy()
    else:
        masks_np = masks_detached.numpy()

    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    results = []
    for mask_np in masks_np:
        dilated = cv2.dilate(mask_np, kernel, iterations=1)
        results.append(dilated)

    result_np = np.stack(results, axis=0)
    result = torch.from_numpy(result_np).to(input_device)

    if return_dtype == torch.uint8 or input_dtype == torch.uint8:
        return result
    return (result > 0).to(dtype=input_dtype)
