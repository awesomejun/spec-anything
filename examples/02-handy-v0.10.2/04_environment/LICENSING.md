# Licensing & Asset Redistribution Boundaries (`cjpais/Handy v0.10.2`)

## 1. Upstream Source Code License
- **Repository**: `https://github.com/cjpais/Handy`
- **Pinned Tag / Commit**: `v0.10.2` (`a822741f9c697b6f6a00c557e4817bf59ae70867`)
- **License**: **MIT License** (`LICENSE`, Copyright (c) 2025 CJ Pais)
- **Clean-Room Reimplementation Boundary**: Functional specifications, Tauri IPC schemas, SQLite DDL, state machine transitions, and behavioral tests derived from MIT-licensed source and isolated runtime observations may be used to build an independent clean-room reimplementation. No verbatim upstream source files are copied into `cleanroom-reimpl/`.

## 2. UI Assets, Brand Marks, Audio & Fonts (Separated From Code License)
- **Brand Name, Wordmark & Mascot**: The "Handy" name, pink hand mascot (`HandyHand`, `HandyTextLogo`), `icon.icns`, and tray icons (`Contents/Resources/resources/tray_*.png`, `handy.png`) MUST NOT be redistributed as third-party product branding. The clean-room reimplementation uses a distinct brand mark (**`Handy CR`**) and original minimal geometric iconography.
- **Audio Feedback Samples**: Bundled WAV chimes (`marimba_start.wav`, `marimba_stop.wav`, `pop_start.wav`, `pop_stop.wav`) in `src-tauri/resources/` are excluded from clean-room redistribution.
- **Bundled Fonts & Icons**: Upstream UI uses `lucide-react` (ISC License) and a subsetted Noto Sans CJK font (`src/assets/fonts/cjk-subset.woff2`, SIL Open Font License 1.1) plus system UI stacks (`SF Pro Rounded` / `system-ui`). Clean-room UI relies solely on system fonts and original inline SVG icons.
- **Reference Screenshots (`05_ui/screenshots/*.png`)**: Captured strictly as live upstream UI reference baselines for differential visual verification (`07_tests/verify_parity.py`). Do not distribute as end-user application assets.

## 3. Third-Party Native & ML Model Dependencies
- **Inference & VAD**: Upstream integrates `transcribe.cpp` (`0.4.0`), Metal/Vulkan/CPU backends, Silero/Earshot VAD, and downloadable GGUF ASR models from Hugging Face Hub / `blob.handy.computer` (each model carries its own upstream weights license such as MIT, Apache-2.0, or CC-BY-4.0).
- **Deterministic Test Double**: Runtime tests and the clean-room reimplementation stub local acoustic inference deterministically without bundling external GGUF weights.
