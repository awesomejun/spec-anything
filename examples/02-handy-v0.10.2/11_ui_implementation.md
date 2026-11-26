# 11 — UI Implementation & Measured Design Tokens (`cjpais/Handy v0.10.2`)

## 1. Live Computed Design Tokens (`11_ui/tokens.json`)
Measured directly via `getComputedStyle(document.documentElement)` on the live upstream Vite app at `1024x700@1x` in light theme `[REF: src/styles/theme.css:12-166]` `[REF: src/App.css:176-215]` `[REF: 11_ui/tokens.json:1-127]`:

| Token | Measured Light Value | Role |
|---|---|---|
| `--color-background` | `#fbfbfb` | Primary window & card surface |
| `--color-text` | `#0f0f0f` | Primary foreground copy |
| `--color-logo-primary` | `#faa2ca` | Sidebar active pill (`80%` alpha), starred icon highlight |
| `--color-background-ui` | `#da5893` | Active toggle switch fill, active model checkmark circle, volume bar fill |
| `--color-moss` | `#2f7d5b` | Footer model-ready status dot |
| `--color-plum` | `#382731` | Wordmark outline / keycap ink |
| `--color-ink-2` | `color-mix(in srgb, #0f0f0f 60%, transparent)` | Secondary text & footer copy |
| `--color-ink-3` | `#808080` | Section headings (`11.25px` uppercase), icon buttons, descriptions |
| `--color-line` | `color-mix(in srgb, #808080 20%, transparent)` | 1 px dividers, sidebar border, card borders |
| `--color-wash` | `color-mix(in srgb, #808080 10%, transparent)` | Hover fills & subtle input backgrounds |
| Root Typography | `15px / 24px`, `ui-sans-serif, system-ui, sans-serif` | Base scale (`1rem = 15px`, making `w-40 = 150px`, `max-w-3xl = 720px`) |

## 2. Measured Shell Geometry
- **Desktop Viewport**: `1024 x 700 px` (`1x`)
- **Left Sidebar (`Sidebar.tsx`)**: Fixed `150 px` width, `1px solid var(--color-line)` right border, `7.5px` horizontal padding; active navigation item `134 x 39 px`, `7.5px` radius, `rgba(250, 162, 202, 0.8)` fill `[REF: src/components/Sidebar.tsx:95-124]`.
- **Main Scroll Column (`App.tsx`)**: Flexible width, centered `max-width: 720px` content container with `15px` outer padding and `22.5px` vertical group spacing `[REF: src/App.tsx:328-351]`.
- **SettingsGroup Card**: `720px` wide, `1px solid var(--color-line)` border, `7.5px` border radius, `45px` minimum row height separated by hairline horizontal dividers `[REF: src/components/ui/SettingsGroup.tsx:9-31]`.
- **Fixed Footer (`Footer.tsx`)**: `1024 x 39 px`, `1px solid var(--color-line)` top border, model status switcher on the left and update status + version string on the right `[REF: src/components/footer/Footer.tsx:30-50]`.

## 3. Clean-Room Brand & Asset Separation
To comply with `04_environment/LICENSING.md`, `cleanroom-reimpl/app.py` replaces the upstream pink hand mascot and `HandyTextLogo` SVG with an original **`handy [CR]`** badge and minimal inline geometric SVG icons while preserving exact measured geometry and design tokens (`1.67%`–`3.17%` RGB MAE across `SCR-001`–`SCR-003`).

## Sources Read
- `src/styles/theme.css` (`1-244`)
- `src/App.css` (`1-272`)
- `src/App.tsx` (`318-365`)
- `src/components/Sidebar.tsx` (`1-126`)
- `src/components/footer/Footer.tsx` (`1-53`)
- `src/components/ui/SettingsGroup.tsx` (`1-31`)
- `11_ui/tokens.json`
- `04_environment/LICENSING.md`
