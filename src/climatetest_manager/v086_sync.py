"""Sincronização leve da Dashboard entre sessões conectadas ao servidor central."""

from __future__ import annotations

import asyncio

from climatetest_manager import production_app, v086_runtime


def _dashboard_signature(app: production_app.ProductionClimateTestApplication) -> tuple:
    items = app._service.list_dashboard_tests()
    return tuple(
        (
            item.id,
            item.client,
            item.process_number,
            item.product,
            item.sample_quantity,
            item.situation,
            item.deadline_condition,
            item.nominal_end_at,
            item.maximum_end_at,
            item.is_paused,
            item.pause_reason,
        )
        for item in items
    )


async def _smart_dashboard_sync_loop(
    app: production_app.ProductionClimateTestApplication,
) -> None:
    """Consulta o estado compartilhado sem repintar a tela quando nada mudou."""

    last_signature: tuple | None = None
    while getattr(app, "_v086_sync_active", False):
        await asyncio.sleep(5)
        if not getattr(app, "_v086_sync_active", False):
            return
        if getattr(app, "_selected_view", None) != "dashboard":
            last_signature = None
            continue
        if getattr(app, "_v086_sync_refreshing", False):
            continue
        try:
            signature = _dashboard_signature(app)
        except (OSError, RuntimeError, ValueError):
            continue
        if last_signature is None:
            last_signature = signature
            continue
        if signature == last_signature:
            continue
        last_signature = signature
        app._v086_sync_refreshing = True
        try:
            app.show_dashboard()
        except (OSError, RuntimeError, ValueError):
            pass
        finally:
            app._v086_sync_refreshing = False


def install() -> None:
    v086_runtime._dashboard_sync_loop = _smart_dashboard_sync_loop
