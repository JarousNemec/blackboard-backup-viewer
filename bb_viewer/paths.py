from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

HIDDEN_NAMES = {"Thumbs.db", ".DS_Store"}
ASSETS_DIR_NAME = "_assets"
INDEX_FILE = "index.html"


def safe_resolve(root: Path, *parts: str) -> Path:
    """Spojí parts a vrátí Path uvnitř root. Chrání před path traversal.

    - odmítá komponenty rovné `..` nebo prázdné,
    - odmítá absolutní komponenty,
    - po resolve ověří is_relative_to(root.resolve()).
    """
    root_resolved = root.resolve()
    cleaned: list[str] = []
    for raw in parts:
        if raw is None or raw == "":
            continue
        # part může být víc-úrovňová cesta (např. "Cvičení/Cvičení 5")
        for segment in raw.replace("\\", "/").split("/"):
            if segment == "" or segment == ".":
                continue
            if segment == "..":
                raise PermissionError("Path traversal odmítnut.")
            cleaned.append(segment)

    candidate = root_resolved.joinpath(*cleaned).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise PermissionError("Cesta mimo povolený root.")
    return candidate


def _is_hidden(name: str) -> bool:
    return name.startswith(".") or name in HIDDEN_NAMES


def list_courses(courses_dir: Path) -> list[dict]:
    """Top-level složky v courses_dir."""
    if not courses_dir.is_dir():
        return []
    out: list[dict] = []
    for entry in sorted(courses_dir.iterdir(), key=lambda p: p.name.lower()):
        if entry.is_dir() and not _is_hidden(entry.name):
            out.append({"name": entry.name})
    return out


def list_tree(course_root: Path) -> dict:
    """Rekurzivní strom složek pod course_root.

    Vrací uzly ve formátu:
      {"name": str, "path": str, "has_index": bool, "children": [...]}
    `path` je relativní vůči course_root, oddělovač "/", pro root je "".
    Soubory v listingu nejsou — ty se zjistí přes /api/content.
    """

    def walk(folder: Path, rel: str) -> dict:
        children: list[dict] = []
        has_index = (folder / INDEX_FILE).is_file()
        try:
            entries = sorted(folder.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            entries = []
        for entry in entries:
            if not entry.is_dir():
                continue
            if _is_hidden(entry.name) or entry.name == ASSETS_DIR_NAME:
                continue
            child_rel = f"{rel}/{entry.name}" if rel else entry.name
            children.append(walk(entry, child_rel))
        return {
            "name": folder.name if rel else course_root.name,
            "path": rel,
            "has_index": has_index,
            "children": children,
        }

    return walk(course_root, "")


def list_folder(folder: Path, course: str, rel_path: str) -> list[dict]:
    """Soubory v dané složce (bez index.html, bez _assets/, bez podsložek).

    Každý prvek: {"name": str, "url": str (URL kódovaná /files/...)}.
    """
    if not folder.is_dir():
        return []
    items: list[dict] = []
    base_url = "/files/" + quote(course, safe="")
    if rel_path:
        # rel_path má části oddělené "/", každou enkódujeme zvlášť
        encoded_parts = "/".join(quote(p, safe="") for p in rel_path.split("/") if p)
        base_url = f"{base_url}/{encoded_parts}"

    try:
        entries = sorted(folder.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return items
    for entry in entries:
        if not entry.is_file():
            continue
        if entry.name == INDEX_FILE or _is_hidden(entry.name):
            continue
        try:
            size = entry.stat().st_size
        except OSError:
            continue
        items.append({
            "name": entry.name,
            "url": f"{base_url}/{quote(entry.name, safe='')}",
            "size": size,
        })
    return items
