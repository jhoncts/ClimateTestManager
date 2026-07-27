"""Configuração da janela principal da aplicação."""

import os
from collections.abc import Callable
from datetime import datetime

import flet as ft

from climatetest_manager import __version__
from climatetest_manager.config import (
    get_database_path,
    load_theme_mode,
    save_theme_mode,
    test_controls_enabled,
)
from climatetest_manager.database.session import create_session_factory, initialize_database
from climatetest_manager.repositories.climate_tests import ClimateTestRepository
from climatetest_manager.services.background import (
    configure_notification_task,
    notification_task_installed,
)
from climatetest_manager.services.climate_tests import (
    ClimateTestListItem,
    ClimateTestService,
    CreateClimateTestCommand,
    UpdateClimateTestCommand,
)
from climatetest_manager.services.exports import (
    build_database_backup_bytes,
    build_tests_csv_bytes,
    export_test_calendar,
)
from climatetest_manager.services.notifications import WindowsToastProvider
from climatetest_manager.ui.theme import AppColors
from climatetest_manager.ui.views.agenda import build_agenda_view
from climatetest_manager.ui.views.dashboard import build_dashboard
from climatetest_manager.ui.views.history import build_history_view
from climatetest_manager.ui.views.new_test import build_edit_test_view, build_new_test_view
from climatetest_manager.ui.views.settings import build_settings_view
from climatetest_manager.ui.views.test_details import build_test_details_view
from climatetest_manager.ui.views.tests_list import build_tests_list_view


def _navigation_item(
    label: str,
    icon: ft.IconData,
    *,
    selected: bool = False,
    on_click: Callable[[], None] | None = None,
) -> ft.Container:
    """Cria um item visual da navegação lateral."""

    return ft.Container(
        border_radius=10,
        bgcolor=AppColors.NAV_SELECTED if selected else AppColors.NAV_BACKGROUND,
        padding=12,
        opacity=1 if on_click or selected else 0.55,
        on_click=(lambda _event: on_click()) if on_click else None,
        content=ft.Row(
            spacing=12,
            controls=[
                ft.Icon(
                    icon,
                    size=20,
                    color=AppColors.PRIMARY if selected else AppColors.NAV_TEXT,
                ),
                ft.Text(
                    label,
                    size=14,
                    weight=ft.FontWeight.BOLD if selected else ft.FontWeight.NORMAL,
                    color=AppColors.PRIMARY if selected else AppColors.NAV_TEXT,
                ),
            ],
        ),
    )


def _build_sidebar(
    *,
    selected_view: str,
    on_dashboard: Callable[[], None],
    on_tests: Callable[[], None],
    on_new_test: Callable[[], None],
    on_agenda: Callable[[], None],
    on_history: Callable[[], None],
    on_settings: Callable[[], None],
) -> ft.Container:
    """Monta a identidade e a navegação principal."""

    return ft.Container(
        width=252,
        bgcolor=AppColors.NAV_BACKGROUND,
        padding=24,
        content=ft.Column(
            spacing=8,
            controls=[
                ft.Row(
                    spacing=12,
                    controls=[
                        ft.Container(
                            width=42,
                            height=42,
                            border_radius=12,
                            bgcolor=AppColors.PRIMARY,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(ft.Icons.SCIENCE, color=AppColors.WHITE, size=24),
                        ),
                        ft.Column(
                            spacing=0,
                            controls=[
                                ft.Text(
                                    "ClimateTest",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    "Manager",
                                    size=13,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ],
                ),
                ft.Container(height=22),
                _navigation_item(
                    "Dashboard",
                    ft.Icons.DASHBOARD,
                    selected=selected_view == "dashboard",
                    on_click=on_dashboard,
                ),
                _navigation_item(
                    "Ensaios",
                    ft.Icons.LIST,
                    selected=selected_view in {"tests", "details"},
                    on_click=on_tests,
                ),
                _navigation_item(
                    "Novo ensaio",
                    ft.Icons.ADD,
                    selected=selected_view == "new_test",
                    on_click=on_new_test,
                ),
                _navigation_item(
                    "Agenda",
                    ft.Icons.CALENDAR_MONTH,
                    selected=selected_view == "agenda",
                    on_click=on_agenda,
                ),
                _navigation_item(
                    "Atividades",
                    ft.Icons.HISTORY,
                    selected=selected_view == "history",
                    on_click=on_history,
                ),
                _navigation_item(
                    "Configurações",
                    ft.Icons.SETTINGS,
                    selected=selected_view == "settings",
                    on_click=on_settings,
                ),
                ft.Container(expand=True),
                ft.Divider(height=1, color=AppColors.DIVIDER),
                ft.Text(
                    "ABNT NBR IEC 60079-0:2020",
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                ),
                ft.Text(
                    f"Versão {__version__}",
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                ),
            ],
        ),
    )


def _build_shell(
    content: ft.Control,
    *,
    selected_view: str,
    on_dashboard: Callable[[], None],
    on_tests: Callable[[], None],
    on_new_test: Callable[[], None],
    on_agenda: Callable[[], None],
    on_history: Callable[[], None],
    on_settings: Callable[[], None],
) -> ft.Row:
    """Combina a navegação e o conteúdo da tela atual."""

    return ft.Row(
        expand=True,
        spacing=0,
        controls=[
            _build_sidebar(
                selected_view=selected_view,
                on_dashboard=on_dashboard,
                on_tests=on_tests,
                on_new_test=on_new_test,
                on_agenda=on_agenda,
                on_history=on_history,
                on_settings=on_settings,
            ),
            ft.Container(
                expand=True,
                bgcolor=AppColors.PAGE_BACKGROUND,
                padding=32,
                content=content,
            ),
        ],
    )


class ClimateTestApplication:
    """Controla navegação e casos de uso sem colocar regras na interface."""

    def __init__(
        self,
        page: ft.Page,
        service: ClimateTestService,
        *,
        theme_mode: str,
    ) -> None:
        self._page = page
        self._service = service
        self._theme_mode = theme_mode

    def start(self) -> None:
        self.show_dashboard()

    def _render(self, content: ft.Control, *, selected_view: str) -> None:
        self._page.clean()
        self._page.add(
            _build_shell(
                content,
                selected_view=selected_view,
                on_dashboard=self.show_dashboard,
                on_tests=self.show_tests,
                on_new_test=self.show_new_test,
                on_agenda=self.show_agenda,
                on_history=self.show_history,
                on_settings=self.show_settings,
            )
        )
        self._page.update()

    def show_dashboard(self) -> None:
        content = build_dashboard(
            self._service.dashboard_summary(),
            self._service.list_dashboard_tests(),
            self._service.resource_statuses(),
            on_new_test=self.show_new_test,
            on_select=self.show_details,
            on_pause_resource=self._pause_resource,
            on_resume_resource=self._resume_resource,
        )
        self._render(content, selected_view="dashboard")

    def show_new_test(self) -> None:
        content = build_new_test_view(
            on_cancel=self.show_dashboard,
            on_save=self._save_test,
        )
        self._render(content, selected_view="new_test")

    def show_edit_test(self, test_id: int) -> None:
        content = build_edit_test_view(
            self._service.get_details(test_id),
            on_cancel=lambda: self.show_details(test_id),
            on_save=lambda command: self._update_test(test_id, command),
        )
        self._render(content, selected_view="details")

    def show_tests(self) -> None:
        content = build_tests_list_view(
            self._service.list_tests(),
            on_select=self.show_details,
            on_new_test=self.show_new_test,
            on_export=self._export_csv,
        )
        self._render(content, selected_view="tests")

    def show_history(self) -> None:
        content = build_history_view(
            self._service.list_history(),
            on_select=self.show_details,
        )
        self._render(content, selected_view="history")

    def show_agenda(self) -> None:
        content = build_agenda_view(
            self._service.list_agenda_events(),
            on_select=self.show_details,
        )
        self._render(content, selected_view="agenda")

    def show_settings(self) -> None:
        content = build_settings_view(
            database_path=get_database_path(),
            notifications_enabled=notification_task_installed(),
            notification_status=self._service.notification_status(),
            theme_mode=self._theme_mode,
            on_theme_change=self._change_theme,
            on_enable_notifications=lambda: self._configure_notifications(True),
            on_disable_notifications=lambda: self._configure_notifications(False),
            on_test_notification=self._test_notification,
            on_open_data_folder=self._open_data_folder,
            on_backup=self._backup_database,
        )
        self._render(content, selected_view="settings")

    def show_details(self, test_id: int) -> None:
        details = self._service.get_details(test_id)
        content = build_test_details_view(
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
            on_calendar=lambda: self._export_calendar(test_id),
            on_change_chamber_start=lambda value, reason: self._perform(
                test_id,
                lambda: self._service.change_chamber_start(test_id, value, reason),
                "Entrada da câmara alterada e prazos recalculados.",
            ),
            on_advance_for_testing=(
                lambda: (
                    self._perform(
                        test_id,
                        lambda: self._service.advance_for_testing(test_id),
                        "Etapa avançada somente para validação.",
                    )
                    if test_controls_enabled()
                    else None
                )
            ),
        )
        self._render(content, selected_view="details")

    def _save_test(self, command: CreateClimateTestCommand) -> None:
        test_id = self._service.create(command)
        self.show_dashboard()
        self._page.show_dialog(
            ft.SnackBar(
                content=f"Ensaio #{test_id} cadastrado com sucesso.",
                bgcolor=AppColors.PRIMARY,
                show_close_icon=True,
            )
        )

    def _update_test(self, test_id: int, command: UpdateClimateTestCommand) -> None:
        try:
            self._service.update(test_id, command)
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_details(test_id)
        self._show_message("Dados corrigidos e alteração registrada.")

    def _delete_test(self, test_id: int) -> None:
        try:
            self._service.delete_waiting(test_id)
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_tests()
        self._show_message(f"Cadastro do ensaio #{test_id} excluído.")

    def _pause_resource(self, resource: str, reason: str) -> None:
        try:
            affected = self._service.pause_resource(resource, reason)
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_dashboard()
        self._show_message(
            f"Equipamento pausado. {affected} ensaio(s) tiveram a contagem congelada."
        )

    def _resume_resource(self, resource: str) -> None:
        try:
            affected = self._service.resume_resource(resource)
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_dashboard()
        self._show_message(f"Equipamento retomado. {affected} prazo(s) foram recalculados.")

    def _change_theme(self, mode: str) -> None:
        self._theme_mode = "dark" if mode == "dark" else "light"
        AppColors.apply_mode(self._theme_mode)
        self._page.theme_mode = (
            ft.ThemeMode.DARK if self._theme_mode == "dark" else ft.ThemeMode.LIGHT
        )
        self._page.theme = ft.Theme(color_scheme_seed=AppColors.PRIMARY)
        self._page.bgcolor = AppColors.PAGE_BACKGROUND
        try:
            save_theme_mode(self._theme_mode)
        except OSError as error:
            self._show_message(
                f"O tema foi alterado, mas não foi possível salvar a preferência: {error}",
                error=True,
            )
        self.show_settings()

    def _perform(
        self,
        test_id: int,
        operation: Callable[[], None],
        success_message: str,
    ) -> None:
        try:
            operation()
        except (ValueError, LookupError) as error:
            self._show_message(str(error), error=True)
            return
        self.show_details(test_id)
        self._show_message(success_message)

    def _show_message(self, message: str, *, error: bool = False) -> None:
        self._page.show_dialog(
            ft.SnackBar(
                content=message,
                bgcolor=AppColors.DANGER if error else AppColors.PRIMARY,
                show_close_icon=True,
            )
        )

    async def _export_csv(self, tests: list[ClimateTestListItem]) -> None:
        file_name = f"ensaios_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = await ft.FilePicker().save_file(
            dialog_title="Escolha onde salvar a exportação dos ensaios",
            file_name=file_name,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["csv"],
            src_bytes=build_tests_csv_bytes(tests),
        )
        if path:
            self._show_message(f"CSV salvo com {len(tests)} ensaio(s) em: {path}")

    async def _backup_database(self, _event: object | None = None) -> None:
        database_path = get_database_path()
        try:
            backup_bytes = build_database_backup_bytes(database_path)
        except (OSError, ValueError) as error:
            self._show_message(str(error), error=True)
            return
        file_name = f"climatetest_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        path = await ft.FilePicker().save_file(
            dialog_title="Escolha onde salvar a cópia de segurança",
            file_name=file_name,
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["db"],
            src_bytes=backup_bytes,
        )
        if path:
            self._show_message(f"Cópia de segurança criada em: {path}")

    def _open_data_folder(self) -> None:
        folder = get_database_path().parent
        if not hasattr(os, "startfile"):
            self._show_message(
                f"A pasta dos dados é: {folder}",
                error=True,
            )
            return
        os.startfile(folder)  # type: ignore[attr-defined]

    def _test_notification(self) -> None:
        try:
            WindowsToastProvider().send(
                "ClimateTest Manager",
                "Notificação de teste enviada com sucesso.",
            )
        except Exception as error:  # pragma: no cover - integração do Windows
            self._show_message(
                f"Não foi possível exibir a notificação: {error}",
                error=True,
            )
            return
        self._show_message("Notificação de teste enviada.")

    def _export_calendar(self, test_id: int) -> None:
        try:
            path = export_test_calendar(self._service.get_details(test_id))
        except ValueError as error:
            self._show_message(str(error), error=True)
            return
        if hasattr(os, "startfile"):
            os.startfile(path)  # type: ignore[attr-defined]
        self._show_message(f"Arquivo de agenda criado em: {path}")

    def _configure_notifications(self, enable: bool) -> None:
        try:
            configure_notification_task(enable=enable)
        except RuntimeError as error:
            self._show_message(str(error), error=True)
            return
        self.show_settings()
        self._show_message(
            "Avisos em segundo plano ativados."
            if enable
            else "Avisos em segundo plano desativados."
        )


def main(page: ft.Page) -> None:
    """Inicializa o banco local e apresenta a janela desktop."""

    theme_mode = load_theme_mode()
    AppColors.apply_mode(theme_mode)
    page.title = "ClimateTest Manager"
    page.theme_mode = ft.ThemeMode.DARK if theme_mode == "dark" else ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=AppColors.PRIMARY)
    page.padding = 0
    page.spacing = 0
    page.bgcolor = AppColors.PAGE_BACKGROUND
    page.window.width = 1280
    page.window.height = 800
    page.window.min_width = 1000
    page.window.min_height = 680

    try:
        engine = initialize_database()
    except Exception as error:  # pragma: no cover - depende do sistema operacional
        page.add(
            ft.Container(
                padding=32,
                content=ft.Column(
                    controls=[
                        ft.Text(
                            "Não foi possível preparar o banco de dados.",
                            size=22,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.DANGER,
                        ),
                        ft.Text(str(error), color=AppColors.TEXT_SECONDARY),
                    ]
                ),
            )
        )
        return

    repository = ClimateTestRepository(create_session_factory(engine))
    page.on_close = lambda _event: engine.dispose()
    ClimateTestApplication(
        page,
        ClimateTestService(repository),
        theme_mode=theme_mode,
    ).start()
