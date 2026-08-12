"""Paleta visual centralizada com temas locais e materiais discretos."""

from __future__ import annotations

from contextvars import ContextVar

THEME_OPTIONS = (
    ("light", "Claro", "Leve e neutro"),
    ("amber", "Âmbar", "Laranja, branco e grafite com alto contraste"),
    ("ice", "Gelo", "Claro frio em azul e branco"),
    ("dark", "Escuro", "Confortável em ambientes com pouca luz"),
    ("graphite", "Grafite", "Escuro neutro com menos saturação"),
    ("ocean", "Oceano", "Azul profundo com destaque técnico"),
)
THEME_KEYS = {item[0] for item in THEME_OPTIONS}

_PALETTES: dict[str, dict[str, str]] = {
    "light": {
        "PRIMARY": "#087E8B",
        "PRIMARY_LIGHT": "#D5F6F7",
        "PAGE_BACKGROUND": "#EEF4F8",
        "NAV_BACKGROUND": "#FDFEFE",
        "NAV_SELECTED": "#DCF6F7",
        "NAV_HOVER": "#EDF7F9",
        "NAV_TEXT": "#475569",
        "SURFACE": "#FFFFFF",
        "TEXT_PRIMARY": "#0F172A",
        "TEXT_SECONDARY": "#64748B",
        "DIVIDER": "#DCE6ED",
        "WARNING": "#D97706",
        "WARNING_LIGHT": "#FEF3C7",
        "DANGER": "#DC2626",
        "DANGER_LIGHT": "#FEE2E2",
        "INFO": "#2563EB",
        "INFO_LIGHT": "#DBEAFE",
        "DRYING": "#7C3AED",
        "DRYING_LIGHT": "#EDE9FE",
        "WHITE": "#FFFFFF",
        "GLASS_SURFACE": "#EFFFFFFF",
        "GLASS_SURFACE_ACCENT": "#E8F7FBFC",
        "GLASS_BORDER": "#99D5E2E8",
        "SURFACE_SHADOW": "#190F172A",
        "INTERACTIVE_HOVER": "#16087E8B",
        "INTERACTIVE_PRESSED": "#26087E8B",
        "ACCENT_GLOW": "#3606B6C2",
    },
    "amber": {
        "PRIMARY": "#D85F00",
        "PRIMARY_LIGHT": "#FFE8D2",
        "PAGE_BACKGROUND": "#F6F2EE",
        "NAV_BACKGROUND": "#FFFEFC",
        "NAV_SELECTED": "#FFE0C2",
        "NAV_HOVER": "#FFF1E3",
        "NAV_TEXT": "#38332F",
        "SURFACE": "#FFFFFF",
        "TEXT_PRIMARY": "#211F1D",
        "TEXT_SECONDARY": "#6C625A",
        "DIVIDER": "#E5D8CC",
        "WARNING": "#B94F00",
        "WARNING_LIGHT": "#FFF0D9",
        "DANGER": "#C62828",
        "DANGER_LIGHT": "#FDE4E4",
        "INFO": "#315D9A",
        "INFO_LIGHT": "#E4EEF9",
        "DRYING": "#7450A8",
        "DRYING_LIGHT": "#EEE7F7",
        "WHITE": "#FFFFFF",
        "GLASS_SURFACE": "#F7FFFFFF",
        "GLASS_SURFACE_ACCENT": "#F4FFF8F2",
        "GLASS_BORDER": "#B8DFD1C3",
        "SURFACE_SHADOW": "#1A211F1D",
        "INTERACTIVE_HOVER": "#18D85F00",
        "INTERACTIVE_PRESSED": "#2AD85F00",
        "ACCENT_GLOW": "#34D85F00",
    },
    "ice": {
        "PRIMARY": "#1677A6",
        "PRIMARY_LIGHT": "#DDF2FA",
        "PAGE_BACKGROUND": "#F0F7FA",
        "NAV_BACKGROUND": "#FFFFFF",
        "NAV_SELECTED": "#D9F0F8",
        "NAV_HOVER": "#EDF8FC",
        "NAV_TEXT": "#40566A",
        "SURFACE": "#FFFFFF",
        "TEXT_PRIMARY": "#102433",
        "TEXT_SECONDARY": "#60788B",
        "DIVIDER": "#D7E7EF",
        "WARNING": "#C26A00",
        "WARNING_LIGHT": "#FFF0D8",
        "DANGER": "#C93643",
        "DANGER_LIGHT": "#FCE4E7",
        "INFO": "#2867B2",
        "INFO_LIGHT": "#E0ECFA",
        "DRYING": "#7460B7",
        "DRYING_LIGHT": "#ECE9F8",
        "WHITE": "#FFFFFF",
        "GLASS_SURFACE": "#F7FFFFFF",
        "GLASS_SURFACE_ACCENT": "#F2F4FBFE",
        "GLASS_BORDER": "#A9CDE2EC",
        "SURFACE_SHADOW": "#17102433",
        "INTERACTIVE_HOVER": "#181677A6",
        "INTERACTIVE_PRESSED": "#2B1677A6",
        "ACCENT_GLOW": "#341677A6",
    },
    "dark": {
        "PRIMARY": "#42D7C8",
        "PRIMARY_LIGHT": "#123F42",
        "PAGE_BACKGROUND": "#0C1420",
        "NAV_BACKGROUND": "#111C2A",
        "NAV_SELECTED": "#153D42",
        "NAV_HOVER": "#172737",
        "NAV_TEXT": "#C8D4E0",
        "SURFACE": "#162334",
        "TEXT_PRIMARY": "#F7FAFC",
        "TEXT_SECONDARY": "#9EB0C2",
        "DIVIDER": "#2B3C4D",
        "WARNING": "#FBBF24",
        "WARNING_LIGHT": "#433516",
        "DANGER": "#FB7185",
        "DANGER_LIGHT": "#44202A",
        "INFO": "#67A9FF",
        "INFO_LIGHT": "#183555",
        "DRYING": "#C4B5FD",
        "DRYING_LIGHT": "#312B50",
        "WHITE": "#FFFFFF",
        "GLASS_SURFACE": "#E619293A",
        "GLASS_SURFACE_ACCENT": "#E51B343D",
        "GLASS_BORDER": "#70445A68",
        "SURFACE_SHADOW": "#52000000",
        "INTERACTIVE_HOVER": "#2042D7C8",
        "INTERACTIVE_PRESSED": "#3542D7C8",
        "ACCENT_GLOW": "#5042D7C8",
    },
    "graphite": {
        "PRIMARY": "#67D6D0",
        "PRIMARY_LIGHT": "#24373A",
        "PAGE_BACKGROUND": "#171A1F",
        "NAV_BACKGROUND": "#1D2026",
        "NAV_SELECTED": "#26373A",
        "NAV_HOVER": "#282C33",
        "NAV_TEXT": "#D1D5DB",
        "SURFACE": "#22262D",
        "TEXT_PRIMARY": "#F3F4F6",
        "TEXT_SECONDARY": "#A7AFBA",
        "DIVIDER": "#353B44",
        "WARNING": "#F0B84B",
        "WARNING_LIGHT": "#453A20",
        "DANGER": "#F27B83",
        "DANGER_LIGHT": "#47282B",
        "INFO": "#7DA8E8",
        "INFO_LIGHT": "#29384D",
        "DRYING": "#B7A7E8",
        "DRYING_LIGHT": "#383246",
        "WHITE": "#FFFFFF",
        "GLASS_SURFACE": "#E62A2E35",
        "GLASS_SURFACE_ACCENT": "#E62D3839",
        "GLASS_BORDER": "#6B50565F",
        "SURFACE_SHADOW": "#50000000",
        "INTERACTIVE_HOVER": "#2467D6D0",
        "INTERACTIVE_PRESSED": "#3867D6D0",
        "ACCENT_GLOW": "#4D67D6D0",
    },
    "ocean": {
        "PRIMARY": "#5AD7E8",
        "PRIMARY_LIGHT": "#17384C",
        "PAGE_BACKGROUND": "#071724",
        "NAV_BACKGROUND": "#0C2132",
        "NAV_SELECTED": "#113B51",
        "NAV_HOVER": "#123047",
        "NAV_TEXT": "#C6D9E8",
        "SURFACE": "#0F2638",
        "TEXT_PRIMARY": "#F3FAFD",
        "TEXT_SECONDARY": "#98B5C8",
        "DIVIDER": "#234156",
        "WARNING": "#F6C45C",
        "WARNING_LIGHT": "#40351E",
        "DANGER": "#FF7F8A",
        "DANGER_LIGHT": "#49252D",
        "INFO": "#78B9FF",
        "INFO_LIGHT": "#173C5C",
        "DRYING": "#C2B4FF",
        "DRYING_LIGHT": "#332F57",
        "WHITE": "#FFFFFF",
        "GLASS_SURFACE": "#E5102A3D",
        "GLASS_SURFACE_ACCENT": "#E5153448",
        "GLASS_BORDER": "#70496A7C",
        "SURFACE_SHADOW": "#59000000",
        "INTERACTIVE_HOVER": "#245AD7E8",
        "INTERACTIVE_PRESSED": "#3A5AD7E8",
        "ACCENT_GLOW": "#4F5AD7E8",
    },
}
_COLOR_NAMES = frozenset(_PALETTES["light"])
_THEME_MODE: ContextVar[str] = ContextVar("climatetest_theme_mode", default="light")


class _AppColorsMeta(type):
    """Resolve cores no contexto da sessão atual em vez de mutar estado global."""

    def __getattribute__(cls, name: str):
        if name in _COLOR_NAMES:
            palette = _PALETTES.get(_THEME_MODE.get(), _PALETTES["light"])
            return palette[name]
        return super().__getattribute__(name)


class AppColors(metaclass=_AppColorsMeta):
    """Cores semânticas isoladas por contexto de sessão Flet.

    O servidor atende várias máquinas no mesmo processo. Usar atributos de classe mutáveis fazia
    uma estação alterar a paleta usada pela próxima renderização de outra sessão. O modo atual é
    guardado em ``ContextVar``; cada callback prepara sua própria paleta antes de construir a tela.
    """

    # Os valores abaixo mantêm introspecção e compatibilidade com ferramentas que inspecionam a
    # classe; o metaclass devolve a cor correspondente ao contexto corrente no acesso normal.
    PRIMARY = _PALETTES["light"]["PRIMARY"]
    PRIMARY_LIGHT = _PALETTES["light"]["PRIMARY_LIGHT"]
    PAGE_BACKGROUND = _PALETTES["light"]["PAGE_BACKGROUND"]
    NAV_BACKGROUND = _PALETTES["light"]["NAV_BACKGROUND"]
    NAV_SELECTED = _PALETTES["light"]["NAV_SELECTED"]
    NAV_HOVER = _PALETTES["light"]["NAV_HOVER"]
    NAV_TEXT = _PALETTES["light"]["NAV_TEXT"]
    SURFACE = _PALETTES["light"]["SURFACE"]
    TEXT_PRIMARY = _PALETTES["light"]["TEXT_PRIMARY"]
    TEXT_SECONDARY = _PALETTES["light"]["TEXT_SECONDARY"]
    DIVIDER = _PALETTES["light"]["DIVIDER"]
    WARNING = _PALETTES["light"]["WARNING"]
    WARNING_LIGHT = _PALETTES["light"]["WARNING_LIGHT"]
    DANGER = _PALETTES["light"]["DANGER"]
    DANGER_LIGHT = _PALETTES["light"]["DANGER_LIGHT"]
    INFO = _PALETTES["light"]["INFO"]
    INFO_LIGHT = _PALETTES["light"]["INFO_LIGHT"]
    DRYING = _PALETTES["light"]["DRYING"]
    DRYING_LIGHT = _PALETTES["light"]["DRYING_LIGHT"]
    WHITE = _PALETTES["light"]["WHITE"]
    GLASS_SURFACE = _PALETTES["light"]["GLASS_SURFACE"]
    GLASS_SURFACE_ACCENT = _PALETTES["light"]["GLASS_SURFACE_ACCENT"]
    GLASS_BORDER = _PALETTES["light"]["GLASS_BORDER"]
    SURFACE_SHADOW = _PALETTES["light"]["SURFACE_SHADOW"]
    INTERACTIVE_HOVER = _PALETTES["light"]["INTERACTIVE_HOVER"]
    INTERACTIVE_PRESSED = _PALETTES["light"]["INTERACTIVE_PRESSED"]
    ACCENT_GLOW = _PALETTES["light"]["ACCENT_GLOW"]

    @classmethod
    def normalize_mode(cls, mode: str | None) -> str:
        normalized = (mode or "light").strip().casefold()
        return normalized if normalized in THEME_KEYS else "light"

    @classmethod
    def apply_mode(cls, mode: str) -> None:
        """Seleciona a paleta apenas no contexto de execução da sessão atual."""

        _THEME_MODE.set(cls.normalize_mode(mode))

    @classmethod
    def current_mode(cls) -> str:
        return _THEME_MODE.get()
