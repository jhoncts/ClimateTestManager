"""Regressões da interface final e do upgrade seguro da versão 0.8.5."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import flet as ft

from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.repositories.climate_tests import AuditHistoryEntry, ClimateTestRepository
from climatetest_manager.round3_runtime import _build_history_view
from climatetest_manager.round7_runtime import CleanDetailsView
from climatetest_manager.services.auth import UserSummary
from climatetest_manager.services.climate_tests import ClimateTestService, CreateClimateTestCommand
from climatetest_manager.ui.components.table17_interactive import build_interactive_table17
from climatetest_manager.ui.interaction import hoverable_navigation_surface
from climatetest_manager.ui.theme import THEME_KEYS, AppColors
from climatetest_manager.ui.views.final_new_test import TABLE17_MODE, FinalNewTestView
from climatetest_manager.v084_stability import _hold_button


def _walk(control: ft.Control):
    yield control
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from _walk(content)
    for child in getattr(control, "controls", ()) or ():
        if isinstance(child, ft.Control):
            yield from _walk(child)


def _texts(control: ft.Control) -> list[str]:
    return [str(item.value or "") for item in _walk(control) if isinstance(item, ft.Text)]


def _admin() -> UserSummary:
    return UserSummary(
        id=1,
        username="admin",
        email="admin@example.com",
        first_name="Administrador",
        last_name="Laboratório",
        role="admin",
        is_active=True,
        onboarding_completed=True,
        last_login_at=None,
    )


def test_final_new_test_has_one_scroll_owner_and_no_reparented_control() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
    controls = list(_walk(view.root))
    identities = [id(control) for control in controls]

    assert isinstance(view.root, ft.Column)
    assert view.root.scroll == ft.ScrollMode.AUTO
    assert len(identities) == len(set(identities))
    assert sum(control is view.service_temperature for control in controls) == 1
    assert _texts(view.root).count("Condição que será aplicada") == 1
    assert "0/1000" in _texts(view.root)


def test_final_table17_changes_with_ts_and_selects_a_condition_in_one_click() -> None:
    selected: list[tuple[str, str]] = []
    table = build_interactive_table17(
        ts=Decimal("65"),
        selected_epl=None,
        selected_option=None,
        on_select_epl=lambda value: selected.append(("epl", value)),
        on_select_option=lambda value: selected.append(("option", value)),
    )
    gb_a = next(cell for epl, option, cell in table._option_cells if (epl, option) == ("Gb", "A"))
    gb_b = next(cell for epl, option, cell in table._option_cells if (epl, option) == ("Gb", "B"))

    assert gb_a.opacity == 0.72
    assert gb_b.opacity == 0.28
    gb_a.on_click(None)
    assert selected == [("epl", "Gb"), ("option", "A")]

    table.set_state(ts=Decimal("81"), selected_epl="Gb", selected_option="B")
    assert gb_b.opacity == 1
    assert "selecionada" in str(gb_b.tooltip).lower()


def test_table17_keeps_the_session_theme_during_late_state_updates() -> None:
    try:
        AppColors.apply_mode("lavender")
        table = build_interactive_table17(
            ts=Decimal("81"),
            selected_epl="Gb",
            selected_option="B",
            on_select_epl=lambda _value: None,
            on_select_option=lambda _value: None,
        )
        gb = table._epl_chips["Gb"]
        gb_b = next(
            cell for epl, option, cell in table._option_cells if (epl, option) == ("Gb", "B")
        )
        expected_primary = AppColors.PRIMARY
        expected_light = AppColors.PRIMARY_LIGHT

        # Simula um callback tardio iniciado em outro ContextVar.
        AppColors.apply_mode("light")
        table.set_state(ts=Decimal("81"), selected_epl="Gb", selected_option="B")

        assert gb.border.top.color == expected_primary
        assert gb.bgcolor == expected_light
        assert gb_b.border.top.color == expected_primary
        assert gb_b.bgcolor == expected_light
        assert AppColors.current_mode() == "lavender"
    finally:
        AppColors.apply_mode("light")


def test_final_form_marks_required_fields_and_keeps_table_tree_stable() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
    table = view._interactive_table
    cells = tuple(cell for _epl, _option, cell in table._option_cells)
    view.mode_group.value = TABLE17_MODE
    view._on_mode_change()
    view.service_temperature.value = "81"
    view._recalculate()
    view._interactive_table._select_condition("Gb", "B")

    assert view._condition is not None
    assert view._condition.rule_id == "G1-HIGH-B"
    assert view._interactive_table is table
    assert tuple(cell for _epl, _option, cell in table._option_cells) == cells

    view.client.value = ""
    view.process_number.value = ""
    view.product.value = ""
    view._submit()
    assert view.client.error == "Campo obrigatório."
    assert view.process_number.error == "Campo obrigatório."
    assert view.product.error == "Campo obrigatório."
    assert view.error_banner.visible is True


def test_sidebar_labels_exist_expanded_and_only_hide_after_explicit_collapse() -> None:
    expanded = hoverable_navigation_surface(
        label="Novo ensaio",
        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
        selected=True,
        compact=False,
        icon_size=20,
        on_click=lambda: None,
        badge_count=2,
    )
    compact = hoverable_navigation_surface(
        label="Novo ensaio",
        icon=ft.Icons.ADD_CIRCLE_OUTLINE,
        selected=True,
        compact=True,
        icon_size=20,
        on_click=lambda: None,
        badge_count=0,
    )

    assert "Novo ensaio" in _texts(expanded)
    assert "Novo ensaio" not in _texts(compact)
    assert compact.tooltip == "Novo ensaio"
    assert len(expanded.content.controls) == 3
    label_box = expanded.content.controls[1]
    assert isinstance(label_box, ft.Container)
    assert label_box.expand is None
    assert (label_box.width or 0) > 0
    assert isinstance(label_box.content, ft.Text)
    assert label_box.content.value == "Novo ensaio"
    assert label_box.content.height is None


def test_table17_rows_have_explicit_height_and_cannot_collapse_in_webview() -> None:
    table = build_interactive_table17(
        ts=Decimal("75"),
        selected_epl=None,
        selected_option=None,
        on_select_epl=lambda _value: None,
        on_select_option=lambda _value: None,
    )

    assert len(table._data_rows) == 8
    assert all(row.height == 58 for row in table._data_rows)
    assert all(row.vertical_alignment == ft.CrossAxisAlignment.CENTER for row in table._data_rows)
    assert sum(row.height or 0 for row in table._data_rows) + 42 == table.TABLE_BODY_HEIGHT


def test_final_form_keeps_compact_header_and_equal_height_top_cards() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
    header = view.root.controls[0]
    cards = view.root.controls[2]

    assert isinstance(header, ft.Row)
    assert header.wrap is False
    assert header.controls[0].expand is True
    assert isinstance(cards, ft.Row)
    assert cards.intrinsic_height is False
    assert cards.vertical_alignment == ft.CrossAxisAlignment.START
    assert cards.controls[0].expand == 5
    assert cards.controls[1].expand == 7
    assert cards.controls[0].height == cards.controls[1].height
    assert cards.controls[0].height == view.STANDARD_TOP_CARD_HEIGHT
    assert view._identity_panel_control in view._refresh_targets
    assert view._thermal_panel_control in view._refresh_targets
    assert view.notes.height == 56

    view.mode_group.value = ConditionInputMode.DIRECT_TS.value
    view._on_mode_change()
    assert cards.controls[0].height == cards.controls[1].height
    assert cards.controls[0].height == view.DIRECT_TS_TOP_CARD_HEIGHT
    assert view.DIRECT_TS_TOP_CARD_HEIGHT > view.STANDARD_TOP_CARD_HEIGHT

    view.mode_group.value = TABLE17_MODE
    view._on_mode_change()
    assert cards.controls[0].height == cards.controls[1].height
    assert cards.controls[0].height == view.TABLE17_TOP_CARD_HEIGHT
    assert view._advanced_holder.visible is True
    assert view._advanced_holder.height == view.ADVANCED_TABLE_HEIGHT
    assert view._interactive_table.height < view._advanced_holder.height


def test_final_screen_builds_under_every_supported_theme() -> None:
    try:
        for mode in sorted(THEME_KEYS):
            AppColors.apply_mode(mode)
            view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
            assert isinstance(view.root, ft.Column)
            assert view.root.scroll == ft.ScrollMode.AUTO
            assert "Identificação" in _texts(view.root)
            assert "Configuração térmica" in _texts(view.root)
    finally:
        AppColors.apply_mode("light")


def test_advanced_table_is_read_only_outside_explicit_table_selection_mode() -> None:
    changed: list[tuple[str, str]] = []
    table = build_interactive_table17(
        ts=Decimal("81"),
        selected_epl="Gb",
        selected_option="B",
        on_select_epl=lambda value: changed.append(("epl", value)),
        on_select_option=lambda value: changed.append(("option", value)),
        interactive=False,
    )
    gb = table._epl_chips["Gb"]
    gb_b = next(cell for epl, option, cell in table._option_cells if (epl, option) == ("Gb", "B"))

    assert gb.on_click is None
    assert gb_b.on_click is None
    assert "somente visualização" in str(gb_b.tooltip).lower()
    table._select_condition("Gb", "A")
    assert changed == []


def test_final_form_only_allows_table_edits_in_table17_mode() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
    view.epl.value = "Gb"
    view.delta_t.value = "41"
    view._recalculate()
    original_option = view.option_group.value

    assert view.mode_group.value == ConditionInputMode.CALCULATED.value
    assert view._interactive_table._interactive is False
    view._select_table_option("B")
    assert view.option_group.value == original_option

    view.mode_group.value = TABLE17_MODE
    view._on_mode_change()
    view.service_temperature.value = "81"
    view._recalculate()
    assert view._interactive_table._interactive is True


def test_custom_mode_uses_roomier_fields_and_clean_two_column_layout() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
    view.mode_group.value = ConditionInputMode.DIRECT_CONFIGURATION.value
    view._on_mode_change()

    assert view.manual_chamber_temperature.height == 52
    assert view.manual_chamber_humidity.height == 52
    assert view.manual_chamber_duration.height == 52
    assert view._mode_selector_box.col["sm"] == 4
    assert view._thermal_input_box.col["sm"] == 8
    rows = view.manual_condition_fields.content.controls
    chamber_row = rows[1]
    assert isinstance(chamber_row, ft.ResponsiveRow)
    assert chamber_row.controls[0].col["sm"] == 6
    assert chamber_row.controls[1].col["sm"] == 6


def test_alternative_panel_uses_two_compact_condition_cards() -> None:
    view = FinalNewTestView(on_cancel=lambda: None, on_save=lambda _command: None)
    view.epl.value = "Gb"
    view.service_temperature.value = "69"
    view.mode_group.value = ConditionInputMode.DIRECT_TS.value
    view._on_mode_change()

    assert view.option_panel.height == 104
    assert view._option_card_a.height == 58
    assert view._option_card_b.height == 58
    assert "90±2 °C" in str(view._option_summary_a.value)
    assert "672 h" in str(view._option_summary_a.value)
    assert view._option_card_b.opacity < 1
    assert view._option_summary_a.no_wrap is True
    assert view._option_detail_a.no_wrap is True


def test_actions_use_anchored_popup_with_permission_states() -> None:
    with TemporaryDirectory() as temporary_directory:
        engine = initialize_database(Path(temporary_directory) / "actions.db")
        try:
            repository = ClimateTestRepository(create_session_factory(engine))
            service = ClimateTestService(repository)
            test_id = service.create(
                CreateClimateTestCommand(
                    client="Cliente",
                    process_number="26018",
                    product="Produto",
                    epl="Gb",
                    tamb_max_c="40",
                    delta_t_max_k="41",
                    selected_option="B",
                )
            )
            view = CleanDetailsView(
                service.get_details(test_id),
                on_back=lambda: None,
                on_start_chamber=lambda _value: None,
                on_start_drying=lambda _value: None,
                on_finish=lambda _value: None,
                on_cancel=lambda _reason: None,
                on_edit=lambda: None,
                on_delete=lambda: None,
                on_admin_delete=lambda _reason: None,
                is_admin=False,
                can_operate=True,
                on_change_timestamp=lambda _timestamp, _value, _reason: None,
            )
            menu = view._r7_actions_button

            assert isinstance(menu, ft.PopupMenuButton)
            assert menu.menu_position == ft.PopupMenuPosition.UNDER
            assert menu.width == 112
            assert menu.height == 40
            assert view.root.controls[0].wrap is False
            assert len(menu.items) == 3
            assert menu.items[0].disabled is False
            assert menu.items[1].disabled is False
            assert menu.items[2].disabled is True
            assert "Somente administradores" in str(menu.items[2].tooltip)
        finally:
            engine.dispose()


def test_hold_confirmation_and_global_pause_history_are_explicit() -> None:
    hold = _hold_button(
        SimpleNamespace(run_task=lambda *_args: None),
        label="Cancelar ensaio",
        on_confirm=lambda: None,
    )
    assert isinstance(hold, ft.GestureDetector)
    assert "Segure por 1,6 s • solte para abortar" in _texts(hold)
    assert "0%" in _texts(hold)

    event = AuditHistoryEntry(
        test_id=0,
        client="Equipamento",
        process_number="Câmara climática",
        action="Câmara climática pausada",
        actor="Operador",
        occurred_at=datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
        new_value="0 ensaio(s) afetado(s).",
        reason="Manutenção preventiva",
    )
    history = _build_history_view([event], on_select=lambda _test_id: None)
    event_card = history.controls[2]

    assert event_card.on_click is None
    assert "Câmara climática pausada" in _texts(history)
    assert any("Manutenção preventiva" in value for value in _texts(history))
