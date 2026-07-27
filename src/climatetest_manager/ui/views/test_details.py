"""Detalhes operacionais, comandos de etapa e histórico auditável."""

from collections.abc import Callable
from contextlib import suppress
from datetime import datetime

import flet as ft

from climatetest_manager.domain.enums import ConditionInputMode
from climatetest_manager.services.climate_tests import ClimateTestDetails
from climatetest_manager.ui.formatters import (
    format_condition_source,
    format_datetime,
    format_decimal,
    format_duration_detail,
    format_thermal_summary,
    normalize_date_input,
    normalize_time_input,
    parse_local_datetime,
)
from climatetest_manager.ui.theme import AppColors


def _masked_datetime_field(
    *,
    label: str,
    value: str,
    hint_text: str,
    width: int,
    is_date: bool,
) -> ft.TextField:
    """Cria um campo numérico com máscara progressiva de data ou hora."""

    normalizer = normalize_date_input if is_date else normalize_time_input
    max_length = 10 if is_date else 5
    field = ft.TextField(
        label=label,
        value=value,
        hint_text=hint_text,
        width=width,
        max_length=max_length,
        counter="",
        keyboard_type=ft.KeyboardType.NUMBER,
        border_radius=10,
    )

    def normalize(_event: object | None = None) -> None:
        masked = normalizer(field.value)
        if masked == field.value:
            return
        field.value = masked
        field.selection = ft.TextSelection(
            base_offset=len(masked),
            extent_offset=len(masked),
        )
        with suppress(RuntimeError):
            field.update()

    field.on_change = normalize
    return field


def _value(label: str, value: str) -> ft.Column:
    return ft.Column(
        expand=True,
        spacing=2,
        controls=[
            ft.Text(label, size=11, color=AppColors.TEXT_SECONDARY),
            ft.Text(value, size=14, weight=ft.FontWeight.BOLD, color=AppColors.TEXT_PRIMARY),
        ],
    )


def _panel(title: str, controls: list[ft.Control]) -> ft.Container:
    return ft.Container(
        bgcolor=AppColors.SURFACE,
        border_radius=16,
        padding=20,
        content=ft.Column(
            spacing=14,
            controls=[
                ft.Text(
                    title,
                    size=16,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                *controls,
            ],
        ),
    )


def _schedule_item(label: str, value: str, icon: ft.IconData) -> ft.Container:
    return ft.Container(
        expand=True,
        border_radius=12,
        bgcolor=AppColors.PAGE_BACKGROUND,
        padding=12,
        content=ft.Row(
            spacing=9,
            controls=[
                ft.Icon(icon, size=19, color=AppColors.PRIMARY),
                ft.Column(
                    spacing=2,
                    controls=[
                        ft.Text(label, size=10, color=AppColors.TEXT_SECONDARY),
                        ft.Text(value, size=12, weight=ft.FontWeight.BOLD),
                    ],
                ),
            ],
        ),
    )


def _stage_card(title: str, status: str, summary: str, *, active: bool) -> ft.Container:
    color = AppColors.PRIMARY if active else AppColors.TEXT_SECONDARY
    return ft.Container(
        width=205,
        height=116,
        border_radius=14,
        border=ft.Border.all(2 if active else 1, color),
        bgcolor=AppColors.PRIMARY_LIGHT if active else AppColors.PAGE_BACKGROUND,
        padding=14,
        content=ft.Column(
            spacing=5,
            controls=[
                ft.Text(title, size=13, weight=ft.FontWeight.BOLD),
                ft.Text(status, size=11, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(summary, size=10, color=AppColors.TEXT_SECONDARY),
            ],
        ),
    )


def _thermal_summary(details: ClimateTestDetails) -> ft.Control:
    source = _value("Origem da condição", format_condition_source(details.input_mode))
    if details.input_mode == ConditionInputMode.CALCULATED.value:
        return ft.Column(
            spacing=12,
            controls=[
                ft.Row(
                    controls=[
                        source,
                        _value("EPL", details.epl),
                        _value("Alternativa", f"Opção {details.selected_option}"),
                    ]
                ),
                ft.Row(
                    controls=[
                        _value("Tamb", f"{format_decimal(details.tamb_max_c)} °C"),
                        _value("Delta T", f"{format_decimal(details.delta_t_max_k)} K"),
                        _value(
                            "Ts calculado",
                            f"{format_decimal(details.service_temperature_c)} °C",
                        ),
                    ]
                ),
            ],
        )
    if details.input_mode == ConditionInputMode.DIRECT_TS.value:
        return ft.Row(
            controls=[
                source,
                _value("EPL", details.epl),
                _value("Ts informado", f"{format_decimal(details.service_temperature_c)} °C"),
                _value("Alternativa", f"Opção {details.selected_option}"),
            ]
        )
    return ft.Row(
        controls=[
            source,
            _value(
                "Informação registrada",
                format_thermal_summary(
                    input_mode=details.input_mode,
                    epl=details.epl,
                    service_temperature_c=details.service_temperature_c,
                    ts_reference=details.ts_reference,
                    selected_option=details.selected_option,
                ),
            ),
        ]
    )


class TestDetailsView:
    """Apresenta um ensaio e coleta datas manuais sem esconder o horário real."""

    def __init__(
        self,
        details: ClimateTestDetails,
        *,
        on_back: Callable[[], None],
        on_start_chamber: Callable[[datetime | None], None],
        on_start_drying: Callable[[datetime | None], None],
        on_finish: Callable[[datetime | None], None],
        on_cancel: Callable[[str], None],
        on_edit: Callable[[], None],
        on_delete: Callable[[], None],
        on_calendar: Callable[[], None],
        on_change_chamber_start: Callable[[datetime, str], None],
        on_advance_for_testing: Callable[[], None] | None = None,
    ) -> None:
        self._details = details
        self._on_start_chamber = on_start_chamber
        self._on_start_drying = on_start_drying
        self._on_finish = on_finish
        self._on_cancel = on_cancel
        self._on_delete = on_delete
        self._on_change_chamber_start = on_change_chamber_start
        self._on_advance_for_testing = on_advance_for_testing
        now = datetime.now()
        self.date = _masked_datetime_field(
            label="Data",
            value=now.strftime("%d/%m/%Y"),
            hint_text="DD/MM/AAAA",
            width=170,
            is_date=True,
        )
        self.time = _masked_datetime_field(
            label="Hora",
            value=now.strftime("%H:%M"),
            hint_text="HH:MM",
            width=130,
            is_date=False,
        )
        self.manual_error = ft.Text("", size=12, color=AppColors.DANGER)
        self.cancel_reason = ft.TextField(
            label="Motivo obrigatório",
            hint_text="Explique por que o ensaio está sendo cancelado",
            border_radius=10,
            expand=True,
        )

        header_actions: list[ft.Control] = [
            ft.Button(
                content="Corrigir dados",
                icon=ft.Icons.EDIT,
                on_click=lambda _event: on_edit(),
            )
        ]
        if details.chamber_started_at:
            header_actions.append(
                ft.Button(
                    content="Alterar entrada da câmara",
                    icon=ft.Icons.EDIT_CALENDAR,
                    on_click=lambda _event: self._show_change_chamber_start(),
                )
            )
            header_actions.append(
                ft.Button(
                    content="Adicionar à agenda",
                    icon=ft.Icons.EVENT,
                    on_click=lambda _event: on_calendar(),
                )
            )

        self.root = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=18,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    controls=[
                        ft.Row(
                            spacing=12,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ARROW_BACK,
                                    on_click=lambda _event: on_back(),
                                ),
                                ft.Column(
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            f"Ensaio #{details.id}",
                                            size=27,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Text(
                                            f"{details.client} • processo {details.process_number}",
                                            size=13,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Row(controls=header_actions),
                    ],
                ),
                _panel(
                    "Resumo",
                    [
                        ft.Row(
                            controls=[
                                _value(
                                    "Situação",
                                    (
                                        f"Pausado — {details.situation}"
                                        if details.is_paused
                                        else details.situation
                                    ),
                                ),
                                _value("Condição", details.deadline_condition or "Sem prazo ativo"),
                                _value("Produto", details.product),
                                _value("Amostras", str(details.sample_quantity)),
                            ]
                        ),
                        ft.Row(
                            controls=[
                                ft.ProgressBar(
                                    value=details.progress_percent,
                                    width=260,
                                    height=8,
                                    color=(
                                        AppColors.WARNING
                                        if details.is_paused
                                        else AppColors.PRIMARY
                                    ),
                                    bgcolor=AppColors.DIVIDER,
                                    border_radius=6,
                                ),
                                ft.Text(
                                    details.progress_label,
                                    size=11,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ]
                        ),
                        *(
                            [
                                ft.Text(
                                    f"Motivo da pausa: {details.pause_reason}",
                                    size=11,
                                    color=AppColors.WARNING,
                                )
                            ]
                            if details.is_paused
                            else []
                        ),
                        _thermal_summary(details),
                    ],
                ),
                self._journey_panel(),
                self._phase_panel(),
                self._action_panel(),
                self._history_panel(),
                ft.Container(height=8),
            ],
        )

    def _journey_panel(self) -> ft.Container:
        details = self._details
        chamber_status = (
            "Concluída"
            if details.chamber_ended_at
            else "Pausada"
            if details.is_paused and details.situation == "Na Câmara"
            else "Em andamento"
            if details.chamber_started_at
            else "Pendente"
        )
        drying_status = (
            "Não requerida"
            if not details.drying_required
            else "Concluída"
            if details.drying_ended_at
            else "Pausada"
            if details.is_paused and details.situation == "Em Secagem"
            else "Em andamento"
            if details.drying_started_at
            else "Pendente"
        )
        final_status = (
            "Cancelado"
            if details.cancelled_at
            else "Finalizado"
            if details.finished_at
            else "Pendente"
        )
        stages: list[ft.Control] = [
            _stage_card(
                "1. Ensaio cadastrado",
                "Concluído",
                f"{details.sample_quantity} amostra(s) • processo {details.process_number}",
                active=details.situation == "Aguardando",
            ),
            ft.Icon(ft.Icons.ARROW_FORWARD, color=AppColors.TEXT_SECONDARY),
            _stage_card(
                "2. Câmara climática",
                chamber_status,
                (
                    f"Início: {format_datetime(details.chamber_started_at)}"
                    if details.chamber_started_at
                    else "Aguardando registro de entrada"
                ),
                active=details.situation == "Na Câmara",
            ),
        ]
        if details.drying_required:
            stages.extend(
                [
                    ft.Icon(ft.Icons.ARROW_FORWARD, color=AppColors.TEXT_SECONDARY),
                    _stage_card(
                        "3. Secagem",
                        drying_status,
                        (
                            f"Início: {format_datetime(details.drying_started_at)}"
                            if details.drying_started_at
                            else "Aguardando retirada da câmara"
                        ),
                        active=details.situation == "Em Secagem",
                    ),
                ]
            )
        stages.extend(
            [
                ft.Icon(ft.Icons.ARROW_FORWARD, color=AppColors.TEXT_SECONDARY),
                _stage_card(
                    "Etapa final",
                    final_status,
                    (
                        f"Conclusão: {format_datetime(details.finished_at)}"
                        if details.finished_at
                        else f"Cancelamento: {format_datetime(details.cancelled_at)}"
                        if details.cancelled_at
                        else "Aguardando conclusão operacional"
                    ),
                    active=details.situation in {"Finalizado", "Cancelado"},
                ),
            ]
        )
        return _panel(
            "Caminho do ensaio",
            [
                ft.Text(
                    "Resumo visual das etapas realizadas e da etapa atual.",
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                ),
                ft.Row(scroll=ft.ScrollMode.AUTO, controls=stages),
            ],
        )

    def _phase_panel(self) -> ft.Container:
        details = self._details
        chamber_condition = ft.Container(
            expand=True,
            border_radius=14,
            bgcolor=AppColors.PAGE_BACKGROUND,
            padding=16,
            content=ft.Column(
                spacing=8,
                controls=[
                    ft.Text(
                        "Condição da câmara",
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.PRIMARY,
                    ),
                    ft.Row(
                        controls=[
                            _value(
                                "Temperatura",
                                f"{format_decimal(details.chamber_temperature_c)} ± 2 °C",
                            ),
                            _value(
                                "Umidade",
                                f"{format_decimal(details.chamber_humidity_percent)} ± 5% UR",
                            ),
                            _value(
                                "Permanência",
                                f"{details.chamber_duration_hours} h "
                                f"(+{details.chamber_duration_tolerance_hours} h)",
                            ),
                        ]
                    ),
                    ft.Text(
                        format_duration_detail(
                            details.chamber_duration_hours,
                            details.chamber_duration_tolerance_hours,
                        ),
                        size=11,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
        )
        chamber_schedule = ft.Column(
            spacing=9,
            controls=[
                ft.Text("Cronograma da câmara", weight=ft.FontWeight.BOLD),
                ft.Row(
                    controls=[
                        _schedule_item(
                            "Entrada registrada",
                            format_datetime(details.chamber_started_at),
                            ft.Icons.LOGIN,
                        ),
                        _schedule_item(
                            "Retirada recomendada",
                            format_datetime(details.chamber_nominal_end_at),
                            ft.Icons.EVENT_AVAILABLE,
                        ),
                        _schedule_item(
                            "Último prazo permitido",
                            format_datetime(details.chamber_maximum_end_at),
                            ft.Icons.WARNING_AMBER,
                        ),
                        _schedule_item(
                            "Retirada registrada",
                            format_datetime(details.chamber_ended_at),
                            ft.Icons.LOGOUT,
                        ),
                    ]
                ),
            ],
        )
        controls: list[ft.Control] = [
            chamber_condition,
            chamber_schedule,
        ]
        if details.drying_required:
            controls.extend(
                [
                    ft.Divider(height=1, color=AppColors.DIVIDER),
                    ft.Container(
                        expand=True,
                        border_radius=14,
                        bgcolor=AppColors.PAGE_BACKGROUND,
                        padding=16,
                        content=ft.Column(
                            spacing=8,
                            controls=[
                                ft.Text(
                                    "Condição da secagem",
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.DRYING,
                                ),
                                ft.Row(
                                    controls=[
                                        _value(
                                            "Temperatura",
                                            f"{format_decimal(details.drying_temperature_c or '0')}"
                                            " ± 2 °C",
                                        ),
                                        _value(
                                            "Permanência",
                                            f"{details.drying_duration_hours} h "
                                            f"(+{details.drying_duration_tolerance_hours} h)",
                                        ),
                                    ]
                                ),
                                ft.Text(
                                    format_duration_detail(
                                        details.drying_duration_hours or 0,
                                        details.drying_duration_tolerance_hours or 0,
                                    ),
                                    size=11,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ),
                    ft.Text("Cronograma da secagem", weight=ft.FontWeight.BOLD),
                    ft.Row(
                        controls=[
                            _schedule_item(
                                "Entrada registrada",
                                format_datetime(details.drying_started_at),
                                ft.Icons.LOGIN,
                            ),
                            _schedule_item(
                                "Retirada recomendada",
                                format_datetime(details.drying_nominal_end_at),
                                ft.Icons.EVENT_AVAILABLE,
                            ),
                            _schedule_item(
                                "Último prazo permitido",
                                format_datetime(details.drying_maximum_end_at),
                                ft.Icons.WARNING_AMBER,
                            ),
                            _schedule_item(
                                "Retirada registrada",
                                format_datetime(details.drying_ended_at),
                                ft.Icons.LOGOUT,
                            ),
                        ]
                    ),
                ]
            )
        else:
            controls.append(
                ft.Text(
                    "Esta condição não exige etapa de secagem.",
                    size=12,
                    color=AppColors.TEXT_SECONDARY,
                )
            )
        return _panel("Condição do ensaio e cronograma", controls)

    def _action_panel(self) -> ft.Container:
        details = self._details
        action_buttons: list[ft.Control] = []
        active_situations = {"Aguardando", "Na Câmara", "Em Secagem"}
        if details.is_paused:
            action_buttons = []
        elif details.situation == "Aguardando":
            action_buttons = [
                ft.Button(
                    content="Iniciar câmara agora",
                    icon=ft.Icons.PLAY_ARROW,
                    bgcolor=AppColors.PRIMARY,
                    color=AppColors.WHITE,
                    on_click=lambda _event: self._on_start_chamber(None),
                ),
                ft.Button(
                    content="Registrar horário informado",
                    icon=ft.Icons.EDIT_CALENDAR,
                    on_click=lambda _event: self._manual(self._on_start_chamber),
                ),
            ]
        elif details.situation == "Na Câmara":
            label = "Iniciar secagem agora" if details.drying_required else "Finalizar agora"
            callback = self._on_start_drying if details.drying_required else self._on_finish
            action_buttons = [
                ft.Button(
                    content=label,
                    icon=ft.Icons.AIR if details.drying_required else ft.Icons.CHECK,
                    bgcolor=AppColors.PRIMARY,
                    color=AppColors.WHITE,
                    on_click=lambda _event: callback(None),
                ),
                ft.Button(
                    content="Registrar horário informado",
                    icon=ft.Icons.EDIT_CALENDAR,
                    on_click=lambda _event: self._manual(callback),
                ),
            ]
        elif details.situation == "Em Secagem":
            action_buttons = [
                ft.Button(
                    content="Finalizar agora",
                    icon=ft.Icons.CHECK,
                    bgcolor=AppColors.PRIMARY,
                    color=AppColors.WHITE,
                    on_click=lambda _event: self._on_finish(None),
                ),
                ft.Button(
                    content="Registrar horário informado",
                    icon=ft.Icons.EDIT_CALENDAR,
                    on_click=lambda _event: self._manual(self._on_finish),
                ),
            ]

        controls: list[ft.Control] = []
        if details.is_paused:
            controls.append(
                ft.Container(
                    border_radius=12,
                    bgcolor=AppColors.WARNING_LIGHT,
                    padding=14,
                    content=ft.Text(
                        "A contagem está congelada. Retome o equipamento no Dashboard "
                        "antes de avançar ou finalizar esta etapa.",
                        size=12,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                )
            )
        elif action_buttons:
            controls.extend(
                [
                    ft.Text(
                        "Use “agora” ou informe o horário real se o registro foi feito depois.",
                        size=12,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                    ft.Row(spacing=10, controls=[self.date, self.time, *action_buttons]),
                    self.manual_error,
                ]
            )
        else:
            controls.append(
                ft.Text(
                    "Este ensaio está encerrado e não possui ações operacionais pendentes.",
                    color=AppColors.TEXT_SECONDARY,
                )
            )
        if details.situation in active_situations:
            controls.extend(
                [
                    ft.Divider(height=1, color=AppColors.DIVIDER),
                    ft.Row(
                        controls=[
                            self.cancel_reason,
                            ft.Button(
                                content="Cancelar ensaio",
                                icon=ft.Icons.CANCEL_OUTLINED,
                                color=AppColors.DANGER,
                                on_click=lambda _event: self._cancel(),
                            ),
                        ]
                    ),
                ]
            )
        if details.situation == "Aguardando":
            controls.extend(
                [
                    ft.Divider(height=1, color=AppColors.DIVIDER),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text(
                                "Cadastros ainda não iniciados podem ser excluídos "
                                "permanentemente.",
                                size=11,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                            ft.Button(
                                content="Excluir cadastro",
                                icon=ft.Icons.DELETE_OUTLINE,
                                color=AppColors.DANGER,
                                on_click=lambda _event: self._confirm_delete(),
                            ),
                        ],
                    ),
                ]
            )
        if self._on_advance_for_testing is not None and details.situation in active_situations:
            controls.extend(
                [
                    ft.Divider(height=1, color=AppColors.DIVIDER),
                    ft.Container(
                        border_radius=12,
                        bgcolor=AppColors.INFO_LIGHT,
                        padding=12,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Text(
                                    "Ferramenta temporária: ignora a espera para validar telas.",
                                    size=11,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                                ft.Button(
                                    content="Teste: avançar etapa",
                                    icon=ft.Icons.SKIP_NEXT,
                                    on_click=lambda _event: self._confirm_test_advance(),
                                ),
                            ],
                        ),
                    ),
                ]
            )
        return _panel("Ações operacionais", controls)

    def _history_panel(self) -> ft.Container:
        rows: list[ft.Control] = []
        for event in reversed(self._details.audit_events):
            description = event.new_value or event.reason or "Evento registrado"
            if "; regra=" in description:
                description = description.split("; regra=", maxsplit=1)[0]
            change_controls: list[ft.Control] = []
            if event.old_value:
                change_controls.append(
                    ft.Text(
                        f"Antes: {event.old_value}",
                        size=10,
                        color=AppColors.TEXT_SECONDARY,
                    )
                )
            rows.append(
                ft.Container(
                    border=ft.Border(left=ft.BorderSide(3, AppColors.PRIMARY_LIGHT)),
                    padding=ft.Padding.only(left=12, top=6, bottom=6),
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Text(event.action, weight=ft.FontWeight.BOLD),
                            ft.Text(description, size=12, color=AppColors.TEXT_SECONDARY),
                            *change_controls,
                            *(
                                [
                                    ft.Text(
                                        f"Motivo: {event.reason}",
                                        size=10,
                                        color=AppColors.TEXT_SECONDARY,
                                    )
                                ]
                                if event.reason and event.reason != description
                                else []
                            ),
                            ft.Text(
                                f"{format_datetime(event.occurred_at)} • {event.actor}",
                                size=10,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                )
            )
        return _panel("Registro técnico detalhado", rows)

    def _show_change_chamber_start(self) -> None:
        started_at = self._details.chamber_started_at
        if started_at is None:
            return
        date_field = _masked_datetime_field(
            label="Nova data",
            value=started_at.strftime("%d/%m/%Y"),
            width=180,
            hint_text="DD/MM/AAAA",
            is_date=True,
        )
        time_field = _masked_datetime_field(
            label="Nova hora",
            value=started_at.strftime("%H:%M"),
            width=140,
            hint_text="HH:MM",
            is_date=False,
        )
        reason_field = ft.TextField(
            label="Motivo obrigatório",
            hint_text="Ex.: correção do horário registrado",
            multiline=True,
            min_lines=2,
            max_lines=3,
        )
        error_text = ft.Text("", size=11, color=AppColors.DANGER)
        page = self.root.page

        def confirm(_event: object | None = None) -> None:
            try:
                new_start = parse_local_datetime(date_field.value, time_field.value)
            except ValueError as error:
                error_text.value = str(error)
                error_text.update()
                return
            reason = reason_field.value.strip()
            if not reason:
                reason_field.error = "Informe o motivo da alteração."
                reason_field.update()
                return
            page.pop_dialog()
            self._on_change_chamber_start(new_start, reason)

        page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Alterar entrada da câmara"),
                content=ft.Column(
                    tight=True,
                    spacing=10,
                    controls=[
                        ft.Text(
                            "O prazo da câmara será recalculado e os valores anterior e "
                            "novo ficarão registrados na trilha de atividades.",
                            size=12,
                        ),
                        ft.Row(controls=[date_field, time_field]),
                        reason_field,
                        error_text,
                    ],
                ),
                actions=[
                    ft.TextButton(
                        content="Cancelar",
                        on_click=lambda _event: page.pop_dialog(),
                    ),
                    ft.TextButton(content="Salvar alteração", on_click=confirm),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )

    def _confirm_test_advance(self) -> None:
        if self._on_advance_for_testing is None:
            return
        self._show_confirmation(
            "Avançar etapa somente para teste?",
            "A ação ficará registrada e não deve ser usada para um ensaio real.",
            self._on_advance_for_testing,
            confirm_label="Sim, avançar",
            danger=False,
        )

    def _manual(self, callback: Callable[[datetime | None], None]) -> None:
        try:
            value = parse_local_datetime(self.date.value, self.time.value)
        except ValueError as error:
            self.manual_error.value = str(error)
            self.manual_error.update()
            return
        callback(value)

    def _cancel(self) -> None:
        reason = self.cancel_reason.value.strip()
        if not reason:
            self.manual_error.value = "Informe o motivo do cancelamento."
            self.manual_error.update()
            return

        def confirm() -> None:
            self._on_cancel(reason)

        self._show_confirmation(
            "Cancelar este ensaio?",
            "O ensaio permanecerá no sistema como cancelado e o motivo será registrado.",
            confirm,
            confirm_label="Sim, cancelar",
        )

    def _confirm_delete(self) -> None:
        self._show_confirmation(
            "Excluir este cadastro?",
            "Essa ação é permanente. Use-a apenas para um cadastro incorreto que ainda "
            "não iniciou a câmara.",
            self._on_delete,
            confirm_label="Sim, excluir",
        )

    def _show_confirmation(
        self,
        title: str,
        message: str,
        on_confirm: Callable[[], None],
        *,
        confirm_label: str,
        danger: bool = True,
    ) -> None:
        page = self.root.page

        def confirm(_event: object | None = None) -> None:
            page.pop_dialog()
            on_confirm()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(title),
            content=ft.Text(message),
            actions=[
                ft.TextButton(content="Não", on_click=lambda _event: page.pop_dialog()),
                ft.TextButton(
                    content=confirm_label,
                    on_click=confirm,
                    style=ft.ButtonStyle(color=AppColors.DANGER if danger else AppColors.PRIMARY),
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(dialog)


def build_test_details_view(
    details: ClimateTestDetails,
    *,
    on_back: Callable[[], None],
    on_start_chamber: Callable[[datetime | None], None],
    on_start_drying: Callable[[datetime | None], None],
    on_finish: Callable[[datetime | None], None],
    on_cancel: Callable[[str], None],
    on_edit: Callable[[], None],
    on_delete: Callable[[], None],
    on_calendar: Callable[[], None],
    on_change_chamber_start: Callable[[datetime, str], None],
    on_advance_for_testing: Callable[[], None] | None = None,
) -> ft.Column:
    """Cria a tela de detalhes do ensaio informado."""

    return TestDetailsView(
        details,
        on_back=on_back,
        on_start_chamber=on_start_chamber,
        on_start_drying=on_start_drying,
        on_finish=on_finish,
        on_cancel=on_cancel,
        on_edit=on_edit,
        on_delete=on_delete,
        on_calendar=on_calendar,
        on_change_chamber_start=on_change_chamber_start,
        on_advance_for_testing=on_advance_for_testing,
    ).root
