from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]


def test_remote_deployment_is_product_scoped_and_verifies_each_copy() -> None:
    script = (PROJECT / "scripts" / "deploy_update_to_stations.ps1").read_text(encoding="utf-8")

    assert "com.jhoncts.climatetestmanager" in script
    assert "server-mode.marker" in script
    assert "Get-FileHash" in script
    assert "$remoteHash -ne $actualHash" in script
    assert '"/ROLE=client"' in script
    assert '"--check-only"' in script
    assert "Export-Csv" in script


def test_station_bootstrap_does_not_store_credentials_or_trust_wildcards() -> None:
    script = (PROJECT / "scripts" / "enable_remote_update_station.ps1").read_text(encoding="utf-8")

    assert "Enable-PSRemoting" in script
    assert "Set-NetFirewallRule -Enabled True -RemoteAddress $addresses" in script
    assert "server-mode.marker" in script
    assert "LocalAccountTokenFilterPolicy" not in script
    assert "WSMan:\\localhost\\Client\\TrustedHosts" not in script


def test_installer_and_build_include_controlled_update_tools() -> None:
    installer = (PROJECT / "installer" / "ClimateTestManager.iss").read_text(encoding="utf-8")
    build = (PROJECT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    for name in (
        "deploy_update_to_stations.ps1",
        "enable_remote_update_station.ps1",
        "stations.example.txt",
    ):
        assert name in installer
        assert name in build
    assert "Atualizar estações da rede" in installer
    assert "ApprovedUpdates" in installer


def test_public_tree_has_no_test_environment_organization_identifier() -> None:
    blocked_identifier = "cp" + "ex"
    searchable_suffixes = {".py", ".ps1", ".md", ".txt", ".toml", ".yml", ".iss"}
    matches: list[str] = []

    for path in PROJECT.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in searchable_suffixes:
            continue
        if any(
            part in {".git", ".venv", ".pytest_cache", ".ruff_cache", "build", "dist"}
            for part in path.parts
        ):
            continue
        if blocked_identifier in path.read_text(encoding="utf-8", errors="ignore").casefold():
            matches.append(str(path.relative_to(PROJECT)))

    assert matches == []
