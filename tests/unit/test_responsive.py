"""Testes das faixas de redimensionamento usadas por toda a interface."""

import unittest
from types import SimpleNamespace

from climatetest_manager.ui.responsive import LayoutProfile, viewport_width


class ResponsiveLayoutTests(unittest.TestCase):
    def test_selects_compact_regular_and_spacious_profiles(self) -> None:
        compact = LayoutProfile.from_width(820)
        notebook = LayoutProfile.from_width(900)
        regular = LayoutProfile.from_width(1280)
        spacious = LayoutProfile.from_width(1600)

        self.assertEqual(compact.mode, "compact")
        self.assertTrue(compact.compact_navigation)
        self.assertLess(compact.sidebar_width, regular.sidebar_width)
        self.assertEqual(notebook.mode, "regular")
        self.assertFalse(notebook.compact_navigation)
        self.assertEqual(regular.mode, "regular")
        self.assertEqual(spacious.mode, "spacious")
        self.assertGreater(spacious.content_padding, regular.content_padding)

    def test_resolves_event_page_window_and_fallback_widths(self) -> None:
        page = SimpleNamespace(width=1200, window=SimpleNamespace(width=1280))

        self.assertEqual(viewport_width(page, SimpleNamespace(width=900)), 900)
        self.assertEqual(viewport_width(page), 1200)
        page.width = None
        self.assertEqual(viewport_width(page), 1280)
        page.window.width = None
        self.assertEqual(viewport_width(page), 1280)

    def test_user_can_collapse_wide_sidebar_without_changing_content_profile(self) -> None:
        regular = LayoutProfile.for_mode("regular")
        collapsed = regular.with_collapsed_sidebar(True)

        self.assertTrue(collapsed.compact_navigation)
        self.assertEqual(collapsed.sidebar_width, 84)
        self.assertEqual(collapsed.content_padding, regular.content_padding)
        self.assertEqual(collapsed.mode, regular.mode)
        self.assertIs(regular.with_collapsed_sidebar(False), regular)
        compact = LayoutProfile.for_mode("compact")
        self.assertIs(compact.with_collapsed_sidebar(True), compact)

    def test_keeps_current_profile_while_width_jitters_near_breakpoint(self) -> None:
        self.assertEqual(
            LayoutProfile.stable_from_width(850, current_mode="regular").mode,
            "regular",
        )
        self.assertEqual(
            LayoutProfile.stable_from_width(827, current_mode="regular").mode,
            "compact",
        )
        self.assertEqual(
            LayoutProfile.stable_from_width(890, current_mode="compact").mode,
            "compact",
        )
        self.assertEqual(
            LayoutProfile.stable_from_width(892, current_mode="compact").mode,
            "regular",
        )
        self.assertEqual(
            LayoutProfile.stable_from_width(1480, current_mode="spacious").mode,
            "spacious",
        )


if __name__ == "__main__":
    unittest.main()
