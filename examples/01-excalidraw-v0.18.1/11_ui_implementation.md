# 11 — UI Design Tokens & Layout Implementation Specification

Canonical extracted token artifact: `11_ui/tokens.json` (captured via live Chromium `getComputedStyle` against `@excalidraw/excalidraw@0.18.1` at `1280x800`, `DPR=1`).

## 1. Core Theme CSS Custom Properties (`Light` vs `Dark`)
Measured directly from `.excalidraw` (light) and `.excalidraw.theme--dark` (dark) [REF: packages/excalidraw/css/theme.scss:4-268]:

| Token | Light Theme Value | Dark Theme Value | Usage |
| :--- | :--- | :--- | :--- |
| `--default-bg-color` | `#ffffff` | `#121212` | Viewport / canvas backdrop |
| `--island-bg-color` | `#ffffff` | `#232329` | Floating toolbar & properties inspector surfaces |
| `--color-surface-low` | `#ececf4` | `hsl(240, 8%, 15%)` (`rgb(35, 35, 41)`) | Corner buttons, zoom & undo/redo groups |
| `--color-surface-high` | `#f1f0ff` | `hsl(245, 10%, 21%)` | Button hover background |
| `--color-on-surface` | `#1b1b1f` | `#e3e3e8` | Primary icon and label foreground |
| `--color-primary` | `#6965db` | `#a8a5ff` | Brand accent & selection indicator |
| `--color-surface-primary-container` | `#e0dfff` | `#403e6a` | Active toolbar tool fill |
| `--color-on-primary-container` | `#030064` | `#e0dfff` | Active toolbar icon foreground |
| `--keybinding-color` | `#b8b8b8` | `#7a7a7a` | Shortcut numeral hints & helper caption |
| `--theme-filter` | `none` | `invert(93%) hue-rotate(180deg)` | Non-destructive dark-mode canvas filter [REF: packages/excalidraw/constants.ts:271-272] |
| `--border-radius-lg` | `0.5rem` (`8px`) | `0.5rem` (`8px`) | Island and button corner radius |
| `--shadow-island` | `0 0 0.93px rgba(0,0,0,.17), 0 0 3.13px rgba(0,0,0,.08), 0 7px 14px rgba(0,0,0,.05)` | Identical elevation shadow | Floating toolbar & inspector elevation |

## 2. Measured Chrome Bounding Geometry (`1280x800`)
| UI Component | Measured Rect (`x, y, w x h`) | Border Radius | Light BG | Dark BG |
| :--- | :--- | :--- | :--- | :--- |
| Canvas (`canvas.excalidraw__canvas`) | `0, 0, 1280 x 800` | `0px` | `#ffffff` (painted) | `#121212` (filtered) |
| Top-left Menu Trigger | `16, 16, 36 x 36` | `8px` | `rgb(236, 236, 244)` | `rgb(35, 35, 41)` |
| Top-center Floating Toolbar | `365, 16, 550 x 44` | `8px` | `rgb(255, 255, 255)` | `rgb(35, 35, 41)` |
| Hint Caption (`.HintViewer`) | `365, 68, 550 x 23` | `0px` | `transparent` | `transparent` |
| Top-right Action Pill | `1182, 16, 82 x 36` | `8px` | `rgb(236, 236, 244)` | `rgb(35, 35, 41)` |
| Left Properties Inspector | `16, 76, 200 x 634` | `8px` | `rgb(255, 255, 255)` | `rgb(35, 35, 41)` |
| Bottom-left Zoom Bar | `16, 748, 132 x 36` | `8px` | `rgb(236, 236, 244)` | `rgb(35, 35, 41)` |
| Bottom-left Undo/Redo Group | `158, 748, 72 x 36` | `8px` | `rgb(236, 236, 244)` | `rgb(35, 35, 41)` |
| Bottom-right Help Button | `1228, 748, 36 x 36` | `8px` | `rgb(236, 236, 244)` | `rgb(35, 35, 41)` |

## 3. Quick-Pick Element Color Swatches
Extracted from `packages/excalidraw/colors.ts` [REF: packages/excalidraw/colors.ts:88-117]:
- **Stroke quick picks**: `#1e1e1e`, `#e03131`, `#2f9e44`, `#1971c2`, `#f08c00`
- **Background quick picks**: `transparent`, `#ffc9c9`, `#b2f2bb`, `#a5d8ff`, `#ffec99`
- **Canvas background picks**: `#ffffff`, `#f8f9fa`, `#f5faff`, `#fffce8`, `#fdf8f6`

## 4. Clean-Room Styling & Asset Policy
`cleanroom-reimpl/styles.css` implements these exact numeric dimensions and CSS variables using system sans-serif UI fonts and generic cursive/handwritten fallback stacks for canvas text without redistributing any upstream `.woff2` font files or brand icons [REF: packages/excalidraw/constants.ts:130-140].

## Sources Read
- `packages/excalidraw/css/theme.scss` (lines 1-268)
- `packages/excalidraw/colors.ts` (lines 51-170)
- `packages/excalidraw/constants.ts` (lines 130-183, 271-272)
- `11_ui/tokens.json` (live Chromium `getComputedStyle` extraction)
