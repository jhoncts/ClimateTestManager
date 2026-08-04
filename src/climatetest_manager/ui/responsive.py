"""Regras centrais de adaptação da interface ao tamanho da janela."""

from dataclasses import dataclass

COMPACT_BREAKPOINT = 1180
SPACIOUS_BREAKPOINT = 1500
BREAKPOINT_HYSTERESIS = 32
RESIZE_REBUILD_MIN_DELTA = 48


@dataclass(frozen=True, slots=True)
class LayoutProfile:
    """Dimensões usadas pelo shell sem espalhar números mágicos pelas telas."""

    mode: str
    sidebar_width: int
    sidebar_padding: int
    content_padding: int
    compact_navigation: bool
    brand_icon_size: int
    navigation_icon_size: int

    def with_collapsed_sidebar(self, collapsed: bool) -> "LayoutProfile":
        """Mantém o breakpoint atual e compacta apenas a navegação lateral."""

        if not collapsed or self.compact_navigation:
            return self
        return LayoutProfile(
            mode=self.mode,
            sidebar_width=84,
            sidebar_padding=12,
            content_padding=self.content_padding,
            compact_navigation=True,
            brand_icon_size=38,
            navigation_icon_size=22,
        )

    @classmethod
    def from_width(cls, width: float | int | None) -> "LayoutProfile":
        """Escolhe uma faixa estável e evita reconstruções a cada pixel redimensionado."""

        resolved = float(width or 1280)
        if resolved < COMPACT_BREAKPOINT:
            return cls.for_mode("compact")
        if resolved < SPACIOUS_BREAKPOINT:
            return cls.for_mode("regular")
        return cls.for_mode("spacious")

    @classmethod
    def stable_from_width(
        cls,
        width: float | int | None,
        *,
        current_mode: str,
    ) -> "LayoutProfile":
        """Evita alternância contínua quando a largura oscila perto de um limite.

        A barra de rolagem e o arredondamento de escala do Windows podem mudar a
        largura útil em poucos pixels. Sem essa margem, a moldura era reconstruída
        repetidamente e a tela podia piscar ou voltar ao topo.
        """

        resolved = float(width or 1280)
        if current_mode == "compact":
            if resolved < COMPACT_BREAKPOINT + BREAKPOINT_HYSTERESIS:
                return cls.for_mode("compact")
            return cls.from_width(resolved)
        if current_mode == "spacious":
            if resolved >= SPACIOUS_BREAKPOINT - BREAKPOINT_HYSTERESIS:
                return cls.for_mode("spacious")
            return cls.from_width(resolved)
        if current_mode == "regular":
            if (
                resolved >= COMPACT_BREAKPOINT - BREAKPOINT_HYSTERESIS
                and resolved < SPACIOUS_BREAKPOINT + BREAKPOINT_HYSTERESIS
            ):
                return cls.for_mode("regular")
            return cls.from_width(resolved)
        return cls.from_width(resolved)

    @classmethod
    def for_mode(cls, mode: str) -> "LayoutProfile":
        """Centraliza as dimensões de cada faixa responsiva."""

        if mode == "compact":
            return cls(
                mode="compact",
                sidebar_width=84,
                sidebar_padding=12,
                content_padding=20,
                compact_navigation=True,
                brand_icon_size=38,
                navigation_icon_size=22,
            )
        if mode == "spacious":
            return cls(
                mode="spacious",
                sidebar_width=268,
                sidebar_padding=26,
                content_padding=36,
                compact_navigation=False,
                brand_icon_size=46,
                navigation_icon_size=21,
            )
        return cls(
            mode="regular",
            sidebar_width=252,
            sidebar_padding=24,
            content_padding=28,
            compact_navigation=False,
            brand_icon_size=42,
            navigation_icon_size=20,
        )


def viewport_width(page: object, event: object | None = None) -> float:
    """Obtém a largura útil sem depender da classe concreta do evento do Flet."""

    event_width = getattr(event, "width", None)
    if isinstance(event_width, (int, float)) and event_width > 0:
        return float(event_width)
    page_width = getattr(page, "width", None)
    if isinstance(page_width, (int, float)) and page_width > 0:
        return float(page_width)
    window = getattr(page, "window", None)
    window_width = getattr(window, "width", None)
    if isinstance(window_width, (int, float)) and window_width > 0:
        return float(window_width)
    return 1280.0
