import base64
import io
import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from config import MAX_IMAGE_MB, MIN_ALIGNMENT_MATCHES

Image.MAX_IMAGE_PIXELS = 45_000_000

def decode_image(raw: bytes) -> np.ndarray:
    if not raw or len(raw) > MAX_IMAGE_MB * 1024 * 1024:
        raise ValueError(f'Image must be nonempty and at most {MAX_IMAGE_MB} MB')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.load()
            return np.asarray(im).copy()
    except (UnidentifiedImageError, OSError, ValueError) as e:
        raise ValueError(f'Invalid image: {e}') from e

def to_data_url(rgb: np.ndarray) -> str:
    ok, buf = cv2.imencode('.jpg', cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise ValueError('Failed to encode image')
    return 'data:image/jpeg;base64,' + base64.b64encode(buf).decode('ascii')

def to_jpg(rgb: np.ndarray) -> bytes:
    return base64.b64decode(to_data_url(rgb).split(',', 1)[1])

def align_to_reference(reference: np.ndarray, test: np.ndarray):
    """ORB + RANSAC homography. Reject low-confidence registrations."""
    rh, rw = reference.shape[:2]
    th, tw = test.shape[:2]
    g1 = cv2.cvtColor(reference, cv2.COLOR_RGB2GRAY)
    g2 = cv2.cvtColor(test, cv2.COLOR_RGB2GRAY)
    orb = cv2.ORB_create(nfeatures=3500)
    kp1, d1 = orb.detectAndCompute(g1, None)
    kp2, d2 = orb.detectAndCompute(g2, None)
    if d1 is None or d2 is None:
        return None, 'Not enough image features to align'
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    pairs = matcher.knnMatch(d2, d1, k=2)
    good = [a for pair in pairs if len(pair) == 2 for a,b in [pair] if a.distance < 0.72*b.distance]
    if len(good) < MIN_ALIGNMENT_MATCHES:
        return None, f'Only {len(good)} alignment matches'
    src = np.float32([kp2[m.queryIdx].pt for m in good]).reshape(-1,1,2)
    dst = np.float32([kp1[m.trainIdx].pt for m in good]).reshape(-1,1,2)
    H, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if H is None or inliers is None or int(inliers.sum()) < 12 or float(inliers.mean()) < 0.45:
        return None, 'Alignment failed geometric consistency check'
    corners = cv2.perspectiveTransform(np.float32([[[0,0]],[[tw,0]],[[tw,th]],[[0,th]]]), H).reshape(4,2)
    area = cv2.contourArea(corners)
    if not (0.55 * rw * rh <= area <= 1.7 * rw * rh):
        return None, 'Alignment scale outside safe limits'
    return cv2.warpPerspective(test, H, (rw,rh)), f'Aligned ({int(inliers.sum())} inliers)'

def defect_box(box, width, height):
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        return None
    try:
        ymin,xmin,ymax,xmax = [max(0, min(1000, float(v))) for v in box]
    except (TypeError, ValueError):
        return None
    x1,x2 = round(xmin*width/1000), round(xmax*width/1000)
    y1,y2 = round(ymin*height/1000), round(ymax*height/1000)
    if x2 <= x1 or y2 <= y1:
        return None
    return [max(0,x1), max(0,y1), min(width-1,x2), min(height-1,y2)]
