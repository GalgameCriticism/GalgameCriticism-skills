"""Shared publication image policy for local exports and hosted uploads."""
from io import BytesIO

from PIL import Image, ImageOps

MAX_BYTES = 500 * 1024
MAX_WIDTH = 1600
POLICY_VERSION = 'jpeg500-white-v1'


def prepare_image(raw, decoration=False, original=False):
    """Return publication bytes, MIME, and audit details without modifying input."""
    with Image.open(BytesIO(raw)) as source:
        mime = Image.MIME.get(source.format)
        if mime not in ('image/png', 'image/jpeg', 'image/gif', 'image/webp'):
            raise ValueError('不支持的本地图片格式')
        animated = getattr(source, 'is_animated', False)
        details = {'original_bytes': len(raw), 'original_size': list(source.size),
                   'white_background': False, 'quality': None, 'preserved': False}
        if original or decoration or animated:
            if not original and len(raw) > MAX_BYTES:
                raise ValueError('装饰图或动图超过 500 KiB，请先处理该素材；明确要求保留原图时才使用 --original-images')
            details.update(bytes=len(raw), size=list(source.size), preserved=True)
            return raw, mime, details
        image = ImageOps.exif_transpose(source)
        transparent = ('A' in image.getbands() and image.getchannel('A').getextrema() != (255, 255)) or 'transparency' in image.info
        if transparent:
            rgba = image.convert('RGBA')
            image = Image.new('RGBA', rgba.size, 'white')
            image.alpha_composite(rgba)
            details['white_background'] = True
        image = image.convert('RGB')
        if image.width > MAX_WIDTH:
            image = image.resize((MAX_WIDTH, max(1, round(image.height * MAX_WIDTH / image.width))), Image.Resampling.LANCZOS)
        # Avoid repeated lossy encoding when the uploader checks a rendered JPEG.
        if source.format == 'JPEG' and len(raw) <= MAX_BYTES and source.size == image.size and source.getexif().get(274, 1) == 1:
            details.update(bytes=len(raw), size=list(image.size), preserved=True)
            return raw, mime, details
        while True:
            low, high, best = 82, 90, None
            while low <= high:
                quality = (low + high) // 2
                buffer = BytesIO()
                image.save(buffer, 'JPEG', quality=quality, subsampling=0, optimize=True)
                candidate = buffer.getvalue()
                if len(candidate) <= MAX_BYTES:
                    best = candidate, quality
                    low = quality + 1
                else:
                    high = quality - 1
            if best:
                data, quality = best
                details.update(bytes=len(data), size=list(image.size), quality=quality)
                return data, 'image/jpeg', details
            if image.width <= 600:
                raise ValueError('图片在清晰度下限内仍超过 500 KiB，请裁切/拆图或明确选择原图模式')
            image = image.resize((max(1, round(image.width * .85)), max(1, round(image.height * .85))), Image.Resampling.LANCZOS)
