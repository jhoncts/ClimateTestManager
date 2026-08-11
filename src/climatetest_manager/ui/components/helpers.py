"""Pequenos componentes visuais compartilhados pelas telas."""

import base64
from collections.abc import Callable
from functools import lru_cache
from io import BytesIO

import flet as ft
from PIL import Image, ImageOps, UnidentifiedImageError

from climatetest_manager.services.auth import UserSummary
from climatetest_manager.ui.theme import AppColors

_GITHUB_MARK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="#64748B" d="'
    "M12 .7a11.5 11.5 0 0 0-3.64 22.41c.58.1.79-.25.79-.56v-2.23 "
    "c-3.22.7-3.9-1.37-3.9-1.37-.52-1.34-1.28-1.7-1.28-1.7 "
    "c-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.2 1.77 1.2 "
    "1.03 1.76 2.7 1.25 3.36.95.1-.75.4-1.25.73-1.54 "
    "c-2.57-.29-5.27-1.28-5.27-5.69 0-1.26.45-2.28 1.19-3.09 "
    "c-.12-.29-.52-1.46.11-3.04 0 0 .97-.31 3.16 1.18A11 11 0 0 1 12 6.13 "
    "c.98 0 1.95.13 2.86.39 2.2-1.49 3.16-1.18 3.16-1.18 "
    "c.63 1.58.23 2.75.11 3.04.74.81 1.19 1.83 1.19 3.09 "
    "0 4.42-2.71 5.39-5.29 5.68.42.36.79 1.07.79 2.16v3.24 "
    "c0 .31.21.67.8.56A11.5 11.5 0 0 0 12 .7Z"
    '"/></svg>'
)
GITHUB_MARK_BASE64 = base64.b64encode(_GITHUB_MARK_SVG.encode("utf-8")).decode("ascii")


@lru_cache(maxsize=32)
def _optimized_profile_photo_source(encoded: str) -> str | None:
    """Reduz a foto antes de enviá-la pela LAN e devolve uma Data URI válida.

    O banco pode conter imagens antigas de até 2 MB. Enviar o base64 original em cada troca
    de tela deixava as estações lentas e, além disso, ``Image.src`` recebia base64 sem o prefixo
    de tipo de mídia. A normalização abaixo resolve os dois problemas sem perder a foto original.
    """

    try:
        raw = base64.b64decode(encoded, validate=True)
        if not raw:
            return None
        with Image.open(BytesIO(raw)) as opened:
            opened.load()
            normalized = ImageOps.exif_transpose(opened)
            fitted = ImageOps.fit(
                normalized,
                (256, 256),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            if fitted.mode not in {"RGB", "RGBA"}:
                fitted = fitted.convert("RGBA" if "A" in fitted.getbands() else "RGB")
            output = BytesIO()
            fitted.save(output, format="WEBP", quality=82, method=6)
    except (ValueError, OSError, UnidentifiedImageError):
        return None
    compact = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/webp;base64,{compact}"


def contextual_help(message: str) -> ft.Container:
    """Mostra uma ajuda compacta sem aumentar artificialmente a altura do título."""

    return ft.Container(
        width=24,
        height=24,
        border_radius=12,
        alignment=ft.Alignment.CENTER,
        tooltip=message,
        content=ft.Icon(
            ft.Icons.HELP_OUTLINE,
            size=17,
            color=AppColors.TEXT_SECONDARY,
        ),
    )


def section_heading(title: str, help_text: str, *, size: int = 17) -> ft.Row:
    """Combina um título de seção com a ajuda contextual pedida pelo usuário."""

    return ft.Row(
        spacing=7,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Text(
                title,
                size=size,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
            contextual_help(help_text),
        ],
    )


def user_avatar(user: UserSummary, *, size: int = 38) -> ft.Container:
    """Exibe uma miniatura leve da foto opcional ou as iniciais do usuário."""

    initials = (user.first_name[:1] + user.last_name[:1]).upper()
    source = (
        _optimized_profile_photo_source(user.profile_photo_b64)
        if user.profile_photo_b64
        else None
    )
    if source:
        content: ft.Control = ft.Image(
            src=source,
            width=size,
            height=size,
            fit=ft.BoxFit.COVER,
            border_radius=size / 2,
            filter_quality=ft.FilterQuality.MEDIUM,
            cache_width=max(64, size * 2),
            cache_height=max(64, size * 2),
            anti_alias=True,
            gapless_playback=True,
            error_content=ft.Text(
                initials,
                size=max(10, int(size * 0.3)),
                weight=ft.FontWeight.BOLD,
                color=AppColors.PRIMARY,
            ),
        )
    else:
        content = ft.Text(
            initials,
            size=max(10, int(size * 0.3)),
            weight=ft.FontWeight.BOLD,
            color=AppColors.PRIMARY,
        )
    return ft.Container(
        width=size,
        height=size,
        border_radius=size / 2,
        bgcolor=AppColors.PRIMARY_LIGHT,
        border=ft.Border.all(1, AppColors.DIVIDER),
        alignment=ft.Alignment.CENTER,
        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
        content=content,
    )


def github_credit(
    on_click: Callable[[object], None],
    *,
    compact: bool = False,
) -> ft.Container:
    """Crédito discreto e clicável exibido no canto inferior da aplicação."""

    return ft.Container(
        border_radius=9,
        padding=6 if compact else ft.Padding.symmetric(horizontal=8, vertical=6),
        alignment=ft.Alignment.CENTER,
        tooltip="Abrir o perfil github.com/jhoncts",
        on_click=on_click,
        content=ft.Row(
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=7,
            controls=[
                ft.Image(
                    src=GITHUB_MARK_BASE64,
                    width=18,
                    height=18,
                    filter_quality=ft.FilterQuality.HIGH,
                    anti_alias=True,
                ),
                *(
                    []
                    if compact
                    else [
                        ft.Text(
                            "Created by Jhoncts",
                            size=10,
                            color=AppColors.TEXT_SECONDARY,
                        )
                    ]
                ),
            ],
        ),
    )
