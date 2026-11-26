# 04 — Reproduction Environment & Official Release REA Audit

## 1. Upstream Source Pin
- **Repository**: `https://github.com/excalidraw/excalidraw`
- **Release Tag**: `v0.18.1`
- **Pinned Commit SHA**: `a2ec2889babf7d2295469c6d90ebe77fae57df84`
- **License**: MIT (see `04_environment/LICENSING.md` for code vs. brand/font separation)

## 2. Official npm Distribution REA Audit (`04_environment/release_audit.json`)
- **Published Package**: `@excalidraw/excalidraw@0.18.1`
- **Registry Tarball**: `https://registry.npmjs.org/@excalidraw/excalidraw/-/excalidraw-0.18.1.tgz` (`31,234,066` bytes)
- **Tarball SHA-256**: `b280d4b364b65cba264c5aa4e7435cc2ce6421eabbbef9765a56997a0fadf534`
- **npm `dist.integrity` (SHA-512)**: `sha512-6i5Gt7IDTOH//qa0Z315Ly5iVRhjWpu2whrlQFqkuwrkKUWgRsMk0P5qdE7bpyDpai7jeLeWYkyj1eVAfni1lw==` — **VERIFIED MATCH (`true`)**
- **npm `dist.shasum` (SHA-1)**: `fd6ad752807c814698c5f51dab778845b7e4bba7` — **VERIFIED MATCH (`true`)**

### Inspected Production Bundle Artifacts (`package/dist/prod/`)
| Archive Path | Size (bytes) | SHA-256 | Role |
| :--- | ---: | :--- | :--- |
| `package/dist/prod/index.js` | `502,077` | `7f651063487849c79a8cdedc3aa6bd04c6b0c717ee63959116f1f12dbc0a51b8` | Primary ESM entry (`65` named exports) |
| `package/dist/prod/index.css` | `144,689` | `e72092760bae272ebe075bdadaff7f82909d318c5d819313185b19e99be31e49` | Compiled theme & component stylesheet |
| `package/dist/prod/chunk-EIO257PC.js` | `1,824,966` | `6ca0a6b4a49be83ed6beb32f845648ca4927c592cc0f4ba43a909624f5659493` | Core editor & canvas rendering split chunk |
| `package/dist/prod/chunk-K2UTITRG.js` | `439,257` | `72b54e8e9b3c17c69f1dd5e40203bfaed62313bc611b86ecb8a1625a12562e51` | Secondary shared runtime chunk |
| `package/dist/prod/chunk-6U3AYISY.js` | `22,458` | `1c4b2bfaa35552f6bf0bbe22af9ca7b3477f466d6ac29af7febbfbd2a0b387fb` | Auxiliary feature chunk |

Additional bundled resources verified inside `dist/prod/`: `9` font families (`Assistant`, `Cascadia`, `ComicShanns`, `Excalifont`, `Liberation`, `Lilita`, `Nunito`, `Virgil`, `Xiaolai`) and `55` locale JSON bundles.

## 3. Source-vs-Distribution REA Findings
1. **REA-001 (Monorepo Scoping)**: The GitHub source tree includes `excalidraw-app/`, `packages/excalidraw/`, `packages/math/`, `packages/utils/`, `firebase-project/`, and `dev-docs/`. The official npm package ships only the `esbuild 0.19.10` compiled ESM output of `packages/excalidraw/` with `@excalidraw/math` and `@excalidraw/utils` bundled in and third-party libraries kept external.
2. **REA-002 (Host-Owned localStorage Persistence)**: Browser `localStorage` persistence (`"excalidraw"` and `"excalidraw-state"`) is implemented in `excalidraw-app/data/localStorage.ts` and is **not** automatically wired inside `<Excalidraw />` from `dist/prod/index.js`. Reproducing `F-011` requires host wiring via `onChange` and `initialData`.
3. **REA-003 (Dual Dev/Prod Export Conditions)**: `package.json` routes `development` imports to `dist/dev/*` (with sourcemaps) and `production`/`default` imports to minified `dist/prod/*` (without sourcemaps).

## 4. Isolated Runtime Execution Environment
- **Host OS / Architecture**: macOS arm64
- **Upstream Harness Stack**: `@excalidraw/excalidraw@0.18.1` + `react@18.3.1` + `react-dom@18.3.1` + `vite@5.4.11` (`vite preview` serving the production build on `http://127.0.0.1:4173/`)
- **Clean-Room Runtime Stack**: Zero-dependency static HTML/CSS/JS served via Python 3.13 stdlib (`cleanroom-reimpl/server.py` on `http://127.0.0.1:4183/`)
- **Browser Automation & Verification**: Playwright Python + Headless Chromium (`1280x800`, `device_scale_factor = 1`), Pillow (`PIL`) for RGB pixel-diff MAE heatmaps, `jsonschema` Draft 2020-12 validator.
- **Deterministic Test Inputs**:
  - Rectangle drag: `(260, 180) -> (480, 320)`
  - Ellipse drag: `(700, 180) -> (900, 320)`
  - Bound Arrow drag: `(482, 250) -> (696, 250)`
  - Text click & type: `(440, 420)`, `"Excalidraw Parity Spec"`, commit `Escape`
  - Property mutations on Rectangle: `strokeColor = "#e03131"`, `backgroundColor = "#a5d8ff"`, `roughness = 2`
  - Undo/Redo probe Diamond drag: `(960, 420) -> (1080, 520)`
