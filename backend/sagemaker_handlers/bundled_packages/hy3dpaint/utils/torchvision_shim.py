# ARTSMOKER SHIM (not from upstream Hunyuan).
# basicsr (a dependency of realesrgan, used by imageSuperNet) imports
# `torchvision.transforms.functional_tensor`, which was REMOVED in torchvision
# 0.17+. The container pins torchvision 0.21, so that import raises ImportError
# and kills the Hunyuan paint backend at load. This shim re-registers
# functional_tensor as an alias of torchvision.transforms.functional (the few
# symbols basicsr uses — rgb_to_grayscale etc. — live there now), so basicsr
# imports cleanly. Import this module BEFORE importing realesrgan/basicsr.
import sys


def apply():
    try:
        import torchvision.transforms.functional as _F
    except Exception:
        return
    mod_name = "torchvision.transforms.functional_tensor"
    if mod_name in sys.modules:
        return
    try:
        import torchvision.transforms  # noqa: F401
        # Expose the old module path as an alias of the current functional module.
        sys.modules[mod_name] = _F
        import torchvision.transforms as _T
        try:
            setattr(_T, "functional_tensor", _F)
        except Exception:
            pass
    except Exception:
        pass
