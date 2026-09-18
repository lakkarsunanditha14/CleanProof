"""Rejects photos that are too blurry or too dark to be used as evidence.

Measured on the demo photos (scripts/eval_robustness.py): normal phone/webcam photos have
sharpness 750-3800 and brightness 105-160; medium/heavy blur and very low resolution fall to
20-100, and underexposed photos to brightness 39-55. A retake is requested below these limits,
because no check can reliably judge a photo it cannot see.
"""
from typing import Optional

from PIL import Image, ImageFilter, ImageStat

MIN_SHARPNESS = 110.0
MIN_BRIGHTNESS = 60.0

_LAPLACIAN = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128)


def measure(image: Image.Image) -> tuple:
    """(sharpness, brightness): variance of the Laplacian and mean grey level at 512 px width."""
    grey = image.convert("L")
    grey = grey.resize((512, max(1, int(512 * grey.height / grey.width))))
    return ImageStat.Stat(grey.filter(_LAPLACIAN)).var[0], ImageStat.Stat(grey).mean[0]


def quality_problem(image: Image.Image) -> Optional[str]:
    """A plain-English retake message if the photo is unusable, otherwise None."""
    sharpness, brightness = measure(image)
    if brightness < MIN_BRIGHTNESS:
        return "The photo is too dark to verify. Please retake it in better light."
    if sharpness < MIN_SHARPNESS:
        return "The photo is too blurry to verify. Please retake it and hold the camera steady."
    return None
