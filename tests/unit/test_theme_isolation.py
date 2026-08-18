from contextvars import Context

from climatetest_manager.ui.theme import AppColors


def _select(mode: str) -> tuple[str, str, str]:
    AppColors.apply_mode(mode)
    return AppColors.PAGE_BACKGROUND, AppColors.SURFACE, AppColors.PRIMARY


def test_theme_palette_is_isolated_between_execution_contexts() -> None:
    server_session = Context()
    workstation_session = Context()

    server_light = server_session.run(_select, "light")
    station_dark = workstation_session.run(_select, "dark")

    assert server_light != station_dark
    assert server_session.run(lambda: AppColors.PAGE_BACKGROUND) == server_light[0]
    assert workstation_session.run(lambda: AppColors.PAGE_BACKGROUND) == station_dark[0]

    workstation_session.run(_select, "ocean")

    assert server_session.run(lambda: AppColors.PAGE_BACKGROUND) == server_light[0]
    assert workstation_session.run(lambda: AppColors.current_mode()) == "ocean"
