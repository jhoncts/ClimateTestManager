"""Regressões da interface final e do upgrade seguro da versão 0.8.5."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import flet as ft

from climatetest_manager.database.session import create_session_factory, initialize_database
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
