"""Rodada 5: layouts críticos estáveis e diagnóstico visível de implantação.

Esta rodada mantém as regras de negócio validadas e reduz a complexidade de layout
nas três telas que apresentaram falhas no Windows real. A tela inteira possui um
único dono da rolagem e os cabeçalhos deixam de depender de ResponsiveRow.
"""

from __future__ import annotations

import flet as ft

from climatetest_manager import production_app
from climatetest_manager.round4_runtime import (
    SafeNewTestView,
    _disable_viewer_actions,
    _force_scroll_top,
    _safe_settings_builder,
    _show_admin_delete_dialog,
)
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.test_details import TestDetailsView

BUILD_REVISION = "R5-20260812"


def _revision_banner() -> ft.Container:
    return ft.Container(
        border_radius=10,
        bgcolor=AppColors.INFO_LIGHT,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        content=ft.Row(
            spacing=8,
            controls=[
                ft.Icon(ft.Icons.VERIFIED_OUTLINED, size=16, color=AppColors.INFO),
                ft.Text(
                    f"Interface estável {BUILD_REVISION}",
                    size=10,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_SECONDARY,
                ),
            ],
        ),
    )


class StableNewTestView(SafeNewTestView):
    """Formulário com uma única Column rolável e sem ListView aninhada."""

    def _build(self) -> ft.Column:
        title = "Editar ensaio" if self._details else "Novo ensaio"
        subtitle = (
            "Corrija os dados e informe o motivo da alteração."
            if self._details
            else "Preencha os campos; a condição é calculada em tempo real."
        )
        controls: list[ft.Control] = [
            ft.Row(
                wrap=True,
                run_spacing=8,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=3,
                        controls=[
                            ft.Text(
                                title,
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(subtitle, size=13, color=AppColors.TEXT_SECONDARY),
                        ],
                    ),
                    ft.Row(
                        wrap=True,
                        spacing=8,
                        controls=[
                            ft.Button(
                                content="Cancelar",
                                icon=ft.Icons.CLOSE,
                                on_click=lambda _event: self._on_cancel(),
                            ),
                            self.save_button,
                        ],
                    ),
                ],
            ),
            _revision_banner(),
            self.error_banner,
            self._identity_panel(),
            self._thermal_panel(),
            self._notes_panel(),
        ]
        if self._details:
            controls.append(
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    border_radius=16,
                    padding=18,
                    content=self.change_reason_selector.control,
                )
            )
        controls.extend([self.result_panel, ft.Container(height=12)])
        return ft.Column(
            key=f"stable-new-test-{id(self)}",
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=controls,
        )


class StableDetailsView(TestDetailsView):
    """Detalhes com cabeçalho simples e uma única rolagem vertical."""

    def __init__(self, details, *, on_back, on_edit, **kwargs) -> None:
        super().__init__(details, on_back=on_back, on_edit=on_edit, **kwargs)
        header_actions: list[ft.Control] = [
            ft.Button(
                content="Corrigir dados",
                icon=ft.Icons.EDIT,
                on_click=lambda _event: on_edit(),
            )
        ]
        if any(
            (
                details.chamber_started_at,
                details.chamber_ended_at,
                details.drying_started_at,
                details.drying_ended_at,
            )
        ):
            header_actions.append(
                ft.Button(
                    content="Corrigir horários",
                    icon=ft.Icons.EDIT_CALENDAR,
                    on_click=lambda _event: self._show_change_timestamps(),
                )
            )
        self.root = ft.Column(
            key=f"stable-details-{details.id}-{id(self)}",
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=16,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    wrap=True,
                    run_spacing=8,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=10,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK,
                                    tooltip="Voltar para Ensaios",
                                    on_click=lambda _event: on_back(),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            f"{details.client} / {details.process_number}",
                                            size=26,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Text(
                                            f"Ensaio #{details.id}",
                                            size=12,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(wrap=True, spacing=8, controls=header_actions),
                    ],
                ),
                _revision_banner(),
                self._summary_panel(),
                self._journey_panel(),
                self._phase_panel(),
                self._action_panel(),
                self._history_panel(),
                ft.Container(height=12),
            ],
        )


_App = production_app.ProductionClimateTestApplication


def _show_new_test(self) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    if self._selected_view == "new_test" and self._new_test_view is not None:
        return
    self._prepare_theme()
    view = StableNewTestView(
        on_cancel=self._confirm_discard_new_test,
        on_save=self._save_test,
        draft=self._new_test_draft,
    )
    view.save_button.disabled = False
    self._new_test_view = view
    self._render(view.root, selected_view="new_test")
    self._page.run_task(_force_scroll_top, view.root)


def _show_edit_test(self, test_id: int) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    self._prepare_theme()
    view = StableNewTestView(
        on_cancel=lambda: self.show_details(test_id),
        on_save=lambda command: self._update_test(test_id, command),
        details=self._service.get_details(test_id),
    )
    view.save_button.disabled = False
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def _show_details(self, test_id: int) -> None:
    self._prepare_theme()
    self._active_test_id = test_id
    details = self._service.get_details(test_id)
    view = StableDetailsView(
        details,
        on_back=self.show_tests,
        on_start_chamber=lambda value: self._perform(
            test_id,
            lambda: self._service.start_chamber(test_id, value),
            "Câmara iniciada e prazos calculados.",
        ),
        on_start_drying=lambda value: self._perform(
            test_id,
            lambda: self._service.start_drying(test_id, value),
            "Secagem iniciada a partir do horário real.",
        ),
        on_finish=lambda value: self._perform(
            test_id,
            lambda: self._service.finish(test_id, value),
            "Ensaio finalizado.",
        ),
        on_cancel=lambda reason: self._perform(
            test_id,
            lambda: self._service.cancel(test_id, reason),
            "Ensaio cancelado e motivo registrado.",
        ),
        on_edit=lambda: self.show_edit_test(test_id),
        on_delete=lambda: self._delete_test(test_id),
        on_change_timestamp=lambda timestamp, value, reason: self._perform(
            test_id,
            lambda: self._service.change_operational_timestamp(
                test_id, timestamp, value, reason
            ),
            "Horário operacional corrigido e alteração registrada.",
        ),
        on_advance_for_testing=(
            (
                lambda: self._perform(
                    test_id,
                    lambda: self._service.advance_for_testing(test_id),
                    "Etapa avançada somente para validação.",
                )
            )
            if production_app.test_controls_enabled()
            else None
        ),
    )
    if self._current_user.is_viewer:
        _disable_viewer_actions(view.root)
    if self._current_user.is_admin:
        view.root.controls.insert(
            2,
            ft.Container(
                bgcolor=AppColors.DANGER_LIGHT,
                border=ft.Border.all(1, AppColors.DANGER),
                border_radius=12,
                padding=12,
                content=ft.Row(
                    wrap=True,
                    run_spacing=8,
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Text(
                            "Administração: exclusão permanente disponível para cadastros "
                            "fictícios, duplicados ou inválidos.",
                            size=11,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        ft.Button(
                            content="Excluir do histórico",
                            icon=ft.Icons.DELETE_OUTLINE,
                            color=AppColors.DANGER,
                            on_click=lambda _event: _show_admin_delete_dialog(self, test_id),
                        ),
                    ],
                ),
            ),
        )
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def _settings_builder(**kwargs) -> ft.Control:
    content = _safe_settings_builder(**kwargs)
    if isinstance(content, ft.Column):
        content.controls.insert(1, _revision_banner())
    return content


def install_round5_fixes() -> None:
    if getattr(production_app, "_round5_fixes_installed", False):
        return
    _App.show_new_test = _show_new_test
    _App.show_edit_test = _show_edit_test
    _App.show_details = _show_details
    production_app.build_production_settings_view = _settings_builder
    production_app._round5_fixes_installed = True


install_round5_fixes()
main = production_app.main
