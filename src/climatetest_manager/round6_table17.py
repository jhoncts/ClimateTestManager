"""Integra a visualização completa da Tabela 17 sem alterar a rolagem da tela principal."""

from __future__ import annotations

import flet as ft

from climatetest_manager import production_app
from climatetest_manager.round4_runtime import _force_scroll_top
from climatetest_manager.round6_runtime import RefinedNewTestView, apply_interaction_polish
from climatetest_manager.ui.components import styled_dialog
from climatetest_manager.ui.components.table17 import build_table17_preview
from climatetest_manager.ui.theme import AppColors


class R6NewTestView(RefinedNewTestView):
    """Mantém o resumo compacto e abre a tabela completa sob demanda."""

    def _build_result_panel(self) -> ft.Container:
        panel = super()._build_result_panel()
        self.table17_button = ft.Button(
            content="Visualizar Tabela 17 completa",
            icon=ft.Icons.TABLE_VIEW_OUTLINED,
            on_click=self._show_table17,
        )
        panel.content.controls.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.END,
                controls=[self.table17_button],
            )
        )
        return panel

    def _show_table17(self, _event: object | None = None) -> None:
        page = self.table17_button.page
        active_rule_id = self._condition.rule_id if self._condition is not None else None
        page.show_dialog(
            apply_interaction_polish(
                styled_dialog(
                    title="Tabela 17 — condição aplicada",
                    subtitle="A linha e a alternativa usadas no cálculo são destacadas automaticamente",
                    icon=ft.Icons.TABLE_CHART_OUTLINED,
                    content=ft.Container(
                        width=1020,
                        height=560,
                        content=ft.Column(
                            scroll=ft.ScrollMode.AUTO,
                            spacing=10,
                            controls=[
                                build_table17_preview(
                                    active_rule_id,
                                    compact=False,
                                    show_caption=True,
                                )
                            ],
                        ),
                    ),
                    actions=[
                        ft.Button(
                            content="Fechar",
                            bgcolor=AppColors.PRIMARY,
                            color=AppColors.WHITE,
                            on_click=lambda _close_event: page.pop_dialog(),
                        )
                    ],
                )
            )
        )


def _show_new_test(self) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    if self._selected_view == "new_test" and self._new_test_view is not None:
        return
    self._prepare_theme()
    view = R6NewTestView(
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
    view = R6NewTestView(
        on_cancel=lambda: self.show_details(test_id),
        on_save=lambda command: self._update_test(test_id, command),
        details=self._service.get_details(test_id),
    )
    view.save_button.disabled = False
    self._render(view.root, selected_view="details")
    self._page.run_task(_force_scroll_top, view.root)


def install() -> None:
    app = production_app.ProductionClimateTestApplication
    app.show_new_test = _show_new_test
    app.show_edit_test = _show_edit_test
