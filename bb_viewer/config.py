from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

_WIN_LONG_PATH_PREFIX = "\\\\?\\"


def _enable_windows_long_paths(p: Path) -> Path:
    """Na Windows přidá `\\?\` prefix, který bypassuje MAX_PATH (260) limit.
    Bez prefixu by `iterdir()` nad hluboce zanořenými adresáři padalo na
    `FileNotFoundError [WinError 3]`. Prefix se propisuje do všech odvozených
    path operací (joinpath, resolve, is_relative_to)."""
    if os.name != "nt":
        return p
    s = str(p)
    if s.startswith(_WIN_LONG_PATH_PREFIX) or s.startswith("\\\\"):
        return p
    return Path(_WIN_LONG_PATH_PREFIX + s)


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    courses_dir: Path
    host: str
    port: int
    open_browser: bool


def load_config(config_path: Path) -> Config:
    if not config_path.is_file():
        raise ConfigError(
            f"Konfigurační soubor nebyl nalezen: {config_path}\n"
            f"Zkopíruj config.example.toml na config.toml a vyplň cestu k adresáři kurzů."
        )

    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(
            f"Chyba v {config_path.name}: {e}\n"
            f"Tip pro Windows cesty: TOML interpretuje '\\' jako escape. Použij\n"
            f"  - dvojité lomítko:   \"C:\\\\Users\\\\jmeno\\\\...\"\n"
            f"  - lomítka vpřed:     \"C:/Users/jmeno/...\"\n"
            f"  - literal string:    'C:\\Users\\jmeno\\...'  (jednoduché uvozovky)"
        ) from e

    paths = data.get("paths") or {}
    raw_dir = paths.get("courses_dir")
    if not raw_dir:
        raise ConfigError("V config.toml chybí [paths] courses_dir.")

    courses_dir = Path(raw_dir)
    if not courses_dir.is_absolute():
        courses_dir = config_path.parent / courses_dir
    courses_dir = courses_dir.resolve()

    if not courses_dir.is_dir():
        raise ConfigError(
            f"Adresář kurzů neexistuje nebo není složka: {courses_dir}"
        )

    courses_dir = _enable_windows_long_paths(courses_dir)

    server = data.get("server") or {}
    host = str(server.get("host", "127.0.0.1"))
    port = int(server.get("port", 0))
    open_browser = bool(server.get("open_browser", True))

    return Config(
        courses_dir=courses_dir,
        host=host,
        port=port,
        open_browser=open_browser,
    )
