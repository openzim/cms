import base64
import io

import numpy as np
from PIL import Image, ImageFile

# https://stackoverflow.com/questions/42462431/oserror-broken-data-stream-when-reading-image-file#47958486
ImageFile.LOAD_TRUNCATED_IMAGES = True


def images_differ(
    b64_a: str, b64_b: str, max_changed_fraction: float = 0.0
) -> tuple[bool, float]:
    """
    Compare two base64-encoded images by checking fraction of different pixels
    """
    a = np.array(Image.open(io.BytesIO(base64.b64decode(b64_a))).convert("RGBA"))
    b = np.array(Image.open(io.BytesIO(base64.b64decode(b64_b))).convert("RGBA"))

    changed_fraction = float(np.any(a != b, axis=-1).mean())
    return changed_fraction > max_changed_fraction, changed_fraction
