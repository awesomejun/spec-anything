# 11 UI Implementation & Design Tokens — Pomotroid v1.7.1

Measured tokens file: `11_ui/tokens.json` (captured live from compiled upstream Svelte 5 DOM at `360×478@2x`).

## 1. Measured Geometry & Typography
- **Main Window**: `360×478 px`, Titlebar `40 px`, Compact Watch threshold `< 300 px` [REF: src/routes/+page.svelte:23-55].
- **Circular Dial**: `220×220 px` (`viewBox="0 0 230 230"`), track `stroke-width: 2`, progress arc `stroke-width: 10`, `stroke-linecap: round`, circumference `691.15` (`2π × 110`) [REF: src/lib/components/TimerDial.svelte:16-72].
- **Countdown Text**: `44.8 px` (`2.8rem`), `font-weight: 300`, centered over dial [REF: src/lib/components/TimerDisplay.svelte:22-39].
- **Controls Grid**: 3-column grid (`Restart 32×32`, `Play/Pause 48×48 circle`, `Skip 32×32`; row 2 `1 | 4`, `Reset`, `Volume`).

## 2. Default Theme Palette (`Pomotroid` Dark vs `Pomotroid Light`)
- Dark: `--color-background: #2f384b`, `--color-background-light: #3d4457`, `--color-foreground: #f6f2eb`, `--color-focus-round: #ff4e4d`, `--color-short-round: #05ec8c`, `--color-long-round: #0bbddb` [REF: static/themes/pomotroid.json:1-15].
- Light: `--color-background: #f5f0e8`, `--color-foreground: #2f384b`, `--color-focus-round: #c84840`, `--color-short-round: #3a7d58`, `--color-long-round: #6aaec4`.

## Sources Read
- `src/routes/+page.svelte`
- `src/lib/components/TimerDial.svelte`
- `src/lib/components/TimerDisplay.svelte`
- `static/themes/pomotroid.json`
