from __future__ import annotations

from pathlib import Path
from urllib.parse import quote, urlparse

from bs4 import BeautifulSoup

URL_ATTRS = {
    "img": ("src",),
    "a": ("href",),
    "source": ("src",),
    "video": ("src", "poster"),
    "audio": ("src",),
    "iframe": ("src",),
    "link": ("href",),
    "object": ("data",),
    "embed": ("src",),
    "script": ("src",),
}

_ABSOLUTE_SCHEMES = {"http", "https", "mailto", "tel", "data", "javascript", "ftp", "file"}


def _is_relative(url: str) -> bool:
    if not url:
        return False
    if url.startswith(("#", "/")):
        return False
    parsed = urlparse(url)
    if parsed.scheme and parsed.scheme.lower() in _ABSOLUTE_SCHEMES:
        return False
    if parsed.scheme:
        return False
    return True


def _build_base_url(course: str, rel_path: str) -> str:
    base = "/files/" + quote(course, safe="")
    if rel_path:
        encoded = "/".join(quote(p, safe="") for p in rel_path.split("/") if p)
        base = f"{base}/{encoded}"
    return base


def _rewrite_relative(url: str, base_url: str) -> str:
    """Přepíše relativní URL na absolutní /files/.../url.

    Zachovává query string a fragment. Každou path-komponentu enkóduje zvlášť.
    """
    parsed = urlparse(url)
    path = parsed.path
    parts = [quote(p, safe="") for p in path.split("/") if p]
    new_path = base_url + ("/" + "/".join(parts) if parts else "")
    if parsed.query:
        new_path += f"?{parsed.query}"
    if parsed.fragment:
        new_path += f"#{parsed.fragment}"
    return new_path


def render_index(index_path: Path, course: str, rel_path: str) -> str:
    """Načte index.html, vrátí HTML fragment vhodný pro innerHTML.

    - Vybere obsah <div class="vtbegenerated">, fallback na <body>.
    - Přepíše relativní URL v `URL_ATTRS` na absolutní /files/...
    """
    raw = index_path.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw, "html.parser")

    base_url = _build_base_url(course, rel_path)

    for tag_name, attrs in URL_ATTRS.items():
        for tag in soup.find_all(tag_name):
            for attr in attrs:
                value = tag.get(attr)
                if not value or not _is_relative(value):
                    continue
                tag[attr] = _rewrite_relative(value, base_url)

    container = soup.select_one("div.vtbegenerated")
    if container is None:
        container = soup.body
    if container is None:
        return raw

    # Vrátíme jen vnitřní obsah kontejneru.
    return container.decode_contents()
