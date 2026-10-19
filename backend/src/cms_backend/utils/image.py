import base64
import io

import numpy as np
from PIL import Image, ImageFile

# https://stackoverflow.com/questions/42462431/oserror-broken-data-stream-when-reading-image-file#47958486
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Per-channel difference (0-255) which is considered re-encoding noise. Images
# recompressed by another encoder or converted between colour profiles commonly
# differ by one or two levels on many pixels without looking any different.
NOISE_TOLERANCE = 2

# Per-channel difference (0-255) which is visible even for a single pixel.
VISIBLE_DELTA = 32


def images_differ(
    b64_a: str,
    b64_b: str,
    max_changed_fraction: float = 0.0,
    noise_tolerance: int = NOISE_TOLERANCE,
) -> tuple[bool, float]:
    """
    Compare two base64-encoded images by checking the fraction of different pixels.
    """
    a = np.array(Image.open(io.BytesIO(base64.b64decode(b64_a))).convert("RGBA"))
    b = np.array(Image.open(io.BytesIO(base64.b64decode(b64_b))).convert("RGBA"))
    if a.shape != b.shape:
        return True, 1.0

    deltas = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=-1)
    changed = deltas > 0
    changed_fraction = float(changed.mean())

    if changed_fraction == 0:
        return False, 0.0

    visible_fraction = float((deltas >= VISIBLE_DELTA).mean())
    if visible_fraction > max_changed_fraction:
        return True, changed_fraction

    median_delta = float(np.median(deltas[changed]))
    return median_delta > noise_tolerance, changed_fraction
