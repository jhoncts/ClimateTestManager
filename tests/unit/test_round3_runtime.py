"""Validações isoladas dos hotfixes aplicados antes da sessão Flet."""

from __future__ import annotations

import subprocess
import sys
import textwrap


def _run_runtime_script(source: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source)],
        capture_output=True,
        text=True,
        check=False,
        timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_runtime_fixes_sidebar_and_required_field_feedback() -> None:
    _run_runtime_script(
        """
        import flet as ft

        from climatetest_manager.round3_runtime import _navigation_surface
        from climatetest_manager.ui.views.polished_new_test import PolishedNewTestView

        regular = _navigation_surface(
            label="Ensaios",
            icon=ft.Icons.LIST_ALT,
            selected=False,
            compact=False,
            icon_size=20,
            on_click=lambda: None,
        )
        compact = _navigation_surface(
            label="Ensaios",
            icon=ft.Icons.LIST_ALT,
            selected=False,
            compact=True,
            icon_size=20,
            on_click=lambda: None,
        )
        assert len(regular.content.controls) == 2
        assert isinstance(regular.content.controls[1], ft.Container)
        assert isinstance(regular.content.controls[1].content, ft.Text)
        assert regular.content.controls[1].content.value == "Ensaios"
        assert len(compact.content.controls) == 1

        view = PolishedNewTestView(
            on_cancel=lambda: None,
            on_save=lambda _command: None,
        )
        assert view.save_button.disabled is False
        view.sample_quantity.value = ""
        view._submit()
        assert view.client.error == "Campo obrigatório."
        assert view.process_number.error == "Campo obrigatório."
        assert view.product.error == "Campo obrigatório."
        assert view.sample_quantity.error == "Campo obrigatório."
        assert view.delta_t.error == "Campo obrigatório."
        assert view.error_banner.visible is True
        assert "obrigatórios" in view.error_banner.content.controls[1].value
        """
    )


def test_runtime_fixes_global_activity_and_admin_multi_delete() -> None:
    _run_runtime_script(
        """
        from pathlib import Path
        from tempfile import TemporaryDirectory

        import climatetest_manager.round3_runtime  # noqa: F401
        from climatetest_manager.database.session import (
            create_session_factory,
            initialize_database,
        )
        from climatetest_manager.repositories.production import (
            ProductionClimateTestRepository,
        )
        from climatetest_manager.services.climate_tests import (
            ClimateTestService,
            CreateClimateTestCommand,
        )

        def command(process_number):
            return CreateClimateTestCommand(
                client="Teste",
                process_number=process_number,
                product="Produto fictício",
                epl="Gc",
                tamb_max_c="40",
                delta_t_max_k="30",
                selected_option="A",
            )

        with TemporaryDirectory() as temp_dir:
            engine = initialize_database(Path(temp_dir) / "round3.db")
            repository = ProductionClimateTestRepository(
                create_session_factory(engine)
            )
            service = ClimateTestService(repository)
            first_id = service.create(command("TESTE.1"))
            second_id = service.create(command("TESTE.2"))

            repository.record_operational_activity(
                actor_user_id=None,
                actor_label="Operador",
                action="resource_paused",
                details=(
                    "recurso=Câmara climática; afetados=0; "
                    "motivo=Manutenção preventiva"
                ),
            )
            history = repository.list_audit_history()
            pause_events = [
                event for event in history if event.action == "Câmara climática pausada"
            ]
            assert len(pause_events) == 1
            assert pause_events[0].reason == "Manutenção preventiva"
            assert pause_events[0].test_id == 0

            deleted = repository.delete_tests_as_administrator(
                [first_id, second_id],
                actor_user_id=None,
                actor_label="Administrador",
                reason="Cadastros fictícios usados na validação",
            )
            assert deleted == 2
            assert service.list_tests() == []
            history = repository.list_audit_history()
            deletion_events = [
                event
                for event in history
                if event.action == "Ensaio excluído do histórico"
            ]
            assert len(deletion_events) == 2
            assert all(event.test_id == 0 for event in deletion_events)
            engine.dispose()
        """
    )
