#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

MCP_URL = "https://praca-mcp.micek.top/mcp"
MARKETPLACE = "olekgoli/jobscout-codex"


class InstallError(RuntimeError):
    pass


def run_codex(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["codex", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def prompt_key() -> str:
    if key := os.environ.get("JOBSCOUT_MCP_KEY"):
        return key
    if sys.platform == "darwin":
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'text returned of (display dialog "Wpisz klucz Job Scout MCP" '
                'default answer "" with hidden answer buttons {"Anuluj", "OK"} '
                'default button "OK")',
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise InstallError("Anulowano podanie klucza.")
        return result.stdout.strip()
    if os.name == "nt":
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "$s=Read-Host 'Klucz Job Scout MCP' -AsSecureString;"
                "$p=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($s);"
                "try {[Runtime.InteropServices.Marshal]::PtrToStringBSTR($p)} "
                "finally {[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($p)}",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode:
            raise InstallError("Nie udało się odczytać klucza.")
        return result.stdout.strip()
    if sys.stdin.isatty():
        return getpass.getpass("Klucz Job Scout MCP: ").strip()
    raise InstallError("Uruchom instalator w terminalu, aby bezpiecznie podać klucz.")


def validate_key(key: str) -> None:
    if not key or quote(key, safe="") != key:
        raise InstallError("Klucz musi być jednym niepustym segmentem URL.")


def verify_key(key: str) -> None:
    body = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "jobscout-installer", "version": "1"},
            },
        }
    ).encode()
    request = Request(
        MCP_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urlopen(request, timeout=15) as response:
            if response.status != 200:
                raise InstallError(f"Job Scout MCP zwrócił HTTP {response.status}.")
    except HTTPError as exc:
        if exc.code == 401:
            raise InstallError("Klucz Job Scout MCP jest nieprawidłowy.") from None
        raise InstallError(f"Job Scout MCP zwrócił HTTP {exc.code}.") from None
    except URLError as exc:
        raise InstallError(f"Nie można połączyć się z Job Scout MCP: {exc.reason}") from None


def install_plugin() -> str:
    added = run_codex(
        "plugin",
        "marketplace",
        "add",
        MARKETPLACE,
        "--ref",
        "main",
        "--json",
    )
    marketplace_name = json.loads(added.stdout)["marketplaceName"]
    run_codex("plugin", "add", f"jobscout@{marketplace_name}", "--json")
    return marketplace_name


def add_static_header(config_path: Path, key: str) -> None:
    lines = config_path.read_text().splitlines()
    section = "[mcp_servers.jobscout]"
    try:
        start = lines.index(section)
    except ValueError as exc:
        raise InstallError("Codex nie utworzył konfiguracji MCP.") from exc
    end = next(
        (index for index in range(start + 1, len(lines)) if lines[index].startswith("[")),
        len(lines),
    )
    header = f"http_headers = {{ Authorization = {json.dumps(f'Bearer {key}')} }}"
    lines.insert(end, header)
    config_path.write_text("\n".join(lines) + "\n")
    config_path.chmod(0o600)


def configure_mcp(key: str) -> None:
    run_codex("mcp", "remove", "jobscout", check=False)
    run_codex("mcp", "add", "jobscout", "--url", MCP_URL)
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    add_static_header(codex_home / "config.toml", key)


def self_test() -> None:
    validate_key("abc_DEF-123")
    for invalid in ("", "a/b", "two words"):
        try:
            validate_key(invalid)
        except InstallError:
            pass
        else:
            raise AssertionError(f"accepted invalid key: {invalid!r}")
    with tempfile.TemporaryDirectory() as directory:
        config = Path(directory) / "config.toml"
        config.write_text('[mcp_servers.jobscout]\nurl = "https://example.test/mcp"\n')
        add_static_header(config, "test_key")
        text = config.read_text()
        assert text.count("http_headers") == 1
        assert 'Authorization = "Bearer test_key"' in text
    print("self-test passed")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Job Scout in Codex.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if shutil.which("codex") is None:
        raise InstallError("Najpierw zainstaluj lub zaktualizuj Codex.")
    key = prompt_key()
    validate_key(key)
    verify_key(key)
    marketplace_name = install_plugin()
    configure_mcp(key)
    print(f"Job Scout zainstalowany z marketplace {marketplace_name}.")
    print("Uruchom Codex ponownie i napisz: znajdź mi pracę")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (InstallError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(f"Błąd instalacji: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
