from __future__ import annotations

import http.server
import json
import mimetypes
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .config import Config, ConfigError, load_config
from .html_rewrite import render_index
from .paths import list_courses, list_folder, list_tree, safe_resolve

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_ROOT / "static"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.toml"

# Doplňky pro mimetypes
mimetypes.add_type("application/x-pkt", ".pkt")  # Cisco Packet Tracer
mimetypes.add_type("text/markdown", ".md")


class ViewerHandler(http.server.BaseHTTPRequestHandler):
    config: Config = None  # type: ignore[assignment]  # injected via factory

    server_version = "BlackboardBackupViewer/0.1"

    # --- routing -------------------------------------------------------------

    def do_GET(self) -> None:
        url = urlparse(self.path)
        path = url.path
        qs = parse_qs(url.query)

        try:
            if path in ("/", "/index.html"):
                return self._serve_static_file(STATIC_DIR / "index.html")

            if path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return

            if path.startswith("/static/"):
                rel = path[len("/static/"):]
                target = (STATIC_DIR / rel).resolve()
                if not target.is_relative_to(STATIC_DIR.resolve()):
                    return self.send_error(403)
                if not target.is_file():
                    return self.send_error(404)
                return self._serve_static_file(target)

            if path == "/api/courses":
                return self._send_json(list_courses(self.config.courses_dir))

            if path == "/api/tree":
                course = self._first_qs(qs, "course")
                course_root = safe_resolve(self.config.courses_dir, course)
                if not course_root.is_dir():
                    return self.send_error(404, "Kurz nenalezen.")
                return self._send_json(list_tree(course_root))

            if path == "/api/content":
                course = self._first_qs(qs, "course")
                rel = qs.get("path", [""])[0]
                folder = safe_resolve(self.config.courses_dir, course, rel)
                if not folder.is_dir():
                    return self.send_error(404, "Složka nenalezena.")
                idx = folder / "index.html"
                html = render_index(idx, course, rel) if idx.is_file() else None
                files = list_folder(folder, course, rel)
                return self._send_json({"html": html, "files": files})

            if path.startswith("/files/"):
                rest = unquote(path[len("/files/"):])
                if not rest:
                    return self.send_error(404)
                course, _, rel = rest.partition("/")
                target = safe_resolve(self.config.courses_dir, course, rel)
                if not target.is_file():
                    return self.send_error(404)
                return self._serve_file(target)

            self.send_error(404)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            # Klient zavřel spojení (browser často zruší PDF GET a udělá Range);
            # nemá smysl posílat 500 do mrtvého socketu.
            return
        except PermissionError as e:
            self.send_error(403, str(e))
        except FileNotFoundError:
            self.send_error(404)
        except KeyError as e:
            self.send_error(400, f"Chybí parametr: {e}")
        except Exception as e:  # pragma: no cover
            self.log_error("Neočekávaná chyba: %r", e)
            try:
                self.send_error(500, str(e))
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                pass

    # --- helpers -------------------------------------------------------------

    @staticmethod
    def _first_qs(qs: dict[str, list[str]], key: str) -> str:
        values = qs.get(key)
        if not values:
            raise KeyError(key)
        return values[0]

    def _send_json(self, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static_file(self, p: Path) -> None:
        ctype, _ = mimetypes.guess_type(p.name)
        if ctype is None:
            ctype = "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        data = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _serve_file(self, p: Path) -> None:
        """Servíruje soubor z courses_dir s podporou Range pro PDF."""
        ctype, _ = mimetypes.guess_type(p.name)
        if ctype is None:
            ctype = "application/octet-stream"

        size = p.stat().st_size
        range_header = self.headers.get("Range")

        if range_header and range_header.startswith("bytes="):
            try:
                start_s, end_s = range_header[len("bytes="):].split("-", 1)
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else size - 1
                if start > end or end >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
            except ValueError:
                self.send_error(400, "Neplatný Range header.")
                return

            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(length))
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Accept-Ranges", "bytes")
            self.end_headers()
            with p.open("rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
            return

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        with p.open("rb") as f:
            while True:
                chunk = f.read(64 * 1024)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def log_message(self, fmt: str, *args) -> None:
        # Tichý logger — viewer není produkční server, jen výpis chyb stačí.
        sys.stderr.write("[viewer] " + (fmt % args) + "\n")


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _make_handler(cfg: Config):
    cls = type(
        "BoundViewerHandler",
        (ViewerHandler,),
        {"config": cfg},
    )
    return cls


def run(cfg: Config) -> None:
    handler_cls = _make_handler(cfg)
    with ThreadingHTTPServer((cfg.host, cfg.port), handler_cls) as httpd:
        host, port = httpd.server_address[:2]
        url = f"http://{host}:{port}/"
        print(f"[viewer] Běží na {url}")
        print(f"[viewer] Kurzy: {cfg.courses_dir}")
        print("[viewer] Ctrl+C pro ukončení.")
        if cfg.open_browser:
            threading.Timer(0.3, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[viewer] Ukončuji…")


def main() -> int:
    # Windows console (cp1252) neumí česká písmena v print() — vynutíme UTF-8.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass

    config_path = DEFAULT_CONFIG_PATH
    if len(sys.argv) > 1:
        config_path = Path(sys.argv[1]).resolve()
    try:
        cfg = load_config(config_path)
    except ConfigError as e:
        print(f"[viewer] CHYBA: {e}", file=sys.stderr)
        return 1
    run(cfg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
