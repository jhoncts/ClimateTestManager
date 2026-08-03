"""Detalhes operacionais, comandos de etapa e histórico auditável."""

from collections.abc import Callable
from contextlib import suppress
from datetime import datetime, timedelta

import flet as ft

from climatetest_manager.domain.enums import ConditionInputMode, OperationalTimestamp
from climatetest_manager.services.climate_tests import ClimateTestDetails
from climatetest_manager.ui.components import (
    ReasonSelector,
    dialog_actions,
    dialog_banner,
    section_heading,
    styled_dialog,
)
from climatetest_manager.ui.formatters import (
    format_condition_source,
    format_datetime,
    format_decimal,
    format_duration_detail,
    format_operational_date,
    normalize_date_input,
    normalize_time_input,
    parse_local_datetime,
)
from climatetest_manager.ui.theme import AppColors

TIMESTAMP_REASON_OPTIONS = (
    "Erro de digitação",
    "Registro realizado após a operação",
    "Correção após conferência documental",
    "Ajuste solicitado pelo responsável",
)

CANCELLATION_REASON_OPTIONS = (
    "Danos evidentes na amostra",
    "Cadastro incorreto",
    "Processo cancelado pelo cliente",
    "Processo suspenso / stand by",
    "Condição de ensaio revisada",
)


def _operational_date_card(
    label: str,
    value: datetime,
    *,
    icon: ft.IconData,
    color: str,
    background: str,
    emphasized: bool = False,
) -> ft.Container:
    """Exibe um prazo como informação operacional, não como texto auxiliar."""

    weekday, date_text, time_text = format_operational_date(value)
    is_weekend = value.weekday() >= 5
    return ft.Container(
        col={"xs": 12, "sm": 4},
        height=166,
        border_radius=14,
        bgcolor=background,
        border=ft.Border.all(2 if emphasized else 1, color),
        padding=14,
        content=ft.Column(
            spacing=5,
            controls=[
                ft.Row(
                    spacing=7,
                    controls=[
                        ft.Icon(icon, color=color, size=19),
                        ft.Text(
                            label,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=color,
                            expand=True,
                        ),
                    ],
                ),
                ft.Text(
                    weekday,
                    size=14,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text(
                    date_text,
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.TEXT_PRIMARY,
                ),
                ft.Text(
                    f"às {time_text}",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color=color,
                ),
                *(
                    [
                        ft.Container(
                            border_radius=10,
                            bgcolor=AppColors.DANGER_LIGHT,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            content=ft.Text(
                                "FIM DE SEMANA",
                                size=9,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.DANGER,
                            ),
                        )
                    ]
                    if is_weekend
                    else []
                ),
            ],
        ),
    )


def _chamber_start_summary(
    entry_at: datetime,
    nominal_end_at: datetime,
    maximum_end_at: datetime,
) -> ft.Column:
    """Monta a confirmação visual dos três horários que orientam a operação."""

    weekend_deadlines: list[str] = []
    if nominal_end_at.weekday() >= 5:
        weekend_deadlines.append("a retirada nominal")
    if maximum_end_at.weekday() >= 5:
        weekend_deadlines.append("o limite com tolerância")
    deadline_verb = "ocorrerá" if len(weekend_deadlines) == 1 else "ocorrerão"
    guidance = (
        f"Atenção: {' e '.join(weekend_deadlines)} {deadline_verb} no fim de semana. "
        "Confirme se a equipe poderá realizar a retirada."
        if weekend_deadlines
        else "Confira principalmente o dia da semana da retirada antes de registrar a entrada."
    )
    return ft.Column(
        width=720,
        tight=True,
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            ft.ResponsiveRow(
                spacing=12,
                run_spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    _operational_date_card(
                        "ENTRADA",
                        entry_at,
                        icon=ft.Icons.LOGIN,
                        color=AppColors.PRIMARY,
                        background=AppColors.PRIMARY_LIGHT,
                    ),
                    _operational_date_card(
                        "RETIRADA NOMINAL",
                        nominal_end_at,
                        icon=ft.Icons.EVENT_AVAILABLE,
                        color=AppColors.INFO,
                        background=AppColors.INFO_LIGHT,
                    ),
                    _operational_date_card(
                        "LIMITE COM TOLERÂNCIA",
                        maximum_end_at,
                        icon=ft.Icons.WARNING_AMBER,
                        color=AppColors.WARNING,
                        background=AppColors.WARNING_LIGHT,
                        emphasized=True,
                    ),
                ],
            ),
            dialog_banner(
                guidance,
                icon=(ft.Icons.WARNING_AMBER if weekend_deadlines else ft.Icons.INFO_OUTLINE),
                warning=bool(weekend_deadlines),
            ),
        ],
    )


def _masked_datetime_field(
    *,
    label: str,
    value: str,
    hint_text: str,
    width: int | None,
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


def _value(
    label: str,
    value: str,
    *,
    col: dict[str, int] | None = None,
) -> ft.Column:
    return ft.Column(
        col=col or {"xs": 12, "sm": 6, "lg": 4},
        spacing=2,
        controls=[
            ft.Text(label, size=11, color=AppColors.TEXT_SECONDARY),
            ft.Text(
                value,
                size=14,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            ),
        ],
    )


def _panel(
    title: str,
    controls: list[ft.Control],
    *,
    help_text: str | None = None,
) -> ft.Container:
    return ft.Container(
        bgcolor=AppColors.SURFACE,
        border_radius=16,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=20,
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                (
                    section_heading(title, help_text, size=16)
                    if help_text
                    else ft.Text(
                        title,
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    )
                ),
                *controls,
            ],
        ),
    )


def _schedule_item(label: str, value: str, icon: ft.IconData) -> ft.Container:
    return ft.Container(
        border_radius=10,
        padding=ft.Padding.symmetric(horizontal=10, vertical=9),
        content=ft.Row(
            spacing=11,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=32,
                    height=32,
                    border_radius=10,
                    bgcolor=AppColors.SURFACE,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, size=18, color=AppColors.PRIMARY),
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(label, size=10, color=AppColors.TEXT_SECONDARY),
                        ft.Text(
                            value,
                            size=12,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                    ],
                ),
            ],
        ),
    )


def _phase_card(
    *,
    title: str,
    subtitle: str,
    icon: ft.IconData,
    accent: str,
    accent_background: str,
    condition_values: list[ft.Control],
    duration_detail: str,
    schedule: list[tuple[str, str, ft.IconData]],
) -> ft.Container:
    """Agrupa condição e prazos de uma etapa em um cartão legível."""

    schedule_rows: list[ft.Control] = []
    for index, (label, value, schedule_icon) in enumerate(schedule):
        schedule_rows.append(_schedule_item(label, value, schedule_icon))
        if index < len(schedule) - 1:
            schedule_rows.append(ft.Divider(height=1, color=AppColors.DIVIDER))
    return ft.Container(
        col={"xs": 12, "lg": 6},
        border_radius=15,
        bgcolor=AppColors.PAGE_BACKGROUND,
        border=ft.Border.all(1, AppColors.DIVIDER),
        padding=18,
        content=ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    spacing=11,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            width=42,
                            height=42,
                            border_radius=13,
                            bgcolor=accent_background,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(icon, color=accent, size=22),
                        ),
                        ft.Column(
                            expand=True,
                            spacing=1,
                            controls=[
                                ft.Text(
                                    title,
                                    size=15,
                                    weight=ft.FontWeight.BOLD,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                                ft.Text(
                                    subtitle,
                                    size=10,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ],
                ),
                ft.ResponsiveRow(
                    spacing=10,
                    run_spacing=8,
                    controls=condition_values,
                ),
                ft.Text(
                    duration_detail,
                    size=10,
                    color=AppColors.TEXT_SECONDARY,
                    no_wrap=False,
                ),
                ft.Divider(height=1, color=AppColors.DIVIDER),
                ft.Text(
                    "Cronograma",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color=accent,
                ),
                ft.Column(
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=schedule_rows,
                ),
            ],
        ),
    )


def _stage_card(title: str, status: str, summary: str, *, active: bool) -> ft.Container:
    color = AppColors.PRIMARY if active else AppColors.TEXT_SECONDARY
    return ft.Container(
        width=205,
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


def _summary_item(
    label: str,
    value: str,
    icon: ft.IconData,
) -> ft.Container:
    """Separa informações de identificação sem competir visualmente com o Ts."""

    return ft.Container(
        col={"xs": 12, "sm": 6},
        border_radius=12,
        bgcolor=AppColors.PAGE_BACKGROUND,
        padding=12,
        content=ft.Row(
            spacing=9,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Icon(icon, size=18, color=AppColors.PRIMARY),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(label, size=10, color=AppColors.TEXT_SECONDARY),
                        ft.Text(
                            value,
                            size=13,
                            weight=ft.FontWeight.BOLD,
                            color=AppColors.TEXT_PRIMARY,
                        ),
                    ],
                ),
            ],
        ),
    )


def _ts_highlight(details: ClimateTestDetails) -> ft.Container:
    """Transforma o Ts na leitura principal do resumo térmico."""

    has_numeric_ts = details.input_mode in {
        ConditionInputMode.CALCULATED.value,
        ConditionInputMode.DIRECT_TS.value,
    }
    if details.input_mode == ConditionInputMode.CALCULATED.value:
        label = "Ts calculado"
        value = f"{format_decimal(details.service_temperature_c)} °C"
        calculation = (
            f"Tamb {format_decimal(details.tamb_max_c)} °C"
            f"  +  ΔT {format_decimal(details.delta_t_max_k)} K"
        )
    elif details.input_mode == ConditionInputMode.DIRECT_TS.value:
        label = "Ts informado"
        value = f"{format_decimal(details.service_temperature_c)} °C"
        calculation = "Valor térmico informado diretamente"
    else:
        label = "Referência térmica"
        value = details.ts_reference or "Conforme plano"
        calculation = "Condição personalizada"

    option = (
        f" • Opção {details.selected_option}"
        if details.selected_option and details.selected_option != "-"
        else ""
    )
    epl = f"EPL {details.epl}" if details.epl else "EPL não informado"
    return ft.Container(
        col={"xs": 12, "md": 5},
        border_radius=16,
        padding=20,
        gradient=ft.LinearGradient(
            begin=ft.Alignment.TOP_LEFT,
            end=ft.Alignment.BOTTOM_RIGHT,
            colors=["#0F766E", "#115E59"],
        ),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=7,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=7,
                    controls=[
                        ft.Icon(ft.Icons.THERMOSTAT, color="#CCFBF1", size=21),
                        ft.Text(
                            label.upper(),
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color="#CCFBF1",
                        ),
                    ],
                ),
                ft.Text(
                    value,
                    size=34 if has_numeric_ts else 24,
                    weight=ft.FontWeight.BOLD,
                    color=AppColors.WHITE,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Text(
                    calculation,
                    size=12,
                    color="#ECFEFF",
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(
                    border_radius=20,
                    bgcolor="#134E4A",
                    padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                    content=ft.Text(
                        f"{epl}{option}",
                        size=10,
                        weight=ft.FontWeight.BOLD,
                        color="#CCFBF1",
                        text_align=ft.TextAlign.CENTER,
                    ),
                ),
            ],
        ),
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
        on_change_timestamp: Callable[[str, datetime, str], None],
        on_advance_for_testing: Callable[[], None] | None = None,
    ) -> None:
        self._details = details
        self._on_start_chamber = on_start_chamber
        self._on_start_drying = on_start_drying
        self._on_finish = on_finish
        self._on_cancel = on_cancel
        self._on_delete = on_delete
        self._on_change_timestamp = on_change_timestamp
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
                    tooltip="Corrigir separadamente entradas e saídas das duas câmaras",
                    on_click=lambda _event: self._show_change_timestamps(),
                )
            )

        self.root = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.AUTO,
            spacing=18,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.ResponsiveRow(
                    spacing=14,
                    run_spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "lg": 7},
                            content=ft.Row(
                                spacing=12,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.ARROW_BACK,
                                        tooltip="Voltar para Ensaios",
                                        on_click=lambda _event: on_back(),
                                    ),
                                    ft.Column(
                                        expand=True,
                                        spacing=3,
                                        controls=[
                                            ft.Text(
                                                f"{details.client} / {details.process_number}",
                                                size=27,
                                                weight=ft.FontWeight.BOLD,
                                                color=AppColors.TEXT_PRIMARY,
                                            ),
                                            ft.Text(
                                                f"Ensaio #{details.id}",
                                                size=13,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            col={"xs": 12, "lg": 5},
                            alignment=ft.Alignment.CENTER_RIGHT,
                            content=ft.Row(
                                alignment=ft.MainAxisAlignment.END,
                                wrap=True,
                                run_spacing=8,
                                controls=header_actions,
                            ),
                        ),
                    ],
                ),
                self._summary_panel(),
                self._journey_panel(),
                self._phase_panel(),
                self._action_panel(),
                self._history_panel(),
                ft.Container(height=8),
            ],
        )

    def _summary_panel(self) -> ft.Container:
        """Organiza o essencial em blocos e reserva destaque exclusivo para o Ts."""

        details = self._details
        situation = f"Pausado — {details.situation}" if details.is_paused else details.situation
        progress_color = AppColors.WARNING if details.is_paused else AppColors.PRIMARY
        metadata = ft.ResponsiveRow(
            spacing=10,
            run_spacing=10,
            controls=[
                _summary_item("Situação", situation, ft.Icons.PLAY_CIRCLE_OUTLINE),
                _summary_item(
                    "Prazo",
                    details.deadline_condition or "Sem prazo ativo",
                    ft.Icons.SCHEDULE_OUTLINED,
                ),
                _summary_item("Produto", details.product, ft.Icons.INVENTORY_2_OUTLINED),
                _summary_item(
                    "Amostras",
                    str(details.sample_quantity),
                    ft.Icons.SCIENCE_OUTLINED,
                ),
            ],
        )
        left = ft.Container(
            col={"xs": 12, "md": 7},
            content=ft.Column(
                spacing=12,
                controls=[
                    metadata,
                    ft.Container(
                        border_radius=12,
                        border=ft.Border.all(1, AppColors.DIVIDER),
                        padding=12,
                        content=ft.Column(
                            spacing=7,
                            controls=[
                                ft.Row(
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                    controls=[
                                        ft.Text(
                                            "Progresso da etapa",
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Text(
                                            f"{details.progress_percent * 100:.0f}%",
                                            size=12,
                                            weight=ft.FontWeight.BOLD,
                                            color=progress_color,
                                        ),
                                    ],
                                ),
                                ft.ProgressBar(
                                    value=details.progress_percent,
                                    height=8,
                                    color=progress_color,
                                    bgcolor=AppColors.DIVIDER,
                                    border_radius=6,
                                ),
                                ft.Text(
                                    details.progress_label,
                                    size=10,
                                    color=AppColors.TEXT_SECONDARY,
                                ),
                            ],
                        ),
                    ),
                    *(
                        [
                            ft.Container(
                                border_radius=10,
                                bgcolor=AppColors.WARNING_LIGHT,
                                padding=10,
                                content=ft.Text(
                                    f"Motivo da pausa: {details.pause_reason}",
                                    size=11,
                                    color=AppColors.TEXT_PRIMARY,
                                ),
                            )
                        ]
                        if details.is_paused
                        else []
                    ),
                    ft.ResponsiveRow(
                        spacing=10,
                        run_spacing=8,
                        controls=[
                            _value(
                                "Origem da condição",
                                format_condition_source(details.input_mode),
                            ),
                            _value("EPL", details.epl or "Não informado"),
                            _value(
                                "Alternativa",
                                (
                                    f"Opção {details.selected_option}"
                                    if details.selected_option != "-"
                                    else "Não aplicável"
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )
        return _panel(
            "Resumo do ensaio",
            [
                ft.ResponsiveRow(
                    spacing=16,
                    run_spacing=16,
                    # A tela inteira é rolável, portanto seus filhos recebem altura
                    # vertical ilimitada durante o layout. STRETCH tentaria impor essa
                    # altura infinita aos cartões e o Flutter deixaria todo o conteúdo
                    # abaixo do cabeçalho sem renderização.
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[left, _ts_highlight(details)],
                )
            ],
            help_text=(
                "O Ts é a temperatura de serviço usada como referência térmica. "
                "Os demais dados ficam agrupados por situação, prazo e identificação."
            ),
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
        chamber = _phase_card(
            title="Câmara úmida",
            subtitle="Condição e marcos da etapa principal",
            icon=ft.Icons.WATER_DROP_OUTLINED,
            accent=AppColors.PRIMARY,
            accent_background=AppColors.PRIMARY_LIGHT,
            condition_values=[
                _value(
                    "Temperatura",
                    f"{format_decimal(details.chamber_temperature_c)} ± 2 °C",
                    col={"xs": 12, "sm": 4},
                ),
                _value(
                    "Umidade",
                    f"{format_decimal(details.chamber_humidity_percent)} ± 5% UR",
                    col={"xs": 12, "sm": 4},
                ),
                _value(
                    "Permanência",
                    f"{details.chamber_duration_hours} h "
                    f"(+{details.chamber_duration_tolerance_hours} h)",
                    col={"xs": 12, "sm": 4},
                ),
            ],
            duration_detail=format_duration_detail(
                details.chamber_duration_hours,
                details.chamber_duration_tolerance_hours,
            ),
            schedule=[
                (
                    "Entrada registrada",
                    format_datetime(details.chamber_started_at),
                    ft.Icons.LOGIN,
                ),
                (
                    "Retirada recomendada",
                    format_datetime(details.chamber_nominal_end_at),
                    ft.Icons.EVENT_AVAILABLE,
                ),
                (
                    "Último prazo permitido",
                    format_datetime(details.chamber_maximum_end_at),
                    ft.Icons.WARNING_AMBER,
                ),
                (
                    "Retirada registrada",
                    format_datetime(details.chamber_ended_at),
                    ft.Icons.LOGOUT,
                ),
            ],
        )
        phase_cards: list[ft.Control] = [chamber]
        if details.drying_required:
            phase_cards.append(
                _phase_card(
                    title="Secagem",
                    subtitle="Etapa posterior à retirada da câmara",
                    icon=ft.Icons.AIR,
                    accent=AppColors.DRYING,
                    accent_background=AppColors.DRYING_LIGHT,
                    condition_values=[
                        _value(
                            "Temperatura",
                            f"{format_decimal(details.drying_temperature_c or '0')} ± 2 °C",
                            col={"xs": 12, "sm": 6},
                        ),
                        _value(
                            "Permanência",
                            f"{details.drying_duration_hours} h "
                            f"(+{details.drying_duration_tolerance_hours} h)",
                            col={"xs": 12, "sm": 6},
                        ),
                    ],
                    duration_detail=format_duration_detail(
                        details.drying_duration_hours or 0,
                        details.drying_duration_tolerance_hours or 0,
                    ),
                    schedule=[
                        (
                            "Entrada registrada",
                            format_datetime(details.drying_started_at),
                            ft.Icons.LOGIN,
                        ),
                        (
                            "Retirada recomendada",
                            format_datetime(details.drying_nominal_end_at),
                            ft.Icons.EVENT_AVAILABLE,
                        ),
                        (
                            "Último prazo permitido",
                            format_datetime(details.drying_maximum_end_at),
                            ft.Icons.WARNING_AMBER,
                        ),
                        (
                            "Retirada registrada",
                            format_datetime(details.drying_ended_at),
                            ft.Icons.LOGOUT,
                        ),
                    ],
                )
            )
        else:
            chamber.col = {"xs": 12}
        controls: list[ft.Control] = [
            ft.ResponsiveRow(
                spacing=14,
                run_spacing=14,
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=phase_cards,
            )
        ]
        if not details.drying_required:
            controls.append(
                ft.Text(
                    "Esta condição não exige etapa de secagem.",
                    size=12,
                    color=AppColors.TEXT_SECONDARY,
                )
            )
        return _panel(
            "Condições e prazos",
            controls,
            help_text=(
                "Cada etapa reúne sua condição nominal, retirada recomendada e "
                "último prazo permitido."
            ),
        )

    def _action_panel(self) -> ft.Container:
        details = self._details
        now_button: ft.Control | None = None
        manual_callback: Callable[[datetime | None], None] | None = None
        manual_label = ""
        active_situations = {"Aguardando", "Na Câmara", "Em Secagem"}
        if details.is_paused:
            now_button = None
        elif details.situation == "Aguardando":
            now_button = ft.Button(
                content="Registrar entrada agora",
                icon=ft.Icons.PLAY_ARROW,
                bgcolor=AppColors.PRIMARY,
                color=AppColors.WHITE,
                tooltip="Confirmar a entrada e conferir a retirada nominal calculada",
                on_click=lambda _event: self._confirm_chamber_start(
                    datetime.now().replace(microsecond=0)
                ),
            )
            manual_callback = self._confirm_chamber_start
            manual_label = "Confirmar entrada informada"
        elif details.situation == "Na Câmara":
            label = (
                "Registrar retirada e iniciar secagem agora"
                if details.drying_required
                else "Registrar retirada e finalizar agora"
            )
            callback = (
                self._confirm_chamber_exit_to_drying
                if details.drying_required
                else self._confirm_chamber_exit_and_finish
            )
            now_button = ft.Button(
                content=label,
                icon=ft.Icons.AIR if details.drying_required else ft.Icons.CHECK,
                bgcolor=AppColors.PRIMARY,
                color=AppColors.WHITE,
                on_click=lambda _event: callback(None),
            )
            manual_callback = callback
            manual_label = (
                "Confirmar retirada e início da secagem"
                if details.drying_required
                else "Confirmar retirada e finalização"
            )
        elif details.situation == "Em Secagem":
            now_button = ft.Button(
                content="Registrar retirada e finalizar agora",
                icon=ft.Icons.CHECK,
                bgcolor=AppColors.PRIMARY,
                color=AppColors.WHITE,
                on_click=lambda _event: self._confirm_drying_exit_and_finish(None),
            )
            manual_callback = self._confirm_drying_exit_and_finish
            manual_label = "Confirmar retirada e finalização"

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
        elif now_button is not None and manual_callback is not None:
            now_button.height = 48
            now_button.style = ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            )
            manual_button = ft.Button(
                content=manual_label,
                icon=ft.Icons.EDIT_CALENDAR,
                height=48,
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=12),
                    padding=ft.Padding.symmetric(horizontal=20, vertical=12),
                ),
                on_click=(lambda _event, selected=manual_callback: self._manual(selected)),
            )
            controls.extend(
                [
                    ft.Column(
                        spacing=3,
                        controls=[
                            ft.Text(
                                "Como esta operação deve ser registrada?",
                                size=17,
                                weight=ft.FontWeight.BOLD,
                                color=AppColors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                "Escolha uma opção conforme o momento em que a atividade ocorreu.",
                                size=12,
                                color=AppColors.TEXT_SECONDARY,
                            ),
                        ],
                    ),
                    ft.ResponsiveRow(
                        spacing=16,
                        run_spacing=16,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "lg": 6},
                                border_radius=16,
                                bgcolor=AppColors.PRIMARY_LIGHT,
                                border=ft.Border.all(2, AppColors.PRIMARY),
                                padding=20,
                                content=ft.Column(
                                    spacing=16,
                                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                    controls=[
                                        ft.Row(
                                            spacing=12,
                                            controls=[
                                                ft.Container(
                                                    width=42,
                                                    height=42,
                                                    border_radius=13,
                                                    bgcolor=AppColors.PRIMARY,
                                                    alignment=ft.Alignment.CENTER,
                                                    content=ft.Icon(
                                                        ft.Icons.SCHEDULE,
                                                        size=23,
                                                        color=AppColors.WHITE,
                                                    ),
                                                ),
                                                ft.Column(
                                                    expand=True,
                                                    spacing=2,
                                                    controls=[
                                                        ft.Text(
                                                            "Registrar agora",
                                                            size=17,
                                                            weight=ft.FontWeight.BOLD,
                                                            color=AppColors.TEXT_PRIMARY,
                                                        ),
                                                        ft.Text(
                                                            "OPERAÇÃO EM TEMPO REAL",
                                                            size=10,
                                                            weight=ft.FontWeight.BOLD,
                                                            color=AppColors.PRIMARY,
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        ft.Text(
                                            "Use quando a entrada ou retirada está acontecendo "
                                            "neste momento. A data e a hora do computador serão "
                                            "capturadas somente ao confirmar.",
                                            size=12,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Container(
                                            border_radius=12,
                                            bgcolor=AppColors.SURFACE,
                                            padding=12,
                                            content=ft.Row(
                                                spacing=9,
                                                controls=[
                                                    ft.Icon(
                                                        ft.Icons.VERIFIED_OUTLINED,
                                                        size=19,
                                                        color=AppColors.PRIMARY,
                                                    ),
                                                    ft.Text(
                                                        "Maior rastreabilidade: evita digitação "
                                                        "manual do horário.",
                                                        expand=True,
                                                        size=11,
                                                        color=AppColors.TEXT_SECONDARY,
                                                    ),
                                                ],
                                            ),
                                        ),
                                        now_button,
                                    ],
                                ),
                            ),
                            ft.Container(
                                col={"xs": 12, "lg": 6},
                                border_radius=16,
                                bgcolor=AppColors.INFO_LIGHT,
                                border=ft.Border.all(1, AppColors.INFO),
                                padding=20,
                                content=ft.Column(
                                    spacing=16,
                                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                                    controls=[
                                        ft.Row(
                                            spacing=12,
                                            controls=[
                                                ft.Container(
                                                    width=42,
                                                    height=42,
                                                    border_radius=13,
                                                    bgcolor=AppColors.INFO,
                                                    alignment=ft.Alignment.CENTER,
                                                    content=ft.Icon(
                                                        ft.Icons.EDIT_CALENDAR,
                                                        size=23,
                                                        color=AppColors.WHITE,
                                                    ),
                                                ),
                                                ft.Column(
                                                    expand=True,
                                                    spacing=2,
                                                    controls=[
                                                        ft.Text(
                                                            "Informar data e hora",
                                                            size=17,
                                                            weight=ft.FontWeight.BOLD,
                                                            color=AppColors.TEXT_PRIMARY,
                                                        ),
                                                        ft.Text(
                                                            "REGISTRO POSTERIOR",
                                                            size=10,
                                                            weight=ft.FontWeight.BOLD,
                                                            color=AppColors.INFO,
                                                        ),
                                                    ],
                                                ),
                                            ],
                                        ),
                                        ft.Text(
                                            "Use somente quando a atividade já aconteceu e não "
                                            "foi registrada no momento real. Confira os dados "
                                            "antes "
                                            "de confirmar.",
                                            size=12,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.ResponsiveRow(
                                            spacing=12,
                                            run_spacing=12,
                                            controls=[
                                                ft.Container(
                                                    col={"xs": 12, "sm": 7},
                                                    content=self.date,
                                                ),
                                                ft.Container(
                                                    col={"xs": 12, "sm": 5},
                                                    content=self.time,
                                                ),
                                            ],
                                        ),
                                        manual_button,
                                    ],
                                ),
                            ),
                        ],
                    ),
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
                    ft.Container(
                        border_radius=14,
                        bgcolor=AppColors.DANGER_LIGHT,
                        border=ft.Border.all(1, AppColors.DIVIDER),
                        padding=16,
                        content=ft.ResponsiveRow(
                            spacing=12,
                            run_spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(
                                    col={"xs": 12, "md": 8, "lg": 9},
                                    content=ft.Column(
                                        spacing=2,
                                        controls=[
                                            ft.Text(
                                                "Cancelar este ensaio",
                                                size=13,
                                                weight=ft.FontWeight.BOLD,
                                                color=AppColors.DANGER,
                                            ),
                                            ft.Text(
                                                "Escolha o motivo em uma janela de confirmação. "
                                                "O registro técnico será preservado.",
                                                size=10,
                                                color=AppColors.TEXT_SECONDARY,
                                            ),
                                        ],
                                    ),
                                ),
                                ft.Container(
                                    col={"xs": 12, "md": 4, "lg": 3},
                                    alignment=ft.Alignment.CENTER_RIGHT,
                                    content=ft.Button(
                                        content="Cancelar ensaio",
                                        icon=ft.Icons.CANCEL_OUTLINED,
                                        color=AppColors.DANGER,
                                        on_click=lambda _event: self._show_cancel_dialog(),
                                    ),
                                ),
                            ],
                        ),
                    ),
                ]
            )
        if details.situation == "Aguardando":
            controls.extend(
                [
                    ft.Divider(height=1, color=AppColors.DIVIDER),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        wrap=True,
                        run_spacing=10,
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
                            wrap=True,
                            run_spacing=10,
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
        return _panel(
            "Ações operacionais",
            controls,
            help_text=(
                "Use “Registrar agora” quando a operação estiver acontecendo neste "
                "momento. Use o horário manual somente para registrar algo que já ocorreu."
            ),
        )

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
                    border_radius=12,
                    bgcolor=AppColors.PAGE_BACKGROUND,
                    border=ft.Border.all(1, AppColors.DIVIDER),
                    padding=14,
                    content=ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                col={"xs": 12, "md": 8, "lg": 9},
                                content=ft.Row(
                                    spacing=12,
                                    vertical_alignment=ft.CrossAxisAlignment.START,
                                    controls=[
                                        ft.Container(
                                            width=36,
                                            height=36,
                                            border_radius=12,
                                            bgcolor=AppColors.PRIMARY_LIGHT,
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(
                                                ft.Icons.HISTORY,
                                                size=18,
                                                color=AppColors.PRIMARY,
                                            ),
                                        ),
                                        ft.Column(
                                            expand=True,
                                            spacing=3,
                                            controls=[
                                                ft.Text(
                                                    event.action,
                                                    weight=ft.FontWeight.BOLD,
                                                    color=AppColors.TEXT_PRIMARY,
                                                ),
                                                ft.Text(
                                                    description,
                                                    size=12,
                                                    color=AppColors.TEXT_SECONDARY,
                                                ),
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
                                            ],
                                        ),
                                    ],
                                ),
                            ),
                            ft.Container(
                                col={"xs": 12, "md": 4, "lg": 3},
                                content=ft.Column(
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                    spacing=2,
                                    controls=[
                                        ft.Text(
                                            event.actor,
                                            size=11,
                                            weight=ft.FontWeight.BOLD,
                                            color=AppColors.TEXT_PRIMARY,
                                        ),
                                        ft.Text(
                                            format_datetime(event.occurred_at),
                                            size=10,
                                            color=AppColors.TEXT_SECONDARY,
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                )
            )
        return _panel(
            "Registro técnico detalhado",
            rows,
            help_text=(
                "Cada alteração permanece vinculada ao responsável e ao horário "
                "em que foi registrada."
            ),
        )

    def _registered_timestamps(self) -> dict[OperationalTimestamp, datetime]:
        """Lista somente horários que já foram registrados operacionalmente."""

        values = {
            OperationalTimestamp.CHAMBER_STARTED: self._details.chamber_started_at,
            OperationalTimestamp.CHAMBER_ENDED: self._details.chamber_ended_at,
            OperationalTimestamp.DRYING_STARTED: self._details.drying_started_at,
            OperationalTimestamp.DRYING_ENDED: self._details.drying_ended_at,
        }
        return {key: value for key, value in values.items() if value is not None}

    def _show_change_timestamps(self) -> None:
        timestamps = self._registered_timestamps()
        if not timestamps:
            return
        selected = next(iter(timestamps))
        selector = ft.Dropdown(
            label="Registro a corrigir *",
            value=selected.value,
            options=[ft.DropdownOption(key=key.value, text=key.label) for key in timestamps],
            border_radius=10,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
            bgcolor=AppColors.SURFACE,
        )
        selected_value = timestamps[selected]
        date_field = _masked_datetime_field(
            label="Data corrigida",
            value=selected_value.strftime("%d/%m/%Y"),
            width=None,
            hint_text="DD/MM/AAAA",
            is_date=True,
        )
        time_field = _masked_datetime_field(
            label="Hora corrigida",
            value=selected_value.strftime("%H:%M"),
            width=None,
            hint_text="HH:MM",
            is_date=False,
        )
        current_value = ft.Text(
            f"Valor atual: {format_datetime(selected_value)}",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=AppColors.TEXT_PRIMARY,
        )
        effect_text = ft.Text(
            "A alteração da entrada recalcula os prazos da etapa correspondente.",
            size=11,
            color=AppColors.TEXT_SECONDARY,
        )
        reason_selector = ReasonSelector(
            TIMESTAMP_REASON_OPTIONS,
            other_hint="Resuma por que este horário precisa ser corrigido",
        )
        error_text = ft.Text("", size=11, color=AppColors.DANGER)
        page = self.root.page

        def change_selection(_event: object | None = None) -> None:
            resolved = OperationalTimestamp(selector.value)
            current = timestamps[resolved]
            date_field.value = current.strftime("%d/%m/%Y")
            time_field.value = current.strftime("%H:%M")
            current_value.value = f"Valor atual: {format_datetime(current)}"
            effect_text.value = (
                "A alteração da entrada recalcula os prazos da etapa correspondente."
                if resolved
                in {
                    OperationalTimestamp.CHAMBER_STARTED,
                    OperationalTimestamp.DRYING_STARTED,
                }
                else "A alteração corrige a saída real sem mudar o prazo nominal calculado."
            )
            page.update(date_field, time_field, current_value, effect_text)

        selector.on_select = change_selection

        def confirm(_event: object | None = None) -> None:
            try:
                timestamp = OperationalTimestamp(selector.value)
                new_value = parse_local_datetime(date_field.value, time_field.value)
            except ValueError as error:
                error_text.value = str(error)
                error_text.update()
                return
            if not reason_selector.validate(message="Selecione o motivo da correção."):
                return
            page.pop_dialog()
            self._on_change_timestamp(
                timestamp.value,
                new_value,
                reason_selector.value(),
            )

        page.show_dialog(
            styled_dialog(
                title="Corrigir horários do ensaio",
                subtitle="Entradas e saídas são registros independentes",
                icon=ft.Icons.EDIT_CALENDAR,
                content=ft.Column(
                    width=620,
                    tight=True,
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "Escolha primeiro o registro exato. Assim, corrigir a entrada "
                            "na câmara seca nunca altera a entrada da câmara climática."
                        ),
                        selector,
                        ft.Container(
                            border_radius=12,
                            bgcolor=AppColors.PAGE_BACKGROUND,
                            border=ft.Border.all(1, AppColors.DIVIDER),
                            padding=12,
                            content=ft.Column(
                                spacing=3,
                                controls=[current_value, effect_text],
                            ),
                        ),
                        ft.ResponsiveRow(
                            spacing=12,
                            run_spacing=10,
                            controls=[
                                ft.Container(
                                    col={"xs": 12, "sm": 7},
                                    content=date_field,
                                ),
                                ft.Container(
                                    col={"xs": 12, "sm": 5},
                                    content=time_field,
                                ),
                            ],
                        ),
                        reason_selector.control,
                        error_text,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Salvar correção",
                    primary_icon=ft.Icons.SAVE_OUTLINED,
                    on_confirm=confirm,
                ),
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

    def _confirm_chamber_start(self, started_at: datetime | None) -> None:
        """Confirma a entrada mostrando antes a retirada nominal e o limite."""

        effective_start = (started_at or datetime.now()).replace(microsecond=0)
        nominal_end = effective_start + timedelta(hours=self._details.chamber_duration_hours)
        maximum_end = nominal_end + timedelta(hours=self._details.chamber_duration_tolerance_hours)
        page = self.root.page

        def confirm(_event: object | None = None) -> None:
            page.pop_dialog()
            self._on_start_chamber(effective_start)

        page.show_dialog(
            styled_dialog(
                title="Confirmar entrada na câmara?",
                subtitle="Confira a data, o horário e o dia da semana",
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                scrollable=True,
                content=_chamber_start_summary(effective_start, nominal_end, maximum_end),
                actions=dialog_actions(
                    page=page,
                    primary_label="Confirmar entrada",
                    primary_icon=ft.Icons.CHECK,
                    on_confirm=confirm,
                    cancel_label="Voltar e revisar",
                ),
            )
        )

    def _confirm_chamber_exit_to_drying(self, occurred_at: datetime | None) -> None:
        self._confirm_operational_transition(
            occurred_at,
            title="Registrar saída e iniciar a secagem?",
            message=(
                "Este horário será salvo como saída da câmara climática e entrada na câmara seca."
            ),
            confirm_label="Confirmar troca de etapa",
            callback=self._on_start_drying,
        )

    def _confirm_chamber_exit_and_finish(self, occurred_at: datetime | None) -> None:
        self._confirm_operational_transition(
            occurred_at,
            title="Registrar saída e finalizar o ensaio?",
            message="Esta condição não exige secagem. O ensaio será marcado como finalizado.",
            confirm_label="Confirmar finalização",
            callback=self._on_finish,
        )

    def _confirm_drying_exit_and_finish(self, occurred_at: datetime | None) -> None:
        self._confirm_operational_transition(
            occurred_at,
            title="Registrar saída da secagem e finalizar?",
            message="O horário será salvo como saída da câmara seca e encerrará o ensaio.",
            confirm_label="Confirmar finalização",
            callback=self._on_finish,
        )

    def _confirm_operational_transition(
        self,
        occurred_at: datetime | None,
        *,
        title: str,
        message: str,
        confirm_label: str,
        callback: Callable[[datetime | None], None],
    ) -> None:
        effective_time = (occurred_at or datetime.now()).replace(microsecond=0)
        self._show_confirmation(
            title,
            f"Horário registrado: {format_datetime(effective_time)}\n{message}",
            lambda: callback(effective_time),
            confirm_label=confirm_label,
            danger=False,
        )

    def _show_cancel_dialog(self) -> None:
        reason_selector = ReasonSelector(
            CANCELLATION_REASON_OPTIONS,
            other_hint="Resuma por que o ensaio precisa ser cancelado",
        )
        page = self.root.page

        def confirm(_event: object | None = None) -> None:
            if not reason_selector.validate(message="Selecione o motivo do cancelamento."):
                return
            page.pop_dialog()
            self._on_cancel(reason_selector.value())

        page.show_dialog(
            styled_dialog(
                title="Cancelar este ensaio?",
                subtitle=(
                    f"{self._details.client} / {self._details.process_number} "
                    f"• Ensaio #{self._details.id}"
                ),
                icon=ft.Icons.CANCEL_OUTLINED,
                danger=True,
                content=ft.Column(
                    width=560,
                    tight=True,
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        dialog_banner(
                            "O ensaio permanecerá no sistema como cancelado. "
                            "A justificativa e o responsável ficarão no registro técnico.",
                            icon=ft.Icons.WARNING_AMBER,
                            danger=True,
                        ),
                        reason_selector.control,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Confirmar cancelamento",
                    primary_icon=ft.Icons.CANCEL_OUTLINED,
                    on_confirm=confirm,
                    danger=True,
                ),
            )
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

        dialog = styled_dialog(
            title=title,
            subtitle="Confira os dados antes de continuar",
            icon=ft.Icons.WARNING_AMBER if danger else ft.Icons.CHECK_CIRCLE_OUTLINE,
            danger=danger,
            content=ft.Container(
                width=520,
                content=dialog_banner(
                    message,
                    icon=ft.Icons.WARNING_AMBER if danger else ft.Icons.INFO_OUTLINE,
                    danger=danger,
                ),
            ),
            actions=dialog_actions(
                page=page,
                primary_label=confirm_label,
                primary_icon=ft.Icons.DELETE_OUTLINE if danger else ft.Icons.CHECK,
                on_confirm=confirm,
                danger=danger,
                cancel_label="Não",
            ),
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
    on_change_timestamp: Callable[[str, datetime, str], None],
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
        on_change_timestamp=on_change_timestamp,
        on_advance_for_testing=on_advance_for_testing,
    ).root
