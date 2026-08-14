"""Correções de produção da rodada 3 para a v0.8.0.

Este módulo concentra hotfixes de interface observados no uso real sem duplicar
as regras de negócio já validadas. Ele é carregado pelo servidor e pelo ponto de
entrada de desenvolvimento antes de a primeira sessão Flet ser criada.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime

import flet as ft
from sqlalchemy import select

from climatetest_manager.database.models import ClimateTestRecord, SecurityAuditEvent
from climatetest_manager.domain.enums import ConditionInputMode, EquipmentResource
from climatetest_manager.repositories.climate_tests import AuditHistoryEntry, ClimateTestRepository
from climatetest_manager.repositories.production import ProductionClimateTestRepository
from climatetest_manager.services.climate_tests import (
    CreateClimateTestCommand,
    UpdateClimateTestCommand,
)
from climatetest_manager.ui import interaction as interaction_module
from climatetest_manager.ui import shell as shell_module
from climatetest_manager.ui.components import dialog_actions, dialog_banner, styled_dialog
from climatetest_manager.ui.interaction import apply_interaction_polish
from climatetest_manager.ui.theme import AppColors, _PALETTES
from climatetest_manager.ui.views import history as history_module
from climatetest_manager.ui.views import polished_new_test as polished_new_test_module
from climatetest_manager.ui.views import polished_test_details as polished_details_module
from climatetest_manager.ui.views import production_settings as production_settings_module
from climatetest_manager.ui.views import test_details as test_details_module
from climatetest_manager.ui.views import tests_list as tests_list_module
from climatetest_manager.ui.views.new_test import NewTestView

# Importado por último de propósito: os módulos de UI acima já estão carregados e
# podem ser ajustados sem ciclo de importação.
from climatetest_manager import production_app

_stable_navigation_surface = interaction_module.hoverable_navigation_surface


def _safe_update(control: ft.Control) -> None:
    with suppress(RuntimeError):
        control.update()


def _install_dark_palettes() -> None:
    """Troca transparências cinzentas por superfícies opacas e hierarquia clara."""

    _PALETTES["dark"].update(
        {
            "PRIMARY": "#2DD4BF",
            "PRIMARY_LIGHT": "#123A37",
            "PAGE_BACKGROUND": "#0D1117",
            "NAV_BACKGROUND": "#161B22",
            "NAV_SELECTED": "#123A37",
            "NAV_HOVER": "#21262D",
            "NAV_TEXT": "#C9D1D9",
            "SURFACE": "#161B22",
            "TEXT_PRIMARY": "#F0F6FC",
            "TEXT_SECONDARY": "#8B949E",
            "DIVIDER": "#30363D",
            "WARNING": "#D29922",
            "WARNING_LIGHT": "#2D2515",
            "DANGER": "#F85149",
            "DANGER_LIGHT": "#3B1E20",
            "INFO": "#58A6FF",
            "INFO_LIGHT": "#172A3D",
            "DRYING": "#BC8CFF",
            "DRYING_LIGHT": "#2A2138",
            "WHITE": "#FFFFFF",
            "GLASS_SURFACE": "#161B22",
            "GLASS_SURFACE_ACCENT": "#18232A",
            "GLASS_BORDER": "#30363D",
            "SURFACE_SHADOW": "#66000000",
            "INTERACTIVE_HOVER": "#26303A",
            "INTERACTIVE_PRESSED": "#30404A",
            "ACCENT_GLOW": "#405EEAD4",
        }
    )
    _PALETTES["graphite"].update(
        {
            "PRIMARY": "#F0B35A",
            "PRIMARY_LIGHT": "#3B3022",
            "PAGE_BACKGROUND": "#1C2128",
            "NAV_BACKGROUND": "#22272E",
            "NAV_SELECTED": "#3B3022",
            "NAV_HOVER": "#2D333B",
            "NAV_TEXT": "#C7D0D9",
            "SURFACE": "#2D333B",
            "TEXT_PRIMARY": "#F0F3F6",
            "TEXT_SECONDARY": "#9DA7B1",
            "DIVIDER": "#444C56",
            "WARNING": "#DAAA3F",
            "WARNING_LIGHT": "#41351F",
            "DANGER": "#E5534B",
            "DANGER_LIGHT": "#432426",
            "INFO": "#6CB6FF",
            "INFO_LIGHT": "#24374A",
            "DRYING": "#D2A8FF",
            "DRYING_LIGHT": "#382B47",
            "WHITE": "#FFFFFF",
            "GLASS_SURFACE": "#2D333B",
            "GLASS_SURFACE_ACCENT": "#33383F",
            "GLASS_BORDER": "#444C56",
            "SURFACE_SHADOW": "#52000000",
            "INTERACTIVE_HOVER": "#373E47",
            "INTERACTIVE_PRESSED": "#414A55",
            "ACCENT_GLOW": "#40F0B35A",
        }
    )
    _PALETTES["ocean"].update(
        {
            "PRIMARY": "#58C7F3",
            "PRIMARY_LIGHT": "#123A50",
            "PAGE_BACKGROUND": "#07121F",
            "NAV_BACKGROUND": "#0B1B2B",
            "NAV_SELECTED": "#123A50",
            "NAV_HOVER": "#10283B",
            "NAV_TEXT": "#C5DBEA",
            "SURFACE": "#10263A",
            "TEXT_PRIMARY": "#EAF7FF",
            "TEXT_SECONDARY": "#9CB7CB",
            "DIVIDER": "#28445B",
            "WARNING": "#F2C14E",
            "WARNING_LIGHT": "#3A321E",
            "DANGER": "#FF6B7A",
            "DANGER_LIGHT": "#43242D",
            "INFO": "#70B7FF",
            "INFO_LIGHT": "#163A59",
            "DRYING": "#C4B5FD",
            "DRYING_LIGHT": "#322A51",
            "WHITE": "#FFFFFF",
            "GLASS_SURFACE": "#10263A",
            "GLASS_SURFACE_ACCENT": "#123047",
            "GLASS_BORDER": "#28445B",
            "SURFACE_SHADOW": "#5C000000",
            "INTERACTIVE_HOVER": "#17364D",
            "INTERACTIVE_PRESSED": "#1D435D",
            "ACCENT_GLOW": "#4058C7F3",
        }
    )


def _navigation_surface(
    *,
    label: str,
    icon: ft.IconData,
    selected: bool,
    compact: bool,
    icon_size: int,
    on_click,
    badge_count: int = 0,
) -> ft.Container:
    """Reutiliza a única implementação estável da navegação lateral."""

    return _stable_navigation_surface(
        label=label,
        icon=icon,
        selected=selected,
        compact=compact,
        icon_size=icon_size,
        on_click=on_click,
        badge_count=badge_count,
    )


def _install_sidebar_fix() -> None:
    interaction_module.hoverable_navigation_surface = _navigation_surface
    shell_module.hoverable_navigation_surface = _navigation_surface


_original_polished_init = polished_new_test_module.PolishedNewTestView.__init__


def _polished_init(self, *args, **kwargs) -> None:
    _original_polished_init(self, *args, **kwargs)
    self.save_button.disabled = False

    manual_column = getattr(self.manual_condition_fields, "content", None)
    controls = getattr(manual_column, "controls", None)
    if isinstance(controls, list) and self.ts_reference not in controls:
        controls.insert(1, self.ts_reference)

    def clear_identity(field: ft.TextField, previous=None):
        def handler(event) -> None:
            if callable(previous):
                previous(event)
            if field.value.strip():
                field.error = None
                _safe_update(field)

        return handler

    for field in (self.client, self.process_number, self.product):
        field.on_change = clear_identity(field, field.on_change)

    previous_quantity = self.sample_quantity.on_change
    self.sample_quantity.on_change = clear_identity(self.sample_quantity, previous_quantity)


def _clear_present_errors(view) -> None:
    fields = (
        view.client,
        view.process_number,
        view.product,
        view.sample_quantity,
        view.delta_t,
        view.service_temperature,
        view.ts_reference,
        view.manual_chamber_temperature,
        view.manual_chamber_humidity,
        view.manual_chamber_duration,
        view.manual_drying_temperature,
        view.manual_drying_duration,
    )
    for field in fields:
        if field.value.strip():
            field.error = None
    if view.epl.value:
        with suppress(Exception):
            view.epl.error = None
        with suppress(Exception):
            view.epl.error_text = None


def _polished_clear_condition(self, help_text: str) -> None:
    NewTestView._clear_condition(self, help_text)
    if hasattr(self, "save_button"):
        self.save_button.disabled = False


def _polished_recalculate(self, event: object | None = None) -> None:
    _clear_present_errors(self)
    NewTestView._recalculate(self, event)
    if hasattr(self, "save_button"):
        self.save_button.disabled = False
        _safe_update(self.save_button)


def _mark_required(field: ft.TextField, label: str, missing: list[str]) -> None:
    empty = not field.value.strip()
    field.error = "Campo obrigatório." if empty else None
    if empty:
        missing.append(label)
    _safe_update(field)


def _polished_submit(self, _event: object | None = None) -> None:
    mode = self.mode_group.value or ConditionInputMode.CALCULATED.value
    missing: list[str] = []

    for field, label in (
        (self.client, "Cliente"),
        (self.process_number, "Processo"),
        (self.product, "Produto"),
        (self.sample_quantity, "Quantidade de amostras"),
    ):
        _mark_required(field, label, missing)

    if mode == ConditionInputMode.CALCULATED.value:
        _mark_required(self.delta_t, "Delta T máximo", missing)
    elif mode == ConditionInputMode.DIRECT_TS.value:
        _mark_required(self.service_temperature, "Ts informado", missing)
    else:
        _mark_required(self.ts_reference, "Critério descrito no plano", missing)
        _mark_required(self.manual_chamber_temperature, "Temperatura personalizada", missing)
        _mark_required(self.manual_chamber_humidity, "Umidade personalizada", missing)
        _mark_required(self.manual_chamber_duration, "Permanência na câmara", missing)
        if self.manual_drying_required.value:
            _mark_required(self.manual_drying_temperature, "Temperatura da secagem", missing)
            _mark_required(self.manual_drying_duration, "Permanência na secagem", missing)

    if mode != ConditionInputMode.DIRECT_CONFIGURATION.value:
        if not self.epl.value:
            missing.append("EPL")
            with suppress(Exception):
                self.epl.error = "Campo obrigatório."
            with suppress(Exception):
                self.epl.error_text = "Campo obrigatório."
        else:
            with suppress(Exception):
                self.epl.error = None
            with suppress(Exception):
                self.epl.error_text = None
        _safe_update(self.epl)

    if missing:
        self.save_button.disabled = False
        self._show_error(
            "Preencha todos os campos obrigatórios destacados em vermelho para salvar o ensaio."
        )
        self._refresh()
        return

    if self._condition is None:
        self.save_button.disabled = False
        self._show_error(
            "Os dados térmicos ainda não formam uma condição válida. Revise os valores informados."
        )
        self._refresh()
        return

    if not self.sample_quantity.value.isdigit() or int(self.sample_quantity.value) < 1:
        self.sample_quantity.error = "Informe um número inteiro maior que zero."
        _safe_update(self.sample_quantity)
        self._show_error("Revise a quantidade de amostras.")
        self._refresh()
        return

    common_values = {
        "client": self.client.value,
        "process_number": self.process_number.value,
        "product": self.product.value,
        "epl": self.epl.value or "",
        "tamb_max_c": self.tamb.value,
        "delta_t_max_k": self.delta_t.value,
        "selected_option": (
            self.option_group.value or ""
            if mode
            in {
                ConditionInputMode.CALCULATED.value,
                ConditionInputMode.DIRECT_TS.value,
            }
            else ""
        ),
        "sample_quantity": self.sample_quantity.value,
        "notes": self.notes.value,
        "input_mode": mode,
        "service_temperature_c": self.service_temperature.value,
        "ts_reference": self.ts_reference.value,
        "manual_chamber_temperature_c": self.manual_chamber_temperature.value,
        "manual_chamber_humidity_percent": self.manual_chamber_humidity.value,
        "manual_chamber_duration_hours": self.manual_chamber_duration.value,
        "manual_drying_required": bool(self.manual_drying_required.value),
        "manual_drying_temperature_c": self.manual_drying_temperature.value,
        "manual_drying_duration_hours": self.manual_drying_duration.value,
    }
    if self._details is not None:
        if not self.change_reason_selector.validate(message="Selecione o motivo da alteração."):
            self._show_error("O motivo é obrigatório para preservar a rastreabilidade.")
            self._refresh()
            return
        command: CreateClimateTestCommand | UpdateClimateTestCommand = UpdateClimateTestCommand(
            **common_values,
            reason=self.change_reason_selector.value(),
        )
    else:
        command = CreateClimateTestCommand(**common_values)

    try:
        self._on_save(command)
    except ValueError as error:
        self.save_button.disabled = False
        self._show_error(str(error))
        self._refresh()


def _install_new_test_fix() -> None:
    cls = polished_new_test_module.PolishedNewTestView
    cls.__init__ = _polished_init
    cls._clear_condition = _polished_clear_condition
    cls._recalculate = _polished_recalculate
    cls._submit = _polished_submit


_original_base_details_init = test_details_module.TestDetailsView.__init__


def _base_details_init(self, *args, **kwargs) -> None:
    _original_base_details_init(self, *args, **kwargs)
    if isinstance(self, polished_details_module.PolishedTestDetailsView):
        root = getattr(self, "root", None)
        controls = getattr(root, "controls", None)
        if isinstance(controls, list):
            controls.clear()


def _install_details_fix() -> None:
    test_details_module.TestDetailsView.__init__ = _base_details_init


def _record_operational_activity(
    self,
    *,
    actor_user_id: int | None,
    actor_label: str,
    action: str,
    details: str,
) -> None:
    with self._session_factory() as session:
        session.add(
            SecurityAuditEvent(
                actor_user_id=actor_user_id,
                actor_label=actor_label,
                action=action,
                details=details.strip() or None,
            )
        )
        session.commit()


def _delete_tests_as_administrator(
    self,
    test_ids: list[int],
    *,
    actor_user_id: int | None,
    actor_label: str,
    reason: str,
) -> int:
    normalized_ids = list(dict.fromkeys(int(test_id) for test_id in test_ids))
    normalized_reason = reason.strip()
    if not normalized_ids:
        raise ValueError("Selecione ao menos um ensaio para excluir.")
    if len(normalized_reason) < 10:
        raise ValueError("Informe um motivo de exclusão com pelo menos 10 caracteres.")

    with self._session_factory() as session:
        records = list(
            session.scalars(
                select(ClimateTestRecord).where(ClimateTestRecord.id.in_(normalized_ids))
            ).all()
        )
        found = {record.id for record in records}
        missing = [test_id for test_id in normalized_ids if test_id not in found]
        if missing:
            raise LookupError(
                "Ensaio(s) não encontrado(s): " + ", ".join(f"#{test_id}" for test_id in missing)
            )

        for record in records:
            details = (
                f"Ensaio #{record.id}; processo={record.process_number}; cliente={record.client}; "
                f"produto={record.product}; situação={record.situation}; motivo={normalized_reason}"
            )
            session.add(
                SecurityAuditEvent(
                    actor_user_id=actor_user_id,
                    actor_label=actor_label,
                    action="climate_test_deleted_by_admin",
                    details=details,
                )
            )
            session.delete(record)
        session.commit()
        return len(records)


def _delete_test_as_administrator(
    self,
    test_id: int,
    *,
    actor_user_id: int | None,
    actor_label: str,
    reason: str,
) -> None:
    _delete_tests_as_administrator(
        self,
        [test_id],
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        reason=reason,
    )


def _security_detail(details: str | None, key: str) -> str | None:
    for part in (details or "").split(";"):
        name, separator, value = part.strip().partition("=")
        if separator and name.strip() == key:
            return value.strip()
    return None


def _utc_sort_key(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _list_audit_history(self) -> list[AuditHistoryEntry]:
    entries = ClimateTestRepository.list_audit_history(self)
    with self._session_factory() as session:
        records = list(
            session.scalars(
                select(SecurityAuditEvent).where(
                    SecurityAuditEvent.action.in_(
                        (
                            "resource_paused",
                            "resource_resumed",
                            "climate_test_deleted_by_admin",
                        )
                    )
                )
            ).all()
        )

    for record in records:
        if record.action == "climate_test_deleted_by_admin":
            process_number = _security_detail(record.details, "processo") or "—"
            client = _security_detail(record.details, "cliente") or "Ensaio excluído"
            reason = _security_detail(record.details, "motivo")
            entries.append(
                AuditHistoryEntry(
                    test_id=0,
                    client=client,
                    process_number=process_number,
                    action="Ensaio excluído do histórico",
                    actor=record.actor_label,
                    occurred_at=record.occurred_at,
                    new_value=record.details,
                    reason=reason,
                )
            )
            continue

        label = _security_detail(record.details, "recurso") or "Equipamento"
        affected = _security_detail(record.details, "afetados") or "0"
        reason = _security_detail(record.details, "motivo")
        paused = record.action == "resource_paused"
        entries.append(
            AuditHistoryEntry(
                test_id=0,
                client="Equipamento",
                process_number=label,
                action=f"{label} {'pausada' if paused else 'retomada'}",
                actor=record.actor_label,
                occurred_at=record.occurred_at,
                new_value=f"{affected} ensaio(s) afetado(s).",
                reason=reason,
            )
        )

    entries.sort(key=lambda item: _utc_sort_key(item.occurred_at), reverse=True)
    return entries


def _install_repository_fix() -> None:
    cls = ProductionClimateTestRepository
    cls.record_operational_activity = _record_operational_activity
    cls.delete_tests_as_administrator = _delete_tests_as_administrator
    cls.delete_test_as_administrator = _delete_test_as_administrator
    cls.list_audit_history = _list_audit_history


def _build_history_view(events: list[AuditHistoryEntry], *, on_select) -> ft.Column:
    rows: list[ft.Control] = []
    for event in events:
        description = event.new_value or event.reason or "Evento registrado"
        if "; regra=" in description:
            description = description.split("; regra=", maxsplit=1)[0]
        if event.reason and event.reason not in description:
            description = f"{description} • Motivo: {event.reason}"

        live_test = bool(event.test_id and event.test_id > 0)
        meta: list[ft.Control] = [
            ft.Text(
                f"{event.client} / {event.process_number}",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=AppColors.TEXT_PRIMARY,
            )
        ]
        if live_test:
            meta.append(
                ft.Text(
                    f"Ensaio #{event.test_id}",
                    size=11,
                    color=AppColors.TEXT_SECONDARY,
                )
            )
        meta.append(
            ft.Text(
                f"{history_module.format_datetime(event.occurred_at)} • {event.actor}",
                size=10,
                color=AppColors.TEXT_SECONDARY,
            )
        )

        rows.append(
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=14,
                border=ft.Border.all(1, AppColors.DIVIDER),
                padding=15,
                on_click=(
                    (lambda _event, test_id=event.test_id: on_select(test_id))
                    if live_test
                    else None
                ),
                content=ft.ResponsiveRow(
                    spacing=14,
                    run_spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Container(
                            col={"xs": 12, "md": 8, "lg": 9},
                            content=ft.Row(
                                spacing=14,
                                controls=[
                                    ft.Container(
                                        width=38,
                                        height=38,
                                        border_radius=12,
                                        bgcolor=AppColors.PRIMARY_LIGHT,
                                        alignment=ft.Alignment.CENTER,
                                        content=ft.Icon(
                                            ft.Icons.HISTORY,
                                            color=AppColors.PRIMARY,
                                            size=20,
                                        ),
                                    ),
                                    ft.Column(
                                        expand=True,
                                        spacing=2,
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
                                controls=meta,
                            ),
                        ),
                    ],
                ),
            )
        )

    if not rows:
        rows.append(
            ft.Container(
                bgcolor=AppColors.SURFACE,
                border_radius=14,
                border=ft.Border.all(1, AppColors.DIVIDER),
                padding=28,
                content=ft.Text("Nenhum evento registrado.", color=AppColors.TEXT_SECONDARY),
            )
        )

    return ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=18,
        controls=[
            ft.Column(
                spacing=3,
                controls=[
                    ft.Text(
                        "Registro de atividades",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=AppColors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "Ações importantes dos ensaios, equipamentos e exclusões administrativas.",
                        size=14,
                        color=AppColors.TEXT_SECONDARY,
                    ),
                ],
            ),
            ft.Container(
                bgcolor=AppColors.INFO_LIGHT,
                border_radius=12,
                padding=14,
                content=ft.Text(
                    "Pausas e retomadas das câmaras são registradas mesmo quando nenhum ensaio "
                    "está ativo. Exclusões administrativas permanecem como evidência de auditoria.",
                    size=12,
                    color=AppColors.TEXT_PRIMARY,
                ),
            ),
            *rows,
        ],
    )


class _ProductionTestsListView(tests_list_module.TestsListView):
    def __init__(self, *args, on_delete_many=None, **kwargs) -> None:
        self._delete_many_callback = on_delete_many
        self._selected_ids: set[int] = set()
        super().__init__(*args, **kwargs)

        self.selection_status = ft.Text("", size=11, color=AppColors.DANGER)
        self.delete_button = ft.Button(
            content="Excluir selecionados",
            icon=ft.Icons.DELETE_OUTLINE,
            color=AppColors.DANGER,
            disabled=True,
            visible=on_delete_many is not None,
            on_click=self._show_bulk_delete_dialog,
        )

        if on_delete_many is not None:
            header = self.root.controls[0] if self.root.controls else None
            if isinstance(header, ft.Row) and header.controls:
                actions = header.controls[-1]
                if isinstance(actions, ft.Row):
                    actions.controls.insert(0, self.delete_button)
            self.root.controls.insert(3, self.selection_status)

    def _row(self, item):
        base = super()._row(item)
        if self._delete_many_callback is None:
            return base

        checkbox = ft.Checkbox(value=item.id in self._selected_ids, tooltip=f"Selecionar ensaio #{item.id}")
        checkbox.on_change = lambda _event, test_id=item.id, box=checkbox: self._toggle_selected(
            test_id, bool(box.value)
        )
        base.expand = True
        base.bgcolor = None
        base.padding = ft.Padding.symmetric(horizontal=8, vertical=12)
        return ft.Container(
            bgcolor=AppColors.SURFACE,
            border=ft.Border.all(1, AppColors.DIVIDER),
            border_radius=14,
            padding=ft.Padding.only(left=8, top=4, right=8, bottom=4),
            content=ft.Row(
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[checkbox, base],
            ),
        )

    def _toggle_selected(self, test_id: int, selected: bool) -> None:
        if selected:
            self._selected_ids.add(test_id)
        else:
            self._selected_ids.discard(test_id)
        count = len(self._selected_ids)
        self.delete_button.disabled = count == 0
        self.delete_button.content = f"Excluir selecionados ({count})" if count else "Excluir selecionados"
        self.selection_status.value = (
            f"{count} ensaio(s) selecionado(s) • exclusão disponível somente ao administrador"
            if count
            else ""
        )
        _safe_update(self.delete_button)
        _safe_update(self.selection_status)

    def _show_bulk_delete_dialog(self, _event: object | None = None) -> None:
        if self._delete_many_callback is None or not self._selected_ids:
            return
        page = self.root.page
        selected_ids = sorted(self._selected_ids)
        reason = ft.TextField(
            label="Motivo da exclusão *",
            hint_text="Ex.: cadastros fictícios usados somente para validar o sistema.",
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=500,
            bgcolor=AppColors.SURFACE,
            border_color=AppColors.DIVIDER,
            focused_border_color=AppColors.PRIMARY,
        )
        error = ft.Text("", size=11, color=AppColors.DANGER)

        def confirm(_confirm_event: object | None = None) -> None:
            normalized = reason.value.strip()
            if len(normalized) < 10:
                reason.error = "Informe um motivo com pelo menos 10 caracteres."
                error.value = "A justificativa é obrigatória para preservar a rastreabilidade."
                _safe_update(reason)
                _safe_update(error)
                return
            page.pop_dialog()
            self._delete_many_callback(selected_ids, normalized)

        page.show_dialog(
            styled_dialog(
                title=f"Excluir {len(selected_ids)} ensaio(s)?",
                subtitle="A operação é restrita ao administrador",
                icon=ft.Icons.DELETE_FOREVER_OUTLINED,
                danger=True,
                content=ft.Column(
                    width=560,
                    tight=True,
                    spacing=12,
                    controls=[
                        dialog_banner(
                            "Os ensaios selecionados deixarão as telas operacionais. Um registro "
                            "administrativo de cada exclusão ficará preservado no Registro de atividades.",
                            icon=ft.Icons.WARNING_AMBER,
                            danger=True,
                        ),
                        reason,
                        error,
                    ],
                ),
                actions=dialog_actions(
                    page=page,
                    primary_label="Excluir selecionados",
                    primary_icon=ft.Icons.DELETE_FOREVER,
                    on_confirm=confirm,
                    danger=True,
                    cancel_label="Cancelar",
                ),
            )
        )


def _build_tests_list_view(*args, on_delete_many=None, **kwargs) -> ft.Column:
    return _ProductionTestsListView(*args, on_delete_many=on_delete_many, **kwargs).root


def _walk(control: ft.Control):
    yield control
    child = getattr(control, "content", None)
    if isinstance(child, ft.Control):
        yield from _walk(child)
    children = getattr(control, "controls", None)
    if isinstance(children, list):
        for item in children:
            if isinstance(item, ft.Control):
                yield from _walk(item)


def _button_label(control: ft.Control) -> str:
    if not isinstance(control, (ft.Button, ft.TextButton, ft.IconButton)):
        return ""
    content = getattr(control, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, ft.Text):
        return content.value or ""
    return ""


_original_settings_builder = production_settings_module.build_production_settings_view


def _fixed_settings_builder(**kwargs) -> ft.Control:
    original = _original_settings_builder(**kwargs)
    controls = list(getattr(original, "controls", []) or [])
    if hasattr(original, "controls"):
        original.controls = []
    root = ft.Column(
        expand=True,
        scroll=ft.ScrollMode.AUTO,
        spacing=20,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=controls,
    )

    callback = kwargs.get("on_report_system_incident")
    refresh_callback = kwargs.get("on_refresh")
    target = next(
        (
            control
            for control in _walk(root)
            if isinstance(control, ft.Button) and _button_label(control) == "Registrar falha"
        ),
        None,
    )
    if isinstance(target, ft.Button) and callable(callback):

        def show_dialog(_event: object | None = None) -> None:
            page = target.page
            from climatetest_manager.domain.incidents import INCIDENT_REASONS, incident_reason

            reason_selector = ft.Dropdown(
                label="Motivo da falha",
                value="software_crash",
                options=[ft.DropdownOption(key=reason.code, text=reason.label) for reason in INCIDENT_REASONS],
                bgcolor=AppColors.SURFACE,
                border_color=AppColors.DIVIDER,
                focused_border_color=AppColors.PRIMARY,
            )
            initial = incident_reason("software_crash")
            priority = ft.Text(
                f"Prioridade automática: {initial.severity}",
                size=12,
                weight=ft.FontWeight.BOLD,
                color=AppColors.DANGER,
            )
            guidance = ft.Text(initial.guidance, size=11, color=AppColors.TEXT_SECONDARY)
            description = ft.TextField(
                label="O que aconteceu?",
                hint_text="Descreva a falha, quando ocorreu e o que foi afetado.",
                multiline=True,
                min_lines=3,
                max_lines=5,
                max_length=2000,
                bgcolor=AppColors.SURFACE,
                border_color=AppColors.DIVIDER,
                focused_border_color=AppColors.PRIMARY,
            )
            immediate_action = ft.TextField(
                label="Qual ação você tomou ao reconhecer a falha?",
                hint_text="Ex.: interrompi a operação e conferi os registros.",
                multiline=True,
                min_lines=2,
                max_lines=4,
                max_length=2000,
                bgcolor=AppColors.SURFACE,
                border_color=AppColors.DIVIDER,
                focused_border_color=AppColors.PRIMARY,
            )
            error = ft.Text("", size=11, color=AppColors.DANGER)

            def update_priority(_change_event: object | None = None) -> None:
                selected = incident_reason(reason_selector.value or "other")
                priority.value = f"Prioridade automática: {selected.severity}"
                priority.color = (
                    AppColors.DANGER
                    if selected.severity in {"Crítica", "Alta"}
                    else AppColors.WARNING
                )
                guidance.value = selected.guidance
                _safe_update(priority)
                _safe_update(guidance)

            reason_selector.on_select = update_priority
            submitted = False
            save_button = ft.Button(
                content="Salvar registro",
                icon=ft.Icons.SAVE_OUTLINED,
                bgcolor=AppColors.PRIMARY,
                color=AppColors.WHITE,
            )

            def confirm(_confirm_event: object | None = None) -> None:
                nonlocal submitted
                if submitted:
                    return
                description_value = description.value.strip()
                action_value = immediate_action.value.strip()
                description.error = None
                immediate_action.error = None
                if len(description_value) < 10:
                    description.error = "Descreva a falha com pelo menos 10 caracteres."
                    _safe_update(description)
                    return
                if len(action_value) < 10:
                    immediate_action.error = "Informe a ação imediata com pelo menos 10 caracteres."
                    _safe_update(immediate_action)
                    return

                submitted = True
                save_button.disabled = True
                save_button.content = "Salvando..."
                _safe_update(save_button)
                try:
                    result = callback(
                        reason_selector.value or "other",
                        description_value,
                        action_value,
                    )
                except Exception as exc:
                    submitted = False
                    save_button.disabled = False
                    save_button.content = "Salvar registro"
                    error.value = f"Não foi possível concluir o registro: {exc}"
                    _safe_update(save_button)
                    _safe_update(error)
                    return

                if result:
                    submitted = False
                    save_button.disabled = False
                    save_button.content = "Salvar registro"
                    error.value = str(result)
                    _safe_update(save_button)
                    _safe_update(error)
                    return

                page.pop_dialog()
                if callable(refresh_callback):
                    refresh_callback()
                page.show_dialog(
                    ft.SnackBar(
                        content="Falha registrada com sucesso.",
                        bgcolor=AppColors.PRIMARY,
                        show_close_icon=True,
                    )
                )

            save_button.on_click = confirm
            page.show_dialog(
                styled_dialog(
                    title="Registrar falha do sistema",
                    subtitle="Evidência para avaliação de impacto e ação corretiva",
                    icon=ft.Icons.BUG_REPORT_OUTLINED,
                    scrollable=False,
                    content=ft.Container(
                        width=610,
                        bgcolor=AppColors.SURFACE,
                        content=ft.Column(
                            tight=True,
                            spacing=11,
                            controls=[
                                dialog_banner(
                                    "A prioridade é definida automaticamente pelo motivo. Registre o impacto e a contenção adotada."
                                ),
                                reason_selector,
                                ft.Container(
                                    border_radius=11,
                                    bgcolor=AppColors.WARNING_LIGHT,
                                    padding=11,
                                    content=ft.Column(spacing=3, controls=[priority, guidance]),
                                ),
                                description,
                                immediate_action,
                                error,
                            ],
                        ),
                    ),
                    actions=[
                        ft.TextButton(content="Voltar", on_click=lambda _click: page.pop_dialog()),
                        save_button,
                    ],
                )
            )

        target.on_click = show_dialog

    return apply_interaction_polish(root)


_ProductionApp = production_app.ProductionClimateTestApplication
_original_build_current_shell = _ProductionApp._build_current_shell


def _detach_current_content(self) -> None:
    screen = getattr(self, "_screen_container", None)
    current = getattr(self, "_current_content", None)
    if screen is None or current is None:
        return
    old_shell = getattr(screen, "content", None)
    controls = getattr(old_shell, "controls", None)
    if not isinstance(controls, list):
        return
    for control in controls:
        if isinstance(control, ft.Container) and control.content is current:
            control.content = None
            break


def _build_current_shell(self):
    _detach_current_content(self)
    return _original_build_current_shell(self)


def _refresh_shell_frame(self) -> None:
    if self._screen_container is None or self._current_content is None:
        return
    self._screen_container.content = self._build_current_shell()
    _safe_update(self._screen_container)
    self._restore_scroll_position()


async def _watch_local_notifications(self) -> None:
    try:
        current = self._production_repository.list_user_notifications(
            user_id=self._current_user.id,
            is_admin=self._current_user.is_admin,
        )
        known = {(item.source_kind, item.source_id) for item in current}
        last_unread = sum(not item.is_read for item in current)
    except (OSError, RuntimeError, ValueError):
        known = set()
        last_unread = -1

    while self._notification_watch_active:
        await asyncio.sleep(5)
        try:
            current = self._production_repository.list_user_notifications(
                user_id=self._current_user.id,
                is_admin=self._current_user.is_admin,
            )
        except (OSError, RuntimeError, ValueError):
            continue

        unread_count = sum(not item.is_read for item in current)
        if unread_count != last_unread:
            last_unread = unread_count
            self._refresh_shell_frame()

        current_keys = {(item.source_kind, item.source_id) for item in current}
        pending = [
            item
            for item in current
            if not item.is_read and (item.source_kind, item.source_id) not in known
        ]
        known = current_keys

        for item in reversed(pending):
            if not self._notification_watch_active:
                return
            delivered = await production_app.queue_desktop_toast(
                self._page,
                item.title,
                item.message,
                command_id=f"{item.source_kind}-{item.source_id}",
            )
            if item.source_kind == "incident" and self._current_user.is_admin:
                self._prepare_theme()
                first_line = item.message.splitlines()[0] if item.message else "Nova falha registrada"
                self._show_message(f"{item.title}: {first_line}")
            if delivered:
                await asyncio.sleep(0.8)


def _pause_resource(self, resource: str, reason: str) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    try:
        equipment = EquipmentResource(resource)
        affected = self._service.pause_resource(resource, reason)
        self._production_repository.record_operational_activity(
            actor_user_id=self._current_user.id,
            actor_label=self._current_user.actor_label,
            action="resource_paused",
            details=f"recurso={equipment.label}; afetados={affected}; motivo={reason.strip()}",
        )
    except (ValueError, LookupError) as error:
        self._show_message(str(error), error=True)
        return
    self.show_dashboard()
    self._show_message(
        f"{equipment.label} pausada. {affected} ensaio(s) tiveram a contagem congelada."
    )


def _resume_resource(self, resource: str) -> None:
    if not self._current_user.can_operate:
        self._show_message("Este perfil possui acesso somente para consulta.", error=True)
        return
    try:
        equipment = EquipmentResource(resource)
        affected = self._service.resume_resource(resource)
        self._production_repository.record_operational_activity(
            actor_user_id=self._current_user.id,
            actor_label=self._current_user.actor_label,
            action="resource_resumed",
            details=f"recurso={equipment.label}; afetados={affected}",
        )
    except (ValueError, LookupError) as error:
        self._show_message(str(error), error=True)
        return
    self.show_dashboard()
    self._show_message(f"{equipment.label} retomada. {affected} prazo(s) foram recalculados.")


def _delete_tests_as_admin(self, test_ids: list[int], reason: str) -> None:
    if not self._current_user.is_admin:
        self._show_message("Somente administradores podem excluir ensaios.", error=True)
        return
    try:
        deleted = self._production_repository.delete_tests_as_administrator(
            test_ids,
            actor_user_id=self._current_user.id,
            actor_label=self._current_user.actor_label,
            reason=reason,
        )
    except (LookupError, ValueError) as error:
        self._show_message(str(error), error=True)
        return
    self._active_test_id = None
    self.show_tests()
    self._show_message(
        f"{deleted} ensaio(s) removido(s). A exclusão ficou registrada na auditoria."
    )


def _show_tests(self) -> None:
    self._prepare_theme()
    content = _build_tests_list_view(
        self._service.list_tests(),
        on_select=self.show_details,
        on_new_test=(self.show_new_test if self._current_user.can_operate else None),
        on_export=self._export_csv,
        on_delete_many=(self._delete_tests_as_admin if self._current_user.is_admin else None),
    )
    self._render(content, selected_view="tests")


def _show_details(self, test_id: int) -> None:
    self._prepare_theme()
    self._active_test_id = test_id
    details = self._service.get_details(test_id)
    content = polished_details_module.build_polished_test_details_view(
        details,
        on_back=self.show_tests,
        read_only=self._current_user.is_viewer,
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
        on_admin_delete=(
            (lambda reason: self._delete_test_as_admin(test_id, reason))
            if self._current_user.is_admin
            else None
        ),
        on_change_timestamp=lambda timestamp, value, reason: self._perform(
            test_id,
            lambda: self._service.change_operational_timestamp(test_id, timestamp, value, reason),
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
    self._render(content, selected_view="details")


def _show_history(self) -> None:
    self._prepare_theme()
    self._render(
        _build_history_view(self._service.list_history(), on_select=self.show_details),
        selected_view="history",
    )


def _install_application_fix() -> None:
    _ProductionApp._build_current_shell = _build_current_shell
    _ProductionApp._refresh_shell_frame = _refresh_shell_frame
    _ProductionApp._watch_local_notifications = _watch_local_notifications
    _ProductionApp._pause_resource = _pause_resource
    _ProductionApp._resume_resource = _resume_resource
    _ProductionApp._delete_tests_as_admin = _delete_tests_as_admin
    _ProductionApp.show_tests = _show_tests
    _ProductionApp.show_details = _show_details
    _ProductionApp.show_history = _show_history
    production_app.build_production_settings_view = _fixed_settings_builder


def install_round3_fixes() -> None:
    """Aplica os hotfixes uma única vez por processo."""

    if getattr(production_app, "_round3_fixes_installed", False):
        return
    _install_dark_palettes()
    _install_sidebar_fix()
    _install_new_test_fix()
    _install_details_fix()
    _install_repository_fix()
    _install_application_fix()
    history_module.build_history_view = _build_history_view
    tests_list_module.build_tests_list_view = _build_tests_list_view
    production_settings_module.build_production_settings_view = _fixed_settings_builder
    production_app._round3_fixes_installed = True


install_round3_fixes()
main = production_app.main
