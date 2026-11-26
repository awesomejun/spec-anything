# Deterministic Static Fact Sheet

Generated mechanically by `scripts/source_map.py`. LLM synthesis must remain grounded in these facts and live runtime observations.

## Coverage Statistics
- Total files scanned: `1116`
- Supported code files: `621` (test files: `95`)
- Languages: `{"css": 3, "html": 2, "javascript": 27, "scss": 76, "typescript": 513}`
- Extracted inventory: `7` modules, `1431` entities, `6` actions/routes, `0` SQL tables, `0` frontend routes, `373` CSS variables, `139` dependencies

## 1. Modules
| Module | Files | Lines | Languages |
|---|---:|---:|---|
| `.` | 2 | 138 | javascript, typescript |
| `dev-docs` | 13 | 1927 | css, javascript, scss, typescript |
| `examples` | 16 | 2573 | html, javascript, scss, typescript |
| `excalidraw-app` | 43 | 6944 | html, javascript, scss, typescript |
| `packages` | 531 | 131993 | css, scss, typescript |
| `public` | 1 | 21 | javascript |
| `scripts` | 15 | 1248 | javascript |

## 2. HTTP Routes & CLI Commands (Sample Top 80)
| Role | Method | Target | Ref |
|---|---|---|---|
| `frontend_api_call` | `CLIENT` | `${
                import.meta.env.VITE_APP_AI_BACKEND
              }/v1/ai/text-to-diagram/generate` | `[REF: excalidraw-app/components/AI.tsx:103]` |
| `frontend_api_call` | `CLIENT` | `${
              import.meta.env.VITE_APP_AI_BACKEND
            }/v1/ai/diagram-to-code/generate` | `[REF: excalidraw-app/components/AI.tsx:39]` |
| `frontend_api_call` | `CLIENT` | `${BACKEND_V2_GET}${id}` | `[REF: excalidraw-app/data/index.ts:204]` |
| `frontend_api_call` | `CLIENT` | `${import.meta.env.VITE_APP_LIBRARY_BACKEND}/submit` | `[REF: packages/excalidraw/components/PublishLibrary.tsx:300]` |
| `frontend_api_call` | `CLIENT` | `${url}?alt=media` | `[REF: excalidraw-app/data/firebase.ts:282]` |
| `frontend_api_call` | `CLIENT` | `/images/rocket.jpeg` | `[REF: examples/with-script-in-browser/components/ExampleApp.tsx:140]` |

## 3. Frontend Routes
| Route | Component | Ref |
|---|---|---|

## 4. SQL Tables Detected in Migrations/Code
| Table | Ref |
|---|---|
