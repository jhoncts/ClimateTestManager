"""Normalização segura de fotos de perfil para uso rápido em várias estações."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

_MAX_INPUT_BYTES = 12 * 1024 * 1024
_MAX_PIXELS = 36_000_000
_OUTPUT_SIZE = 640
_OUTPUT_QUALITY = 88


class ProfilePhotoError(ValueError):
    """Imagem que não pode ser usada com segurança como avatar."""


def optimize_profile_photo(image_bytes: bytes) -> bytes:
    """Converte uma foto para WEBP quadrado de alta qualidade e tamanho previsível.

    Uma imagem de câmera pode ter vários megabytes. Enviar esse base64 a cada reconstrução da
    interface prejudica principalmente as estações conectadas pela LAN. O avatar final mantém
    resolução muito acima do tamanho em que é exibido, mas normalmente fica com uma fração do
    peso original.
    """

    if not image_bytes:
        raise ProfilePhotoError("A foto selecionada está vazia.")
    if len(image_bytes) > _MAX_INPUT_BYTES:
        raise ProfilePhotoError("A foto original deve ter no máximo 12 MB.")

    try:
        with Image.open(BytesIO(image_bytes)) as opened:
            width, height = opened.size
            if width <= 0 or height <= 0 or width * height > _MAX_PIXELS:
                raise ProfilePhotoError(
                    "A resolução da foto é muito alta. Use uma imagem de até 36 megapixels."
                )
            image = ImageOps.exif_transpose(opened)
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGB")
            if image.mode == "RGBA":
                background = Image.new("RGB", image.size, "white")
                background.paste(image, mask=image.getchannel("A"))
                image = background
            else:
                image = image.convert("RGB")
            image = ImageOps.fit(
                image,
                (_OUTPUT_SIZE, _OUTPUT_SIZE),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            output = BytesIO()
            image.save(
                output,
                format="WEBP",
                quality=_OUTPUT_QUALITY,
                method=6,
                optimize=True,
            )
    except ProfilePhotoError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ProfilePhotoError("Escolha uma imagem PNG, JPG ou WEBP válida.") from error

    optimized = output.getvalue()
    if not optimized:
        raise ProfilePhotoError("Não foi possível preparar a foto selecionada.")
    return optimized
