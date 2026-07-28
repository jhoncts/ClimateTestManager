"""Agenda mensal interna para os prazos ativos de câmara e secagem."""

import calendar
from collections.abc import Callable
from datetime import date

import flet as ft

from climatetest_manager.services.climate_tests import AgendaEvent
from climatetest_manager.ui.formatters import format_datetime
from climatetest_manager.ui.theme import AppColors

MONTH_NAMES = (
    "",
    "Janeiro",
    "Fevereiro",
    "Março",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


class AgendaView:
    """Controla navegação mensal e seleção de um dia sem consultar serviço externo."""

    def __init__(
        self,
        events: list[AgendaEvent],
        *,
        on_select: Callable[[int], None],
        today_provider: Callable[[], date] = date.today,
    ) -> None:
        self._events = events
        self._on_select = on_select
        self._today = today_provider()
        self._month = self._today.replace(day=1)
        self._selected_date = self._today
        self.month_title = ft.Text(
            "",
            size=18,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
        self.calendar_grid = ft.Column(spacing=6)
        self.day_title = ft.Text(
            "",
            size=16,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
        self.day_events = ft.Column(spacing=8)
        self.root = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=18,
            controls=[
                ft.Column(
                    spacing=3,
                    controls=[
                        ft.Text(
                            "Agenda",
                            size=28,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                        ft.Text(
                            "Prazos de retirada dos ensaios ativos. Datas pausadas são "
                            "projeções e ficam definitivas ao retomar o equipamento.",
                            size=13,
                            color=AppColors.TEXT_SECONDARY,
                        ),
                    ],
                ),
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border_radius=16,
                    padding=20,
                    content=ft.Column(
                        spacing=12,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.CHEVRON_LEFT,
                                        on_click=lambda _event: self._move_month(-1),
                                    ),
                                    self.month_title,
                                    ft.IconButton(
                                        icon=ft.Icons.CHEVRON_RIGHT,
                                        on_click=lambda _event: self._move_month(1),
                                    ),
                                ],
                            ),
                            ft.Row(
                                controls=[
                                    ft.Container(
                                        expand=True,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Text(
                                            label,
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    )
                                    for label in ("Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom")
                                ]
                            ),
                            self.calendar_grid,
                        ],
                    ),
                ),
                ft.Container(
                    bgcolor=AppColors.SURFACE,
                    border_radius=16,
                    padding=20,
                    content=ft.Column(
                        spacing=12,
                        controls=[self.day_title, self.day_events],
                    ),
                ),
                ft.Container(height=8),
            ],
        )
        self._rebuild()

    def _events_on(self, selected_date: date) -> list[AgendaEvent]:
        return [event for event in self._events if event.occurs_at.date() == selected_date]

    def _move_month(self, offset: int) -> None:
        month_index = self._month.year * 12 + self._month.month - 1 + offset
        year, month_zero_based = divmod(month_index, 12)
        self._month = date(year, month_zero_based + 1, 1)
        self._selected_date = self._month
        self._rebuild()
        self._refresh()

    def _select_date(self, selected_date: date) -> None:
        self._selected_date = selected_date
        if selected_date.month != self._month.month:
            self._month = selected_date.replace(day=1)
        self._rebuild()
        self._refresh()

    def _rebuild(self) -> None:
        self.month_title.value = f"{MONTH_NAMES[self._month.month]} de {self._month.year}"
        weeks = calendar.Calendar(firstweekday=0).monthdatescalendar(
            self._month.year,
            self._month.month,
        )
        self.calendar_grid.controls = [
            ft.Row(
                spacing=6,
                controls=[self._day_cell(day) for day in week],
            )
            for week in weeks
        ]
        self.day_title.value = self._selected_date.strftime("Compromissos de %d/%m/%Y")
        events = self._events_on(self._selected_date)
        self.day_events.controls = (
            [self._event_row(event) for event in events]
            if events
            else [
                ft.Text(
                    "Nenhuma retirada programada para esta data.",
                    size=12,
                    color=AppColors.TEXT_SECONDARY,
                )
            ]
        )

    def _day_cell(self, day: date) -> ft.Container:
        events = self._events_on(day)
        selected = day == self._selected_date
        current_month = day.month == self._month.month
        color = AppColors.PRIMARY if selected else AppColors.TEXT_PRIMARY
        background = AppColors.PRIMARY_LIGHT if selected else AppColors.PAGE_BACKGROUND
        marker_controls: list[ft.Control] = []
        if events:
            marker_controls.append(
                ft.Container(
                    border_radius=12,
                    bgcolor=AppColors.INFO_LIGHT,
                    padding=ft.Padding.symmetric(horizontal=7, vertical=3),
                    content=ft.Text(
                        f"{len(events)} prazo(s)",
                        size=9,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.INFO,
                    ),
                )
            )
        return ft.Container(
            expand=True,
            height=72,
            border_radius=10,
            border=ft.Border.all(
                2 if selected else 1,
                AppColors.PRIMARY if selected else AppColors.DIVIDER,
            ),
            bgcolor=background,
            opacity=1 if current_month else 0.45,
            padding=8,
            on_click=lambda _event, selected_day=day: self._select_date(selected_day),
            content=ft.Column(
                spacing=5,
                controls=[
                    ft.Text(
                        str(day.day),
                        weight=ft.FontWeight.BOLD,
                        color=color,
                    ),
                    *marker_controls,
                ],
            ),
        )

    def _event_row(self, event: AgendaEvent) -> ft.Container:
        color = (
            AppColors.WARNING
            if event.is_paused
            else (AppColors.DANGER if event.kind == "Limite para retirada" else AppColors.PRIMARY)
        )
        return ft.Container(
            border_radius=12,
            bgcolor=AppColors.PAGE_BACKGROUND,
            padding=12,
            on_click=lambda _event: self._on_select(event.test_id),
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Row(
                        spacing=10,
                        expand=True,
                        controls=[
                            ft.Icon(ft.Icons.EVENT, color=color, size=20),
                            ft.Column(
                                spacing=2,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        f"{event.kind} • {event.phase}",
                                        weight=ft.FontWeight.BOLD,
                                        color=AppColors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        f"Processo {event.process_number} • {event.client}",
                                        size=11,
                                        color=AppColors.TEXT_SECONDARY,
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.END,
                        controls=[
                            ft.Text(
                                format_datetime(event.occurs_at),
                                weight=ft.FontWeight.BOLD,
                                color=color,
                            ),
                            *(
                                [
                                    ft.Text(
                                        "Projeção durante pausa",
                                        size=9,
                                        color=AppColors.WARNING,
                                    )
                                ]
                                if event.is_paused
                                else []
                            ),
                        ],
                    ),
                ],
            ),
        )

    def _refresh(self) -> None:
        try:
            _page = self.root.page
        except RuntimeError:
            return
        self.root.update()


def build_agenda_view(
    events: list[AgendaEvent],
    *,
    on_select: Callable[[int], None],
) -> ft.Column:
    """Cria a agenda mensal interna."""

    return AgendaView(events, on_select=on_select).root
