# 11 UI Implementation Specification — PocketBase v0.40.6 Admin SPA

Machine-readable computed DOM & CSS token archive: `11_ui/tokens.json`. Visual baselines: `05_ui_reference.md` (`SCR-001`–`SCR-006`).

## 1. Architecture & Framework Discovery
Source inspection of `v0.40.6` (`ui/src/`) confirms the Admin UI is implemented as a lightweight custom vanilla-JavaScript reactive DOM runtime (`t.div`, `store`, hash router `#/collections`, `#/settings`) rather than Svelte `[REF: ui/src/auth/pageSuperuserLogin.js:1-86]`.

## 2. Source CSS Variables Paired With Live Computed Measurements (`1440x900@1x`)
Verified against both `ui/src/css/vars.css` and live `getComputedStyle(document.documentElement)` on `SCR-004` `[REF: ui/src/css/vars.css:1-120]`:

| Token | Source Code Value (`vars.css`) | Live Computed Value (`11_ui/tokens.json`) | Role |
|---|---|---|---|
| `--baseFontFamily` | `"IBM Plex Sans", system-ui, sans-serif, emoji` | `"IBM Plex Sans", system-ui, sans-serif, emoji` | Primary UI typeface |
| `--monospaceFontFamily` | `"IBM Plex Mono", ui-monospace, monospace, emoji` | `"IBM Plex Mono", ui-monospace, monospace, emoji` | IDs, filter bar, API Preview code |
| `--primaryColor` | `#25272d` | `#25272d` (`rgb(37, 39, 45)`) | Primary buttons & dark ink |
| `--secondaryColor` | `#e4e8ec` | `#e4e8ec` | Secondary surfaces & inputs |
| `--accentColor` | `#1055c9` | `#1055c9` | Active links & focus highlights |
| `--successColor` | `#22a96d` | `#22a96d` | Positive status badges & toasts |
| `--dangerColor` | `#c33751` | `#c33751` | Auth/validation error alerts (`SCR-002`) |
| `--surfaceColor` | `#fff` | `#fff` (`rgb(255, 255, 255)`) | Main canvas background |
| `--surfaceAlt1Color` | `#f8f9fa` | `#f8f9fa` | Sidebar & card surface |
| `--fontSize` / `--lineHeight` | `14px` / `22px` | `14px` / `22px` | Base body typography |
| `--btnHeight` / `--borderRadius` | `45px` / `5px` | `45px` / `5px` | Controls & rounded corners |
| `--spacing` | `30px` | `30px` | Main content grid padding |

## 3. Live Element Geometry Measurements (`SCR-004`)
- **Viewport / Body**: `1440 x 900px`, `font-size: 14px`, `color: rgb(37, 39, 45)`, `background-color: rgb(255, 255, 255)`.
- **Navigation / Sidebar Rail**: `269px` collection sidebar region paired with main data table canvas (`1200px` wide rows).
- **Data Table Row (`table tbody tr`)**: `1200 x 45px`, `14px` font, single-line ellipsis truncation for record columns (`SCR-004`).
- **Search / Filter Input**: `height: 49px`, `padding: 10px 5px 10px 15px`, `14px` font.
- **Modal / Overlay (`SCR-005`)**: Contextual slide-over / modal triggered by `API Preview` (`--modalAnimationSpeed: 200ms`, `--modalOverlayColor: rgba(70, 90, 115, 0.25)`) `[REF: ui/src/apiPreview/apiPreviewModal.js:1-60]`.

## 4. Clean-Room Asset & Branding Rule
Reimplementations must replicate layout geometry, state feedback (`normal`, `empty`, `error`, `modal`), and color contrast ratios without copying PocketBase logo assets or trademarked brand strings (`04_environment/LICENSING.md`).

## Sources Read
- `ui/src/css/vars.css`
- `ui/src/auth/pageSuperuserLogin.js`
- `ui/src/apiPreview/apiPreviewModal.js`
- `05_ui/screens.json`
- `11_ui/tokens.json`
