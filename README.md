# Blackboard Backup Viewer

Lokální prohlížeč kurzů stažených nástrojem [`blackboard-grabber`](../blackboard-grabber).

UI je obyčejné HTML/CSS/JS běžící v prohlížeči, servírované malým Python HTTP serverem,
který zároveň poskytuje JSON API a servíruje samotné soubory kurzu.

## Co viewer umí

- V levém sloupci ukáže seznam kurzů z konfigurované složky.
- Po kliknutí na kurz rozbalí strom složek (= „stránek" kurzu).
- Po kliknutí na složku zobrazí vpravo:
  - textový obsah stránky (`index.html` renderovaný inline),
  - seznam souborů (PDF, .pkt, …) jako odkazy.
- Klik na PDF → otevře se v novém tabu prohlížeče (PDF viewer prohlížeče).
- Klik na ostatní soubory (.pkt apod.) → prohlížeč nabídne stažení.

## Instalace

Vyžaduje Python 3.11+.

```powershell
cd C:\Users\mortar\AI_Projects\blackboard-backup-viewer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

## Konfigurace

```powershell
copy config.example.toml config.toml
```

V `config.toml` nastav `[paths] courses_dir` na cestu k adresáři kurzů
(typicky `output/` z blackboard-grabberu).

## Spuštění

```powershell
python launcher.py
```

Server vypíše URL (např. `http://127.0.0.1:54321/`) a otevře prohlížeč.
Pro ukončení stiskni `Ctrl+C`.

Volitelně lze předat vlastní cestu ke configu:

```powershell
python launcher.py C:\jine\config.toml
```

## Struktura projektu

```
blackboard-backup-viewer/
├── launcher.py              # entry point
├── config.example.toml      # šablona configu
├── bb_viewer/
│   ├── config.py            # načtení config.toml
│   ├── paths.py             # bezpečné cesty + výpis stromu/souborů
│   ├── html_rewrite.py      # parse index.html, přepis relativních URL
│   └── server.py            # HTTP server + main()
└── static/
    ├── index.html
    ├── app.js
    └── style.css
```

## Bezpečnost

Server poslouchá defaultně jen na `127.0.0.1`. Všechny cesty z URL projdou
`safe_resolve`, který odmítá `..` a kontroluje, že výsledná cesta zůstává
v `courses_dir` (ochrana proti path traversal).
