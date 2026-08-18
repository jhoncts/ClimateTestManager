from io import BytesIO

import pytest
from PIL import Image

from climatetest_manager.services.profile_photos import ProfilePhotoError, optimize_profile_photo


def _jpeg(width: int = 1800, height: int = 1200) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), "white").save(buffer, format="JPEG", quality=95)
    return buffer.getvalue()


def test_optimize_profile_photo_generates_compact_square_webp() -> None:
    source = _jpeg()

    optimized = optimize_profile_photo(source)

    assert len(optimized) < len(source)
    with Image.open(BytesIO(optimized)) as avatar:
        assert avatar.format == "WEBP"
        assert avatar.size == (640, 640)
        assert avatar.mode == "RGB"


def test_optimize_profile_photo_rejects_invalid_content() -> None:
    with pytest.raises(ProfilePhotoError, match="PNG, JPG ou WEBP"):
        optimize_profile_photo(b"isto nao e uma imagem")


def test_optimize_profile_photo_rejects_empty_file() -> None:
    with pytest.raises(ProfilePhotoError, match="vazia"):
        optimize_profile_photo(b"")
