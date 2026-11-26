# Licensing & Clean-Room Asset Separation

## Upstream Source License
- **Repository**: `https://github.com/excalidraw/excalidraw`
- **Tag / Pinned Commit**: `v0.18.1` (`a2ec2889babf7d2295469c6d90ebe77fae57df84`)
- **Official npm Package**: `@excalidraw/excalidraw@0.18.1`
- **Code License**: MIT License (`LICENSE` at repository root).

## Asset, Font, and Brand Separation Policy
- **Brand & Trademarks**: The "Excalidraw" name, logo marks, and promotional UI assets belong to Excalidraw and are **NOT** copied or redistributed in `cleanroom-reimpl/`.
- **Bundled Fonts**: The official tarball bundles third-party font files (`Excalifont`, `Virgil`, `Cascadia`, `Nunito`, `ComicShanns`, `Liberation`, `Lilita`, `Assistant`, `Xiaolai`) under their respective font licenses (SIL OFL / Apache / MIT). The clean-room reimplementation uses standard system/generic font stacks and does not copy any `.woff2` binary font files from upstream.
- **Clean-Room Code Provenance**: All files under `cleanroom-reimpl/` (`index.html`, `styles.css`, `app.js`, `server.py`) are authored from scratch using only the specification contracts (`09_contracts/`), observed behavior ledger (`06_evidence/ledger.jsonl`), and extracted CSS design tokens (`11_ui/tokens.json`), branded distinctly as **SketchBoard CR**.
- **Screenshots (`05_ui/screenshots/`)**: Captured purely as behavioral reference evidence of the live open-source MIT software for differential parity testing (`07_tests/verify_parity.py`).
