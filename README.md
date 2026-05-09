# Blackboard Backup Viewer

A local viewer for courses downloaded with [`blackboard-grabber`](../blackboard-grabber).
Run a single command and browse your course content from disk in your web browser.

## Install — binary (recommended)

No Python or other tooling required. Just grab the prebuilt bundle.

1. Open the [GitHub Releases](https://github.com/JarousNemec/blackboard-backup-viewer/releases)
   page and download the archive for your platform:
   - Windows: `bb-viewer-windows-x64-vX.Y.Z.zip`
   - Linux: `bb-viewer-linux-x64-vX.Y.Z.tar.gz`
2. Extract it anywhere on disk.
3. In the folder next to the binary, copy `config.example.toml` to `config.toml`
   and set `courses_dir` to the directory that contains your courses as subfolders
   (typically `output/` from blackboard-grabber).
4. Run the binary:
   - Windows: double-click `bb-viewer.exe` (or run it from a terminal)
   - Linux: `./bb-viewer`

Your browser opens at the URL printed to the console
(e.g. `http://127.0.0.1:54321/`). Press `Ctrl+C` to stop the server.

## How to use it

- **Left pane** — list of courses and the folder tree.
- **Right pane** — clicking a folder shows the page text and a list of files.
- **PDFs** open in a new tab; **other files** (`.pkt`, …) are offered as a download.

## Run from Python (alternative, for developers)

Use this path if you want to hack on the source or prefer not to download the
binary. **Requires Python 3.11+.**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .

copy config.example.toml config.toml   # edit courses_dir
python launcher.py
```

## Optional

Pass a custom config path (works for both the binary and the Python entry point):

```powershell
bb-viewer.exe C:\other\config.toml
python launcher.py C:\other\config.toml
```

Other options (host, port, auto-open browser) are documented inline in
`config.example.toml`.

## Security

The server listens on `127.0.0.1` only, and every URL path is checked against
path traversal (`..` outside `courses_dir` is rejected).
