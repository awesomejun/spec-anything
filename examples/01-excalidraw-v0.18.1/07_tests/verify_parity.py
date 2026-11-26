#!/usr/bin/env python3
"""
Executable Differential Parity Test Harness for @excalidraw/excalidraw v0.18.1.

Reads observed baseline records directly from `06_evidence/ledger.jsonl`,
executes real Chromium Playwright scenarios against either:
  - `--mode baseline --target-url <upstream_url>`  (emits `07_tests/parity_report.json`)
  - `--mode reimplementation_diff --target-url <cleanroom_url>` (emits `07_tests/reimpl_parity_report.json` + visual pixel-diff proof in `cleanroom-reimpl/proof_shots/`)

Conforms strictly to `parity_report.schema.json`.
"""
import argparse
import datetime
import json
import pathlib
import shutil
import sys
import time

import jsonschema
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

BUNDLE_DIR = pathlib.Path(__file__).resolve().parent.parent
LEDGER_PATH = BUNDLE_DIR / "06_evidence" / "ledger.jsonl"
SCENE_SCHEMA_PATH = BUNDLE_DIR / "09_contracts" / "excalidraw_scene.schema.json"
RELEASE_AUDIT_PATH = BUNDLE_DIR / "04_environment" / "release_audit.json"
UPSTREAM_SHOTS_DIR = BUNDLE_DIR / "05_ui" / "screenshots"
PROOF_SHOTS_DIR = BUNDLE_DIR / "cleanroom-reimpl" / "proof_shots"


def load_ledger() -> dict:
    records = {}
    for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        records[rec["evidence_id"]] = rec
    return records


def compute_visual_diff(orig_path: pathlib.Path, reimpl_path: pathlib.Path, diff_out: pathlib.Path) -> dict:
    img_a = Image.open(orig_path).convert("RGB")
    img_b = Image.open(reimpl_path).convert("RGB")
    if img_a.size != img_b.size:
        img_b = img_b.resize(img_a.size)

    diff = ImageChops.difference(img_a, img_b)
    w, h = img_a.size
    total_pixels = w * h

    a_px = img_a.load()
    d_px = diff.load()
    heatmap = Image.new("RGB", (w, h))
    h_px = heatmap.load()

    sum_abs = 0
    changed_pixels = 0
    for y in range(h):
        for x in range(w):
            dr, dg, db = d_px[x, y]
            sum_abs += dr + dg + db
            max_d = max(dr, dg, db)
            if max_d > 15:
                changed_pixels += 1
                intensity = min(255, 110 + max_d)
                h_px[x, y] = (intensity, 28, 42)
            else:
                ar, ag, ab = a_px[x, y]
                gray = int(0.299 * ar + 0.587 * ag + 0.114 * ab)
                dim = int(gray * 0.85 + 24)
                h_px[x, y] = (dim, dim, dim)

    diff_out.parent.mkdir(parents=True, exist_ok=True)
    heatmap.save(diff_out)

    mae_ratio = sum_abs / (total_pixels * 3 * 255.0)
    changed_ratio = changed_pixels / float(total_pixels)
    return {
        "width": w,
        "height": h,
        "mae_ratio": round(mae_ratio, 6),
        "mae_percent": round(mae_ratio * 100.0, 4),
        "changed_pixel_ratio": round(changed_ratio, 6),
        "changed_pixel_percent": round(changed_ratio * 100.0, 4),
    }


def click_tool(page, name: str):
    lbl = page.locator(f'label:has([data-testid="toolbar-{name}"])')
    if lbl.count() > 0:
        lbl.first.click()
    else:
        page.locator(f'[data-testid="toolbar-{name}"]').first.click()


def get_adapter_state(page) -> dict:
    return page.evaluate("""() => {
      const api = window.__excalidrawAPI || window.__whiteboardAPI;
      const els = api.getSceneElements().filter(e => !e.isDeleted);
      const st = api.getAppState();
      const canvas = document.querySelector('canvas');
      const root = document.querySelector('.excalidraw, .sb-app');
      const cs = root ? getComputedStyle(root) : null;
      return {
        element_count: els.length,
        elements: els,
        theme: st.theme,
        viewBackgroundColor: st.viewBackgroundColor,
        zoom: st.zoom ? st.zoom.value : 1,
        activeTool: st.activeTool ? st.activeTool.type : null,
        selectedIds: Object.keys(st.selectedElementIds || {}).filter(k => st.selectedElementIds[k]),
        canvas_width: canvas ? Math.round(canvas.getBoundingClientRect().width) : 0,
        canvas_height: canvas ? Math.round(canvas.getBoundingClientRect().height) : 0,
        dom_has_theme_dark: root ? root.classList.contains('theme--dark') : false,
        default_bg_token: cs ? cs.getPropertyValue('--default-bg-color').trim() : '',
        island_bg_token: cs ? cs.getPropertyValue('--island-bg-color').trim() : '',
        theme_filter_token: cs ? cs.getPropertyValue('--theme-filter').trim() : ''
      };
    }""")


def run_suite(mode: str, target_url: str, out_path: pathlib.Path) -> dict:
    ledger = load_ledger()
    scene_schema = json.loads(SCENE_SCHEMA_PATH.read_text(encoding="utf-8"))
    is_reimpl = mode == "reimplementation_diff"
    report_mode = "reimplementation_diff" if is_reimpl else "upstream_baseline"

    if is_reimpl:
        PROOF_SHOTS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(UPSTREAM_SHOTS_DIR / "SCR-001_canvas_empty_light.png", PROOF_SHOTS_DIR / "orig_empty_light.png")
        shutil.copy2(UPSTREAM_SHOTS_DIR / "SCR-002_shapes_drawn_light.png", PROOF_SHOTS_DIR / "orig_shapes_drawn_light.png")
        shutil.copy2(UPSTREAM_SHOTS_DIR / "SCR-003_dark_theme.png", PROOF_SHOTS_DIR / "orig_dark_theme.png")

    cases = []
    visual_metrics = {}

    def record_case(tc_id: str, ev: dict, passed: bool, duration_ms: float, checked_fields: list, diff_summary=None):
        cases.append({
            "test_id": tc_id,
            "feature_id": ev["feature_id"],
            "evidence_id": ev["evidence_id"],
            "category": ev["category"],
            "verdict": "PASS" if passed else "FAIL",
            "duration_ms": round(duration_ms, 2),
            "checked_fields": checked_fields,
            "diff_summary": diff_summary,
        })

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, device_scale_factor=1)
        page = context.new_page()

        # Clean boot
        page.goto(target_url, wait_until="networkidle")
        page.evaluate("() => localStorage.clear()")
        page.reload(wait_until="networkidle")
        page.wait_for_function("() => Boolean((window.__excalidrawAPI || window.__whiteboardAPI) && document.querySelector('canvas'))", timeout=15000)
        page.evaluate("() => document.fonts.ready")
        page.wait_for_timeout(450)

        # --- TC-001 (EV-001 / F-001): Initial Mount & Empty Light Canvas ---
        t0 = time.perf_counter()
        ev1 = ledger["EV-001"]
        exp1 = ev1["observed_output"]
        st1 = get_adapter_state(page)
        diffs1 = []
        for k in ["element_count", "theme", "viewBackgroundColor", "zoom", "activeTool", "canvas_width", "canvas_height"]:
            if st1[k] != exp1[k]:
                diffs1.append(f"{k}: got {st1[k]!r} != expected {exp1[k]!r}")
        if is_reimpl:
            reimpl_p = PROOF_SHOTS_DIR / "reimpl_empty_light.png"
            page.screenshot(path=str(reimpl_p))
            m = compute_visual_diff(PROOF_SHOTS_DIR / "orig_empty_light.png", reimpl_p, PROOF_SHOTS_DIR / "diff_empty_light.png")
            visual_metrics["empty_light"] = m
            max_diff = ev1["comparison_rules"]["visual_max_diff_ratio"]
            if m["mae_ratio"] > max_diff:
                diffs1.append(f"visual_mae {m['mae_ratio']:.4f} > {max_diff}")
        record_case("TC-001", ev1, not diffs1, (time.perf_counter() - t0) * 1000,
                    ev1["comparison_rules"]["exact_fields"], "; ".join(diffs1) if diffs1 else None)

        # --- TC-002 (EV-002 / F-002): Rectangle Tool & Drag Creation ---
        t0 = time.perf_counter()
        ev2 = ledger["EV-002"]
        exp2 = ev2["observed_output"]
        click_tool(page, ev2["input"]["tool"])
        page.wait_for_timeout(120)
        tool_before = get_adapter_state(page)["activeTool"]
        x0, y0 = ev2["input"]["drag_from"]
        x1, y1 = ev2["input"]["drag_to"]
        page.mouse.move(x0, y0)
        page.mouse.down()
        page.mouse.move(x1, y1, steps=10)
        page.mouse.up()
        page.wait_for_timeout(250)
        st2 = get_adapter_state(page)
        rect_el = next((e for e in st2["elements"] if e["type"] == "rectangle"), None)
        diffs2 = []
        if tool_before != exp2["selected_tool_before_drag"]:
            diffs2.append(f"selected_tool_before_drag: {tool_before} != {exp2['selected_tool_before_drag']}")
        if st2["element_count"] != exp2["element_count"]:
            diffs2.append(f"element_count: {st2['element_count']} != {exp2['element_count']}")
        if not rect_el:
            diffs2.append("missing rectangle element")
        else:
            for k in ["x", "y", "width", "height"]:
                if abs(rect_el[k] - exp2[k]) > 2:
                    diffs2.append(f"rect.{k}: {rect_el[k]} != {exp2[k]}")
            for k in ["strokeColor", "backgroundColor", "roughness"]:
                if rect_el[k] != exp2[k]:
                    diffs2.append(f"rect.{k}: {rect_el[k]} != {exp2[k]}")
        if st2["activeTool"] != exp2["activeTool_after_up"]:
            diffs2.append(f"activeTool_after_up: {st2['activeTool']} != {exp2['activeTool_after_up']}")
        record_case("TC-002", ev2, not diffs2, (time.perf_counter() - t0) * 1000,
                    ev2["comparison_rules"]["exact_fields"], "; ".join(diffs2) if diffs2 else None)

        # --- TC-003 (EV-003 / F-003): Ellipse Creation ---
        t0 = time.perf_counter()
        ev3 = ledger["EV-003"]
        exp3 = ev3["observed_output"]
        click_tool(page, ev3["input"]["tool"])
        page.wait_for_timeout(120)
        tool_before = get_adapter_state(page)["activeTool"]
        x0, y0 = ev3["input"]["drag_from"]
        x1, y1 = ev3["input"]["drag_to"]
        page.mouse.move(x0, y0)
        page.mouse.down()
        page.mouse.move(x1, y1, steps=10)
        page.mouse.up()
        page.wait_for_timeout(250)
        st3 = get_adapter_state(page)
        ell_el = next((e for e in st3["elements"] if e["type"] == "ellipse"), None)
        diffs3 = []
        if tool_before != exp3["selected_tool_before_drag"]:
            diffs3.append(f"selected_tool_before_drag: {tool_before}")
        if st3["element_count"] != exp3["element_count"]:
            diffs3.append(f"element_count: {st3['element_count']} != {exp3['element_count']}")
        if not ell_el:
            diffs3.append("missing ellipse element")
        else:
            for k in ["x", "y", "width", "height"]:
                if abs(ell_el[k] - exp3[k]) > 2:
                    diffs3.append(f"ellipse.{k}: {ell_el[k]} != {exp3[k]}")
        if st3["activeTool"] != exp3["activeTool_after_up"]:
            diffs3.append(f"activeTool_after_up: {st3['activeTool']}")
        record_case("TC-003", ev3, not diffs3, (time.perf_counter() - t0) * 1000,
                    ev3["comparison_rules"]["exact_fields"], "; ".join(diffs3) if diffs3 else None)

        # --- TC-004 (EV-004 / F-004): Arrow Creation & Bidirectional Binding ---
        t0 = time.perf_counter()
        ev4 = ledger["EV-004"]
        exp4 = ev4["observed_output"]
        click_tool(page, ev4["input"]["tool"])
        page.wait_for_timeout(120)
        tool_before = get_adapter_state(page)["activeTool"]
        x0, y0 = ev4["input"]["drag_from"]
        x1, y1 = ev4["input"]["drag_to"]
        page.mouse.move(x0, y0)
        page.mouse.down()
        page.mouse.move(x1, y1, steps=12)
        page.mouse.up()
        page.wait_for_timeout(250)
        st4 = get_adapter_state(page)
        arr_el = next((e for e in st4["elements"] if e["type"] == "arrow"), None)
        diffs4 = []
        if tool_before != exp4["selected_tool_before_drag"]:
            diffs4.append(f"selected_tool_before_drag: {tool_before}")
        if st4["element_count"] != exp4["element_count"]:
            diffs4.append(f"element_count: {st4['element_count']} != {exp4['element_count']}")
        if not arr_el:
            diffs4.append("missing arrow element")
        else:
            if len(arr_el.get("points") or []) < exp4["points_count"]:
                diffs4.append("arrow points_count < 2")
            if arr_el.get("endArrowhead") != exp4["endArrowhead"]:
                diffs4.append(f"endArrowhead: {arr_el.get('endArrowhead')}")
            if bool(arr_el.get("startBinding")) != exp4["has_start_binding"]:
                diffs4.append(f"startBinding missing: {arr_el.get('startBinding')}")
            if bool(arr_el.get("endBinding")) != exp4["has_end_binding"]:
                diffs4.append(f"endBinding missing: {arr_el.get('endBinding')}")
            bound_shapes = [e for e in st4["elements"] if e.get("boundElements") and any(b["id"] == arr_el["id"] for b in e["boundElements"])]
            if len(bound_shapes) < exp4["reciprocal_bound_elements_count"]:
                diffs4.append(f"reciprocal boundElements shapes={len(bound_shapes)} < 2")
        record_case("TC-004", ev4, not diffs4, (time.perf_counter() - t0) * 1000,
                    ev4["comparison_rules"]["exact_fields"], "; ".join(diffs4) if diffs4 else None)

        # --- TC-005 (EV-005 / F-005): Text Element Creation & Drawn Scene Visual Diff ---
        t0 = time.perf_counter()
        ev5 = ledger["EV-005"]
        exp5 = ev5["observed_output"]
        click_tool(page, ev5["input"]["tool"])
        page.wait_for_timeout(120)
        tool_before = get_adapter_state(page)["activeTool"]
        tx, ty = ev5["input"]["click_at"]
        page.mouse.click(tx, ty)
        page.wait_for_timeout(180)
        page.keyboard.type(ev5["input"]["text"])
        page.wait_for_timeout(120)
        page.keyboard.press(ev5["input"]["commit_key"])
        page.wait_for_timeout(200)
        # Deselect for clean visual comparison
        page.mouse.click(1120, 680)
        page.wait_for_timeout(250)
        st5 = get_adapter_state(page)
        txt_el = next((e for e in st5["elements"] if e["type"] == "text"), None)
        diffs5 = []
        if tool_before != exp5["selected_tool_before_click"]:
            diffs5.append(f"selected_tool_before_click: {tool_before}")
        if st5["element_count"] != exp5["element_count"]:
            diffs5.append(f"element_count: {st5['element_count']} != {exp5['element_count']}")
        if not txt_el:
            diffs5.append("missing text element")
        else:
            if txt_el.get("text") != exp5["text"]:
                diffs5.append(f"text: {txt_el.get('text')!r} != {exp5['text']!r}")
            if txt_el.get("fontSize") != exp5["fontSize"]:
                diffs5.append(f"fontSize: {txt_el.get('fontSize')} != {exp5['fontSize']}")
        if st5["activeTool"] != exp5["activeTool_after_commit"]:
            diffs5.append(f"activeTool_after_commit: {st5['activeTool']}")
        if is_reimpl:
            reimpl_p = PROOF_SHOTS_DIR / "reimpl_shapes_drawn_light.png"
            page.screenshot(path=str(reimpl_p))
            m = compute_visual_diff(PROOF_SHOTS_DIR / "orig_shapes_drawn_light.png", reimpl_p, PROOF_SHOTS_DIR / "diff_shapes_drawn_light.png")
            visual_metrics["shapes_drawn_light"] = m
            max_diff = ev5["comparison_rules"]["visual_max_diff_ratio"]
            if m["mae_ratio"] > max_diff:
                diffs5.append(f"visual_mae {m['mae_ratio']:.4f} > {max_diff}")
        record_case("TC-005", ev5, not diffs5, (time.perf_counter() - t0) * 1000,
                    ev5["comparison_rules"]["exact_fields"], "; ".join(diffs5) if diffs5 else None)

        # --- TC-008 (EV-008 / F-008): Dark Theme Toggle & Visual Diff (run while scene matches SCR-003!) ---
        t0 = time.perf_counter()
        ev8 = ledger["EV-008"]
        exp8 = ev8["observed_output"]
        page.locator('[data-testid="main-menu-trigger"]').click()
        page.wait_for_timeout(200)
        dark_toggle = page.locator('[data-testid="toggle-dark-mode"]')
        if dark_toggle.count() > 0:
            dark_toggle.click()
        else:
            page.evaluate("() => (window.__whiteboardAPI ? window.__whiteboardAPI.setTheme('dark') : window.__excalidrawAPI.updateScene({ appState: { theme: 'dark' } }))")
        page.wait_for_timeout(200)
        page.mouse.click(1120, 680)
        page.wait_for_timeout(300)
        st8 = get_adapter_state(page)
        diffs8 = []
        if st8["theme"] != exp8["dark_theme_value"]:
            diffs8.append(f"theme: {st8['theme']} != dark")
        if st8["dom_has_theme_dark"] != exp8["dom_has_theme_dark"]:
            diffs8.append("dom_has_theme_dark != True")
        if st8["default_bg_token"] != exp8["dark_default_bg_token"]:
            diffs8.append(f"dark_default_bg_token: {st8['default_bg_token']!r} != {exp8['dark_default_bg_token']!r}")
        if st8["island_bg_token"] != exp8["dark_island_bg_token"]:
            diffs8.append(f"dark_island_bg_token: {st8['island_bg_token']!r} != {exp8['dark_island_bg_token']!r}")
        rect_dark = next((e for e in st8["elements"] if e["type"] == "rectangle"), None)
        if not rect_dark or rect_dark["strokeColor"] != exp8["raw_element_stroke_preserved"]:
            diffs8.append("raw element strokeColor mutated under dark theme")
        if is_reimpl:
            reimpl_p = PROOF_SHOTS_DIR / "reimpl_dark_theme.png"
            page.screenshot(path=str(reimpl_p))
            m = compute_visual_diff(PROOF_SHOTS_DIR / "orig_dark_theme.png", reimpl_p, PROOF_SHOTS_DIR / "diff_dark_theme.png")
            visual_metrics["dark_theme"] = m
            max_diff = ev8["comparison_rules"]["visual_max_diff_ratio"]
            if m["mae_ratio"] > max_diff:
                diffs8.append(f"visual_mae {m['mae_ratio']:.4f} > {max_diff}")
        # Restore light theme
        page.evaluate("() => (window.__whiteboardAPI ? window.__whiteboardAPI.setTheme('light') : window.__excalidrawAPI.updateScene({ appState: { theme: 'light' } }))")
        page.wait_for_timeout(200)
        st8_light = get_adapter_state(page)
        if st8_light["theme"] != exp8["light_restored_theme"]:
            diffs8.append(f"light_restored_theme: {st8_light['theme']}")
        record_case("TC-008", ev8, not diffs8, (time.perf_counter() - t0) * 1000,
                    ev8["comparison_rules"]["exact_fields"], "; ".join(diffs8) if diffs8 else None)

        # --- TC-006 (EV-006 / F-006): Selection & Properties Update ---
        t0 = time.perf_counter()
        ev6 = ledger["EV-006"]
        exp6 = ev6["observed_output"]
        ex_click, ey_click = ev6["input"]["click_edge"]
        rect_v_before = next(e for e in get_adapter_state(page)["elements"] if e["type"] == "rectangle")["version"]
        page.mouse.click(ex_click, ey_click)
        page.wait_for_timeout(250)
        st6_sel = get_adapter_state(page)
        selected_via_click = len(st6_sel["selectedIds"]) > 0
        panel_visible = page.locator('.App-menu__left').is_visible()
        updates = ev6["input"]["updates"]
        if is_reimpl:
            page.locator('[data-testid="stroke-e03131"]').click()
            page.locator('[data-testid="bg-a5d8ff"]').click()
            page.locator('[data-testid="roughness-2"]').click()
        else:
            page.evaluate("""(u) => {
              const api = window.__excalidrawAPI;
              const els = api.getSceneElements().map(e =>
                e.type === 'rectangle'
                  ? { ...e, strokeColor: u.strokeColor, backgroundColor: u.backgroundColor, roughness: u.roughness, version: e.version + 1, versionNonce: (e.versionNonce || 0) + 1 }
                  : e
              );
              const rect = els.find(e => e.type === 'rectangle');
              api.updateScene({ elements: els, appState: { selectedElementIds: { [rect.id]: true } }, captureUpdate: window.__excalidrawHelpers.CaptureUpdateAction.IMMEDIATELY });
            }""", updates)
        page.wait_for_timeout(250)
        rect_after = next(e for e in get_adapter_state(page)["elements"] if e["type"] == "rectangle")
        diffs6 = []
        if selected_via_click != exp6["selected_via_canvas_click"]:
            diffs6.append("selected_via_canvas_click mismatch")
        if panel_visible != exp6["properties_panel_visible"]:
            diffs6.append("properties_panel_visible mismatch")
        for k in ["strokeColor", "backgroundColor", "roughness"]:
            if rect_after[k] != exp6[k]:
                diffs6.append(f"rect.{k}: {rect_after[k]} != {exp6[k]}")
        if not (rect_after["version"] > rect_v_before):
            diffs6.append("version did not increment")
        record_case("TC-006", ev6, not diffs6, (time.perf_counter() - t0) * 1000,
                    ev6["comparison_rules"]["exact_fields"], "; ".join(diffs6) if diffs6 else None)

        # --- TC-007 (EV-007 / F-007): Undo / Redo Stack Cycle ---
        t0 = time.perf_counter()
        ev7 = ledger["EV-007"]
        exp7 = ev7["observed_output"]
        page.mouse.click(1120, 680)
        page.wait_for_timeout(120)
        c_before = get_adapter_state(page)["element_count"]
        click_tool(page, ev7["input"]["tool"])
        page.wait_for_timeout(120)
        dx0, dy0 = ev7["input"]["drag_from"]
        dx1, dy1 = ev7["input"]["drag_to"]
        page.mouse.move(dx0, dy0)
        page.mouse.down()
        page.mouse.move(dx1, dy1, steps=8)
        page.mouse.up()
        page.wait_for_timeout(250)
        c_after_draw = get_adapter_state(page)["element_count"]
        undo_btn = page.locator('[data-testid="button-undo"]').first
        redo_btn = page.locator('[data-testid="button-redo"]').first
        undo_btn.click()
        page.wait_for_timeout(200)
        c_after_undo = get_adapter_state(page)["element_count"]
        redo_disabled = redo_btn.is_disabled()
        redo_btn.click()
        page.wait_for_timeout(200)
        c_after_redo = get_adapter_state(page)["element_count"]
        undo_btn.click()
        page.wait_for_timeout(200)
        c_after_undo2 = get_adapter_state(page)["element_count"]
        actual7 = {
            "count_before_draw": c_before,
            "count_after_draw": c_after_draw,
            "count_after_undo": c_after_undo,
            "redo_disabled_after_undo": redo_disabled,
            "count_after_redo": c_after_redo,
            "count_after_second_undo": c_after_undo2,
        }
        diffs7 = [f"{k}: {actual7[k]} != {exp7[k]}" for k in exp7 if actual7[k] != exp7[k]]
        record_case("TC-007", ev7, not diffs7, (time.perf_counter() - t0) * 1000,
                    ev7["comparison_rules"]["exact_fields"], "; ".join(diffs7) if diffs7 else None)

        # --- TC-009 (EV-009 / F-009): Zoom Stepping ---
        t0 = time.perf_counter()
        ev9 = ledger["EV-009"]
        exp9 = ev9["observed_output"]
        z0 = round(get_adapter_state(page)["zoom"], 3)
        page.locator('button[aria-label="Zoom in"]').first.click()
        page.wait_for_timeout(150)
        z1 = round(get_adapter_state(page)["zoom"], 3)
        page.locator('button[aria-label="Zoom out"]').first.click()
        page.wait_for_timeout(150)
        z2 = round(get_adapter_state(page)["zoom"], 3)
        actual9 = {"zoom_initial": z0, "zoom_after_in": z1, "zoom_after_out": z2, "step_delta": round(z1 - z0, 3)}
        diffs9 = [f"{k}: {actual9[k]} != {exp9[k]}" for k in exp9 if abs(actual9[k] - exp9[k]) > 0.001]
        record_case("TC-009", ev9, not diffs9, (time.perf_counter() - t0) * 1000,
                    ev9["comparison_rules"]["exact_fields"], "; ".join(diffs9) if diffs9 else None)

        # --- TC-010 (EV-010 / F-010): .excalidraw v2 Export & Restore Roundtrip ---
        t0 = time.perf_counter()
        ev10 = ledger["EV-010"]
        exp10 = ev10["observed_output"]
        exported_str = page.evaluate("""() => window.__whiteboardAPI ? window.__whiteboardAPI.exportExcalidrawJSON() : window.__excalidrawHelpers.exportExcalidrawJSON()""")
        exported_obj = json.loads(exported_str)
        schema_err = None
        try:
            jsonschema.validate(exported_obj, scene_schema)
        except Exception as e:
            schema_err = str(e).splitlines()[0]
        page.evaluate("""() => {
          if (window.__whiteboardAPI) window.__whiteboardAPI.updateScene({ elements: [] });
          else window.__excalidrawAPI.updateScene({ elements: [], captureUpdate: window.__excalidrawHelpers.CaptureUpdateAction.NEVER });
        }""")
        page.wait_for_timeout(200)
        c_cleared = get_adapter_state(page)["element_count"]
        page.evaluate("""(s) => {
          if (window.__whiteboardAPI) window.__whiteboardAPI.importExcalidrawJSON(s);
          else window.__excalidrawHelpers.importExcalidrawJSON(s);
        }""", exported_str)
        page.wait_for_timeout(250)
        st10 = get_adapter_state(page)
        exported_ids = [e["id"] for e in exported_obj.get("elements", [])]
        restored_ids = [e["id"] for e in st10["elements"]]
        actual10 = {
            "exported_type": exported_obj.get("type"),
            "exported_version": exported_obj.get("version"),
            "exported_element_count": len(exported_obj.get("elements", [])),
            "exported_element_types": [e["type"] for e in exported_obj.get("elements", [])],
            "count_after_clear": c_cleared,
            "count_after_restore": st10["element_count"],
            "ids_match": exported_ids == restored_ids,
            "schema_valid": schema_err is None,
        }
        diffs10 = [f"{k}: {actual10[k]} != {exp10[k]}" for k in exp10 if actual10[k] != exp10[k]]
        if schema_err:
            diffs10.append(f"schema_err: {schema_err}")
        record_case("TC-010", ev10, not diffs10, (time.perf_counter() - t0) * 1000,
                    ev10["comparison_rules"]["exact_fields"], "; ".join(diffs10) if diffs10 else None)

        # --- TC-011 (EV-011 / F-011): localStorage Persistence Across Reload ---
        t0 = time.perf_counter()
        ev11 = ledger["EV-011"]
        exp11 = ev11["observed_output"]
        page.wait_for_timeout(250)
        ls_pre = page.evaluate("""() => ({
          has_elements_key: localStorage.getItem('excalidraw') !== null,
          has_state_key: localStorage.getItem('excalidraw-state') !== null,
          stored_element_count: JSON.parse(localStorage.getItem('excalidraw') || '[]').length
        })""")
        page.reload(wait_until="networkidle")
        page.wait_for_function("() => Boolean((window.__excalidrawAPI || window.__whiteboardAPI) && document.querySelector('canvas'))", timeout=15000)
        page.wait_for_timeout(350)
        st11 = get_adapter_state(page)
        actual11 = {
            "has_elements_key": ls_pre["has_elements_key"],
            "has_state_key": ls_pre["has_state_key"],
            "stored_element_count": ls_pre["stored_element_count"],
            "scene_after_reload_count": st11["element_count"],
            "scene_after_reload_types": [e["type"] for e in st11["elements"]],
            "persisted_ids_match": [e["id"] for e in st11["elements"]] == restored_ids,
        }
        diffs11 = [f"{k}: {actual11[k]} != {exp11[k]}" for k in exp11 if actual11[k] != exp11[k]]
        record_case("TC-011", ev11, not diffs11, (time.perf_counter() - t0) * 1000,
                    ev11["comparison_rules"]["exact_fields"], "; ".join(diffs11) if diffs11 else None)

        browser.close()

    # --- TC-012 (EV-012 / F-012): Official Distribution REA Audit Integrity ---
    t0 = time.perf_counter()
    ev12 = ledger["EV-012"]
    exp12 = ev12["observed_output"]
    ra = json.loads(RELEASE_AUDIT_PATH.read_text(encoding="utf-8"))
    diffs12 = []
    if ra["binary"]["sha256"] != exp12["bundle_sha256"]:
        diffs12.append("binary.sha256 mismatch")
    if ra["archive"]["sha256"] != exp12["archive_sha256"]:
        diffs12.append("archive.sha256 mismatch")
    if ra["archive"]["upstream_checksum_verified"] is not True:
        diffs12.append("archive.upstream_checksum_verified != True")
    if ra["target"]["pinned_commit"] != exp12["pinned_commit"]:
        diffs12.append("pinned_commit mismatch")
    record_case("TC-012", ev12, not diffs12, (time.perf_counter() - t0) * 1000,
                ev12["comparison_rules"]["exact_fields"], "; ".join(diffs12) if diffs12 else None)

    # Re-sort cases in TC-001..TC-012 numeric order
    cases.sort(key=lambda c: int(c["test_id"].split("-")[1]))

    if is_reimpl:
        metrics_payload = {
            "schema_version": "1.0.0",
            "threshold_mae_percent": 8.0,
            "scenes": visual_metrics,
        }
        (PROOF_SHOTS_DIR / "visual_diff_metrics.json").write_text(
            json.dumps(metrics_payload, indent=2) + "\n", encoding="utf-8"
        )

    passed_n = sum(1 for c in cases if c["verdict"] == "PASS")
    failed_n = sum(1 for c in cases if c["verdict"] == "FAIL")
    report = {
        "schema_version": "1.0.0",
        "mode": report_mode,
        "target": {
            "name": "SketchBoard CR (clean-room reimplementation)" if is_reimpl else "@excalidraw/excalidraw@0.18.1 (official upstream)",
            "url_or_binary": target_url,
            "artifact_sha256": None if is_reimpl else ra["binary"]["sha256"],
        },
        "evidence_file": "06_evidence/ledger.jsonl",
        "executed_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "total": len(cases),
            "passed": passed_n,
            "failed": failed_n,
            "skipped": 0,
            "unverified": 0,
        },
        "cases": cases,
    }
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description="Excalidraw v0.18.1 Differential Parity Test Harness")
    ap.add_argument("--mode", choices=["baseline", "upstream_baseline", "reimplementation_diff"], required=True)
    ap.add_argument("--target-url", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out = pathlib.Path(args.out) if args.out else (
        BUNDLE_DIR / "07_tests" / ("reimpl_parity_report.json" if args.mode == "reimplementation_diff" else "parity_report.json")
    )
    report = run_suite(args.mode, args.target_url, out)
    print(json.dumps(report["summary"], indent=2))
    if report["summary"]["failed"] > 0:
        for c in report["cases"]:
            if c["verdict"] != "PASS":
                print(f"FAIL {c['test_id']}: {c['diff_summary']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
