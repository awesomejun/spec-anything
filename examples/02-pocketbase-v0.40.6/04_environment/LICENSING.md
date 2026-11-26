# Licensing & Asset Redistribution Boundaries (`pocketbase/pocketbase v0.40.6`)

## 1. Upstream Source Code License
- **Repository**: `https://github.com/pocketbase/pocketbase`
- **Pinned Tag / Commit**: `v0.40.6` (`9d281ccaba65f2686eb7b0b614ccda72d1116a1b`)
- **License**: **MIT License** (`LICENSE.md`, Copyright (c) 2022 - present, Gani)
- **Clean-Room Reimplementation Note**: Code algorithms, REST/SSE wire contracts, SQLite schemas, and behavioral specifications derived from MIT-licensed source and live observation may be freely used for independent reimplementation provided MIT attribution is preserved if any verbatim upstream code is reused.

## 2. UI Assets, Fonts & Brand Trademarks (Separated From Code License)
- **Brand Name & Logo**: "PocketBase" brand marks and SVG logo assets under `ui/public/` / `ui/src/` must **NOT** be redistributed as your own product branding in a clean-room reimplementation. Replace product name, favicon, and brand graphics.
- **Bundled Fonts & Icon Sets**: `ui/src/css/vars.css` references `"IBM Plex Sans"` (`SIL Open Font License 1.1`) and icon fonts/libraries listed in `ui/package.json` (e.g., Remix Icon / CodeMirror / Leaflet). Verify each third-party font/icon license independently before bundling into a clean-room UI.
- **Screenshots (`05_ui/screenshots/*.png`)**: Captured strictly as visual reference baselines of the MIT-licensed upstream Admin UI for differential testing (`07_tests/verify_visual.py`). Do not ship upstream UI screenshots as product assets.

## 3. Third-Party Go & JS Dependencies
- Official binary embeds 36 Go module dependencies (`go version -m` recorded in `04_environment/release_audit.json`), including pure-Go SQLite (`modernc.org/sqlite`), `github.com/golang-jwt/jwt/v5`, `github.com/ganigeorgiev/fexpr`, and `github.com/dop251/goja`. Review upstream notices when mirroring behavior.
