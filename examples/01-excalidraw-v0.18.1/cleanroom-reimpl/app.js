/*
 * SketchBoard CR — Clean-Room Interactive Hand-Drawn Whiteboard Engine
 * Authored strictly from spec-anything 09_contracts, 11_ui/tokens.json, and 06_evidence/ledger.jsonl.
 * Zero upstream source code or assets copied.
 */
(function () {
  "use strict";

  const LS_ELEMENTS_KEY = "excalidraw";
  const LS_STATE_KEY = "excalidraw-state";
  const ZOOM_STEP = 0.1;
  const MIN_ZOOM = 0.1;
  const MAX_ZOOM = 30.0;
  const BINDING_SNAP_RADIUS = 18;

  // Deterministic PRNG (Mulberry32) seeded per element.seed so hand-drawn strokes stay stable across frames
  function createRng(seed) {
    let a = (seed >>> 0) || 1;
    return function () {
      a |= 0;
      a = (a + 0x6d2b79f5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function randomInt() {
    return Math.floor(Math.random() * 2147483647) + 1;
  }

  function genId() {
    const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
    let out = "";
    for (let i = 0; i < 21; i++) {
      out += chars[Math.floor(Math.random() * chars.length)];
    }
    return out;
  }

  function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  function defaultAppState() {
    return {
      theme: "light",
      viewBackgroundColor: "#ffffff",
      zoom: { value: 1 },
      scrollX: 0,
      scrollY: 0,
      gridSize: 20,
      gridStep: 5,
      gridModeEnabled: false,
      activeTool: { type: "selection", locked: false, lastActiveTool: null },
      selectedElementIds: {},
      currentItemStrokeColor: "#1e1e1e",
      currentItemBackgroundColor: "transparent",
      currentItemFillStyle: "solid",
      currentItemStrokeWidth: 2,
      currentItemStrokeStyle: "solid",
      currentItemRoughness: 1,
      currentItemOpacity: 100,
      currentItemFontSize: 20,
      currentItemFontFamily: 5,
    };
  }

  function normalizeElement(raw) {
    const base = {
      id: raw.id || genId(),
      type: raw.type || "rectangle",
      x: Number(raw.x || 0),
      y: Number(raw.y || 0),
      width: Number(raw.width || 0),
      height: Number(raw.height || 0),
      angle: Number(raw.angle || 0),
      strokeColor: raw.strokeColor || "#1e1e1e",
      backgroundColor: raw.backgroundColor || "transparent",
      fillStyle: raw.fillStyle || "solid",
      strokeWidth: Number(raw.strokeWidth || 2),
      strokeStyle: raw.strokeStyle || "solid",
      roughness: raw.roughness !== undefined ? Number(raw.roughness) : 1,
      opacity: raw.opacity !== undefined ? Number(raw.opacity) : 100,
      roundness: raw.roundness !== undefined ? raw.roundness : (raw.type === "rectangle" ? { type: 3 } : raw.type === "arrow" || raw.type === "diamond" ? { type: 2 } : null),
      seed: Number.isInteger(raw.seed) ? raw.seed : randomInt(),
      version: Number.isInteger(raw.version) && raw.version >= 1 ? raw.version : 1,
      versionNonce: Number.isInteger(raw.versionNonce) ? raw.versionNonce : randomInt(),
      index: raw.index || null,
      isDeleted: Boolean(raw.isDeleted),
      groupIds: Array.isArray(raw.groupIds) ? raw.groupIds.slice() : [],
      frameId: raw.frameId || null,
      boundElements: Array.isArray(raw.boundElements) ? deepClone(raw.boundElements) : null,
      updated: raw.updated || Date.now(),
      link: raw.link || null,
      locked: Boolean(raw.locked),
    };

    if (base.type === "arrow" || base.type === "line") {
      base.points = Array.isArray(raw.points) && raw.points.length >= 2 ? deepClone(raw.points) : [[0, 0], [base.width, base.height]];
      base.lastCommittedPoint = raw.lastCommittedPoint || null;
      base.startBinding = raw.startBinding ? deepClone(raw.startBinding) : null;
      base.endBinding = raw.endBinding ? deepClone(raw.endBinding) : null;
      base.startArrowhead = raw.startArrowhead !== undefined ? raw.startArrowhead : null;
      base.endArrowhead = raw.endArrowhead !== undefined ? raw.endArrowhead : (base.type === "arrow" ? "arrow" : null);
      if (base.type === "arrow") {
        base.elbowed = Boolean(raw.elbowed);
      }
    } else if (base.type === "text") {
      base.text = typeof raw.text === "string" ? raw.text : "";
      base.originalText = typeof raw.originalText === "string" ? raw.originalText : base.text;
      base.fontSize = Number(raw.fontSize || 20);
      base.fontFamily = Number(raw.fontFamily || 5);
      base.textAlign = raw.textAlign || "left";
      base.verticalAlign = raw.verticalAlign || "top";
      base.containerId = raw.containerId || null;
      base.autoResize = raw.autoResize !== undefined ? Boolean(raw.autoResize) : true;
      base.lineHeight = Number(raw.lineHeight || 1.25);
    } else if (base.type === "freedraw") {
      base.points = Array.isArray(raw.points) ? deepClone(raw.points) : [[0, 0]];
      base.pressures = Array.isArray(raw.pressures) ? raw.pressures.slice() : [];
      base.simulatePressure = raw.simulatePressure !== undefined ? Boolean(raw.simulatePressure) : true;
      base.lastCommittedPoint = null;
    }
    return base;
  }

  // Application State
  let elements = [];
  let appState = defaultAppState();
  const undoStack = [];
  const redoStack = [];

  // DOM References
  const rootEl = document.getElementById("app");
  const canvas = document.getElementById("board-canvas");
  const ctx = canvas.getContext("2d");
  const menuBtn = document.getElementById("btn-main-menu");
  const menuDropdown = document.getElementById("main-menu-dropdown");
  const menuToggleDark = document.getElementById("menu-toggle-dark");
  const menuThemeBadge = document.getElementById("menu-theme-badge");
  const menuExportBtn = document.getElementById("menu-export-json");
  const menuImportInput = document.getElementById("menu-import-file");
  const menuResetBtn = document.getElementById("menu-reset-canvas");
  const topExportBtn = document.getElementById("btn-export-pill");
  const toolbarThemeBtn = document.getElementById("toolbar-theme-btn");
  const inspectorEl = document.getElementById("properties-panel");
  const opacitySlider = document.getElementById("prop-opacity");
  const zoomInBtn = document.getElementById("btn-zoom-in");
  const zoomOutBtn = document.getElementById("btn-zoom-out");
  const zoomResetBtn = document.getElementById("btn-zoom-reset");
  const undoBtn = document.getElementById("btn-undo");
  const redoBtn = document.getElementById("btn-redo");
  const textEditorEl = document.getElementById("inline-text-editor");
  const hintViewerEl = document.getElementById("hint-viewer");

  // Pointer interaction state
  let interaction = null; // { mode: 'draw'|'move'|'pan', startX, startY, element, origX, origY, ... }
  let activeTextCoords = null;

  // --- Persistence ---
  function persistToLocalStorage() {
    try {
      const active = elements.filter((e) => !e.isDeleted);
      window.localStorage.setItem(LS_ELEMENTS_KEY, JSON.stringify(active));
      const persistState = {
        theme: appState.theme,
        viewBackgroundColor: appState.viewBackgroundColor,
        zoom: appState.zoom,
        scrollX: appState.scrollX,
        scrollY: appState.scrollY,
        gridSize: appState.gridSize,
        gridStep: appState.gridStep,
        gridModeEnabled: appState.gridModeEnabled,
        currentItemStrokeColor: appState.currentItemStrokeColor,
        currentItemBackgroundColor: appState.currentItemBackgroundColor,
        currentItemRoughness: appState.currentItemRoughness,
        currentItemStrokeWidth: appState.currentItemStrokeWidth,
      };
      window.localStorage.setItem(LS_STATE_KEY, JSON.stringify(persistState));
    } catch (_e) {
      // ignore storage errors in restricted contexts
    }
  }

  function hydrateFromLocalStorage() {
    try {
      const rawEls = window.localStorage.getItem(LS_ELEMENTS_KEY);
      const rawSt = window.localStorage.getItem(LS_STATE_KEY);
      if (rawEls) {
        const parsed = JSON.parse(rawEls);
        if (Array.isArray(parsed)) {
          elements = parsed.map(normalizeElement);
        }
      }
      if (rawSt) {
        const parsedSt = JSON.parse(rawSt);
        if (parsedSt && typeof parsedSt === "object") {
          appState = {
            ...defaultAppState(),
            ...parsedSt,
            zoom: parsedSt.zoom && typeof parsedSt.zoom.value === "number" ? { value: parsedSt.zoom.value } : { value: 1 },
            activeTool: defaultAppState().activeTool,
            selectedElementIds: {},
          };
        }
      }
    } catch (_e) {
      elements = [];
      appState = defaultAppState();
    }
  }

  // --- History Stack ---
  function snapshotScene() {
    return {
      elements: deepClone(elements),
      viewBackgroundColor: appState.viewBackgroundColor,
    };
  }

  function pushHistory(prevSnap) {
    undoStack.push(prevSnap);
    if (undoStack.length > 100) undoStack.shift();
    redoStack.length = 0;
    syncHistoryButtons();
  }

  function undo() {
    if (!undoStack.length) return false;
    redoStack.push(snapshotScene());
    const prev = undoStack.pop();
    elements = prev.elements.map(normalizeElement);
    appState.viewBackgroundColor = prev.viewBackgroundColor;
    appState.selectedElementIds = {};
    persistToLocalStorage();
    syncUI();
    render();
    return true;
  }

  function redo() {
    if (!redoStack.length) return false;
    undoStack.push(snapshotScene());
    const next = redoStack.pop();
    elements = next.elements.map(normalizeElement);
    appState.viewBackgroundColor = next.viewBackgroundColor;
    appState.selectedElementIds = {};
    persistToLocalStorage();
    syncUI();
    render();
    return true;
  }

  function syncHistoryButtons() {
    undoBtn.disabled = undoStack.length === 0;
    redoBtn.disabled = redoStack.length === 0;
  }

  // --- Coordinate Transforms ---
  function resizeCanvas() {
    const rect = rootEl.getBoundingClientRect();
    const w = Math.max(1, Math.round(rect.width));
    const h = Math.max(1, Math.round(rect.height));
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
    }
  }

  function viewportToScene(vx, vy) {
    const z = appState.zoom.value;
    return {
      x: vx / z - appState.scrollX,
      y: vy / z - appState.scrollY,
    };
  }

  function sceneToViewport(sx, sy) {
    const z = appState.zoom.value;
    return {
      x: (sx + appState.scrollX) * z,
      y: (sy + appState.scrollY) * z,
    };
  }

  // --- Geometry & Binding Helpers ---
  function getNonDeletedElements() {
    return elements.filter((e) => !e.isDeleted);
  }

  function distanceToRectEdge(px, py, el) {
    const left = el.x;
    const right = el.x + el.width;
    const top = el.y;
    const bottom = el.y + el.height;
    const clampedX = Math.max(left, Math.min(px, right));
    const clampedY = Math.max(top, Math.min(py, bottom));
    const inside = px >= left && px <= right && py >= top && py <= bottom;
    if (!inside) {
      return Math.hypot(px - clampedX, py - clampedY);
    }
    return Math.min(px - left, right - px, py - top, bottom - py);
  }

  function distanceToEllipseEdge(px, py, el) {
    const rx = Math.max(1, el.width / 2);
    const ry = Math.max(1, el.height / 2);
    const cx = el.x + rx;
    const cy = el.y + ry;
    const nx = (px - cx) / rx;
    const ny = (py - cy) / ry;
    const norm = Math.hypot(nx, ny);
    if (norm === 0) return Math.min(rx, ry);
    const bx = cx + (nx / norm) * rx;
    const by = cy + (ny / norm) * ry;
    return Math.hypot(px - bx, py - by);
  }

  function findBindingTarget(sx, sy, excludeId) {
    let best = null;
    let bestDist = BINDING_SNAP_RADIUS;
    for (const el of getNonDeletedElements()) {
      if (el.id === excludeId) continue;
      if (el.type !== "rectangle" && el.type !== "ellipse" && el.type !== "diamond") continue;
      const dist = el.type === "ellipse" ? distanceToEllipseEdge(sx, sy, el) : distanceToRectEdge(sx, sy, el);
      if (dist <= bestDist) {
        bestDist = dist;
        best = { element: el, gap: Math.max(1, Math.round(dist)) };
      }
    }
    return best;
  }

  function attachBindingToShape(shapeEl, arrowId) {
    if (!Array.isArray(shapeEl.boundElements)) {
      shapeEl.boundElements = [];
    }
    if (!shapeEl.boundElements.some((b) => b.id === arrowId)) {
      shapeEl.boundElements.push({ id: arrowId, type: "arrow" });
      shapeEl.version += 1;
      shapeEl.versionNonce = randomInt();
    }
  }

  function hitTestElement(sx, sy) {
    const active = getNonDeletedElements();
    for (let i = active.length - 1; i >= 0; i--) {
      const el = active[i];
      if (el.type === "rectangle" || el.type === "diamond") {
        const margin = 8;
        const inBox = sx >= el.x - margin && sx <= el.x + el.width + margin && sy >= el.y - margin && sy <= el.y + el.height + margin;
        if (!inBox) continue;
        if (el.backgroundColor !== "transparent") return el;
        if (distanceToRectEdge(sx, sy, el) <= 12) return el;
      } else if (el.type === "ellipse") {
        const rx = Math.max(1, el.width / 2);
        const ry = Math.max(1, el.height / 2);
        const cx = el.x + rx;
        const cy = el.y + ry;
        const norm = Math.hypot((sx - cx) / rx, (sy - cy) / ry);
        if (el.backgroundColor !== "transparent" && norm <= 1.05) return el;
        if (distanceToEllipseEdge(sx, sy, el) <= 12) return el;
      } else if (el.type === "text") {
        if (sx >= el.x - 4 && sx <= el.x + Math.max(el.width, 20) + 4 && sy >= el.y - 4 && sy <= el.y + Math.max(el.height, 24) + 4) {
          return el;
        }
      } else if (el.type === "arrow" || el.type === "line") {
        const pts = el.points || [[0, 0], [el.width, el.height]];
        for (let p = 0; p < pts.length - 1; p++) {
          const x1 = el.x + pts[p][0];
          const y1 = el.y + pts[p][1];
          const x2 = el.x + pts[p + 1][0];
          const y2 = el.y + pts[p + 1][1];
          const dx = x2 - x1;
          const dy = y2 - y1;
          const lenSq = dx * dx + dy * dy || 1;
          const t = Math.max(0, Math.min(1, ((sx - x1) * dx + (sy - y1) * dy) / lenSq));
          const dist = Math.hypot(sx - (x1 + t * dx), sy - (y1 + t * dy));
          if (dist <= 10) return el;
        }
      } else if (el.type === "freedraw") {
        if (sx >= el.x - 6 && sx <= el.x + el.width + 6 && sy >= el.y - 6 && sy <= el.y + el.height + 6) {
          return el;
        }
      }
    }
    return null;
  }

  // --- Hand-Drawn Sketchy Canvas Renderer (Deterministic per element.seed) ---
  function jitter(rng, amp) {
    return (rng() - 0.5) * 2 * amp;
  }

  function applyStrokeStyle(c, el) {
    c.strokeStyle = el.strokeColor;
    c.lineWidth = el.strokeWidth;
    c.lineCap = "round";
    c.lineJoin = "round";
    if (el.strokeStyle === "dashed") {
      c.setLineDash([8, 6]);
    } else if (el.strokeStyle === "dotted") {
      c.setLineDash([2, 5]);
    } else {
      c.setLineDash([]);
    }
  }

  function drawSketchyLine(c, x1, y1, x2, y2, roughness, rng) {
    const passes = roughness === 0 ? 1 : 2;
    const amp = roughness * 1.45;
    for (let pass = 0; pass < passes; pass++) {
      const mx = (x1 + x2) / 2 + jitter(rng, amp);
      const my = (y1 + y2) / 2 + jitter(rng, amp);
      c.beginPath();
      c.moveTo(x1 + jitter(rng, amp * 0.6), y1 + jitter(rng, amp * 0.6));
      c.quadraticCurveTo(mx, my, x2 + jitter(rng, amp * 0.6), y2 + jitter(rng, amp * 0.6));
      c.stroke();
    }
  }

  function traceRoundedRectPath(c, x, y, w, h, r) {
    const cr = Math.min(r, w / 2, h / 2);
    c.beginPath();
    c.moveTo(x + cr, y);
    c.lineTo(x + w - cr, y);
    c.quadraticCurveTo(x + w, y, x + w, y + cr);
    c.lineTo(x + w, y + h - cr);
    c.quadraticCurveTo(x + w, y + h, x + w - cr, y + h);
    c.lineTo(x + cr, y + h);
    c.quadraticCurveTo(x, y + h, x, y + h - cr);
    c.lineTo(x, y + cr);
    c.quadraticCurveTo(x, y, x + cr, y);
    c.closePath();
  }

  function fillShape(c, el, clipFn) {
    if (!el.backgroundColor || el.backgroundColor === "transparent") return;
    c.save();
    clipFn();
    if (el.fillStyle === "solid") {
      c.fillStyle = el.backgroundColor;
      c.fill();
    } else {
      c.clip();
      c.strokeStyle = el.backgroundColor;
      c.lineWidth = Math.max(1, el.strokeWidth * 0.8);
      const step = 8;
      const diag = el.width + el.height;
      c.beginPath();
      for (let d = -el.height; d < diag; d += step) {
        c.moveTo(el.x + d, el.y);
        c.lineTo(el.x + d - el.height, el.y + el.height);
      }
      if (el.fillStyle === "cross-hatch") {
        for (let d = -el.height; d < diag; d += step) {
          c.moveTo(el.x + d, el.y + el.height);
          c.lineTo(el.x + d - el.height, el.y);
        }
      }
      c.stroke();
    }
    c.restore();
  }

  function renderRectangle(c, el, rng) {
    const r = el.roundness ? Math.min(32, Math.min(el.width, el.height) * 0.25) : 0;
    fillShape(c, el, () => traceRoundedRectPath(c, el.x, el.y, el.width, el.height, r));
    applyStrokeStyle(c, el);
    const passes = el.roughness === 0 ? 1 : 2;
    const amp = el.roughness * 1.4;
    for (let pass = 0; pass < passes; pass++) {
      const ox = jitter(rng, amp * 0.5);
      const oy = jitter(rng, amp * 0.5);
      const x = el.x + ox;
      const y = el.y + oy;
      const w = el.width;
      const h = el.height;
      const cr = Math.min(r, w / 2, h / 2);
      c.beginPath();
      c.moveTo(x + cr, y);
      c.quadraticCurveTo(x + w / 2, y + jitter(rng, amp), x + w - cr, y);
      if (cr > 0) c.quadraticCurveTo(x + w, y, x + w, y + cr);
      c.quadraticCurveTo(x + w + jitter(rng, amp), y + h / 2, x + w, y + h - cr);
      if (cr > 0) c.quadraticCurveTo(x + w, y + h, x + w - cr, y + h);
      c.quadraticCurveTo(x + w / 2, y + h + jitter(rng, amp), x + cr, y + h);
      if (cr > 0) c.quadraticCurveTo(x, y + h, x, y + h - cr);
      c.quadraticCurveTo(x + jitter(rng, amp), y + h / 2, x, y + cr);
      if (cr > 0) c.quadraticCurveTo(x, y, x + cr, y);
      c.stroke();
    }
  }

  function renderEllipse(c, el, rng) {
    const cx = el.x + el.width / 2;
    const cy = el.y + el.height / 2;
    const rx = Math.max(0.5, el.width / 2);
    const ry = Math.max(0.5, el.height / 2);
    fillShape(c, el, () => {
      c.beginPath();
      c.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      c.closePath();
    });
    applyStrokeStyle(c, el);
    if (el.roughness === 0) {
      c.beginPath();
      c.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2);
      c.stroke();
      return;
    }
    const passes = 2;
    const steps = 28;
    const amp = el.roughness * 1.3;
    for (let pass = 0; pass < passes; pass++) {
      c.beginPath();
      const startAngle = pass * 0.25;
      const endAngle = startAngle + Math.PI * 2 + 0.14;
      for (let i = 0; i <= steps; i++) {
        const theta = startAngle + (i / steps) * (endAngle - startAngle);
        const px = cx + (rx + jitter(rng, amp)) * Math.cos(theta);
        const py = cy + (ry + jitter(rng, amp)) * Math.sin(theta);
        if (i === 0) c.moveTo(px, py);
        else c.lineTo(px, py);
      }
      c.stroke();
    }
  }

  function renderDiamond(c, el, rng) {
    const top = [el.x + el.width / 2, el.y];
    const right = [el.x + el.width, el.y + el.height / 2];
    const bottom = [el.x + el.width / 2, el.y + el.height];
    const left = [el.x, el.y + el.height / 2];
    fillShape(c, el, () => {
      c.beginPath();
      c.moveTo(top[0], top[1]);
      c.lineTo(right[0], right[1]);
      c.lineTo(bottom[0], bottom[1]);
      c.lineTo(left[0], left[1]);
      c.closePath();
    });
    applyStrokeStyle(c, el);
    drawSketchyLine(c, top[0], top[1], right[0], right[1], el.roughness, rng);
    drawSketchyLine(c, right[0], right[1], bottom[0], bottom[1], el.roughness, rng);
    drawSketchyLine(c, bottom[0], bottom[1], left[0], left[1], el.roughness, rng);
    drawSketchyLine(c, left[0], left[1], top[0], top[1], el.roughness, rng);
  }

  function renderLinear(c, el, rng) {
    const pts = el.points || [[0, 0], [el.width, el.height]];
    if (pts.length < 2) return;
    applyStrokeStyle(c, el);
    for (let i = 0; i < pts.length - 1; i++) {
      drawSketchyLine(
        c,
        el.x + pts[i][0],
        el.y + pts[i][1],
        el.x + pts[i + 1][0],
        el.y + pts[i + 1][1],
        el.roughness,
        rng,
      );
    }
    if (el.type === "arrow" && el.endArrowhead === "arrow") {
      const p1 = pts[pts.length - 2];
      const p2 = pts[pts.length - 1];
      const x1 = el.x + p1[0];
      const y1 = el.y + p1[1];
      const x2 = el.x + p2[0];
      const y2 = el.y + p2[1];
      const angle = Math.atan2(y2 - y1, x2 - x1);
      const headLen = 18;
      const spread = 0.42;
      drawSketchyLine(c, x2, y2, x2 - headLen * Math.cos(angle - spread), y2 - headLen * Math.sin(angle - spread), Math.min(1, el.roughness), rng);
      drawSketchyLine(c, x2, y2, x2 - headLen * Math.cos(angle + spread), y2 - headLen * Math.sin(angle + spread), Math.min(1, el.roughness), rng);
    }
  }

  function renderText(c, el) {
    c.fillStyle = el.strokeColor;
    c.font = `${el.fontSize || 20}px "Comic Sans MS", "Chalkboard SE", "Segoe Print", cursive, sans-serif`;
    c.textBaseline = "top";
    c.textAlign = el.textAlign || "left";
    const lines = String(el.text || "").split("\n");
    const lh = (el.fontSize || 20) * (el.lineHeight || 1.25);
    lines.forEach((line, idx) => {
      c.fillText(line, el.x, el.y + idx * lh);
    });
  }

  function renderFreedraw(c, el) {
    const pts = el.points || [];
    if (pts.length < 2) return;
    applyStrokeStyle(c, el);
    c.beginPath();
    c.moveTo(el.x + pts[0][0], el.y + pts[0][1]);
    for (let i = 1; i < pts.length; i++) {
      c.lineTo(el.x + pts[i][0], el.y + pts[i][1]);
    }
    c.stroke();
  }

  function renderSelectionBox(c, el) {
    const pad = 6;
    const x = el.x - pad;
    const y = el.y - pad;
    const w = Math.max(el.width, 4) + pad * 2;
    const h = Math.max(el.height, 4) + pad * 2;
    c.save();
    c.setLineDash([]);
    c.strokeStyle = "#6965db";
    c.lineWidth = 1;
    c.strokeRect(x, y, w, h);
    const handles = [
      [x, y],
      [x + w, y],
      [x, y + h],
      [x + w, y + h],
    ];
    c.fillStyle = "#ffffff";
    handles.forEach(([hx, hy]) => {
      c.fillRect(hx - 3.5, hy - 3.5, 7, 7);
      c.strokeRect(hx - 3.5, hy - 3.5, 7, 7);
    });
    // Rotation handle
    c.beginPath();
    c.arc(x + w / 2, y - 18, 4, 0, Math.PI * 2);
    c.fill();
    c.stroke();
    c.restore();
  }

  function render() {
    resizeCanvas();
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = appState.viewBackgroundColor || "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const z = appState.zoom.value;
    ctx.scale(z, z);
    ctx.translate(appState.scrollX, appState.scrollY);

    const active = getNonDeletedElements();
    for (const el of active) {
      ctx.save();
      ctx.globalAlpha = Math.max(0, Math.min(1, (el.opacity ?? 100) / 100));
      const rng = createRng(el.seed);
      if (el.type === "rectangle") renderRectangle(ctx, el, rng);
      else if (el.type === "ellipse") renderEllipse(ctx, el, rng);
      else if (el.type === "diamond") renderDiamond(ctx, el, rng);
      else if (el.type === "arrow" || el.type === "line") renderLinear(ctx, el, rng);
      else if (el.type === "text") renderText(ctx, el);
      else if (el.type === "freedraw") renderFreedraw(ctx, el);
      ctx.restore();
    }

    // Draw selection frames
    const selIds = Object.keys(appState.selectedElementIds || {}).filter((k) => appState.selectedElementIds[k]);
    for (const id of selIds) {
      const el = active.find((e) => e.id === id);
      if (el) renderSelectionBox(ctx, el);
    }

    ctx.restore();
  }

  // --- UI Synchronization ---
  function getSelectedElements() {
    const sel = appState.selectedElementIds || {};
    return getNonDeletedElements().filter((e) => sel[e.id]);
  }

  function syncUI() {
    // Theme class
    if (appState.theme === "dark") {
      rootEl.classList.add("theme--dark");
      menuThemeBadge.textContent = "On";
    } else {
      rootEl.classList.remove("theme--dark");
      menuThemeBadge.textContent = "Off";
    }

    // Tool classes & active buttons
    const t = appState.activeTool.type;
    rootEl.classList.toggle("tool-drawing", ["rectangle", "diamond", "ellipse", "arrow", "line", "freedraw"].includes(t));
    rootEl.classList.toggle("tool-hand", t === "hand");
    rootEl.classList.toggle("tool-text", t === "text");

    document.querySelectorAll(".sb-tool-btn[data-tool]").forEach((btn) => {
      const bt = btn.getAttribute("data-tool");
      if (bt === "lock") {
        btn.classList.toggle("active", Boolean(appState.activeTool.locked));
      } else {
        btn.classList.toggle("active", bt === t);
      }
    });

    // Zoom percentage
    zoomResetBtn.textContent = `${Math.round(appState.zoom.value * 100)}%`;

    // History buttons
    syncHistoryButtons();

    // Left properties inspector
    const selected = getSelectedElements();
    if (selected.length > 0) {
      inspectorEl.classList.remove("hidden");
      const first = selected[0];
      inspectorEl.querySelectorAll("[data-prop]").forEach((btn) => {
        const prop = btn.getAttribute("data-prop");
        const val = btn.getAttribute("data-value");
        btn.classList.toggle("active", String(first[prop]) === String(val));
      });
      opacitySlider.value = String(first.opacity ?? 100);
      hintViewerEl.textContent = "Drag handles to move or update style properties on the left panel";
    } else {
      inspectorEl.classList.add("hidden");
      hintViewerEl.textContent = "To move canvas, hold mouse wheel or spacebar while dragging, or use the hand tool";
    }
  }

  function setActiveTool(type) {
    appState.activeTool = {
      ...appState.activeTool,
      lastActiveTool: appState.activeTool.type,
      type,
    };
    if (type !== "selection") {
      appState.selectedElementIds = {};
    }
    syncUI();
    render();
  }

  function setTheme(theme) {
    appState.theme = theme === "dark" ? "dark" : "light";
    persistToLocalStorage();
    syncUI();
    render();
  }

  function applyZoom(nextZoomVal) {
    const clamped = Math.round(Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, nextZoomVal)) * 1000) / 1000;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const currentZoom = appState.zoom.value;
    const baseScrollX = appState.scrollX + (cx - cx / currentZoom);
    const baseScrollY = appState.scrollY + (cy - cy / currentZoom);
    appState.scrollX = baseScrollX - (cx - cx / clamped);
    appState.scrollY = baseScrollY - (cy - cy / clamped);
    appState.zoom = { value: clamped };
    persistToLocalStorage();
    syncUI();
    render();
  }

  function mutateSelectedProperty(prop, rawValue) {
    const selected = getSelectedElements();
    if (!selected.length) return;
    const prevSnap = snapshotScene();
    const val = prop === "strokeWidth" || prop === "roughness" || prop === "opacity" ? Number(rawValue) : rawValue;
    const selSet = new Set(selected.map((e) => e.id));
    elements = elements.map((el) => {
      if (!selSet.has(el.id)) return el;
      return {
        ...el,
        [prop]: val,
        version: el.version + 1,
        versionNonce: randomInt(),
        updated: Date.now(),
      };
    });
    if (prop === "strokeColor") appState.currentItemStrokeColor = val;
    if (prop === "backgroundColor") appState.currentItemBackgroundColor = val;
    if (prop === "roughness") appState.currentItemRoughness = val;
    if (prop === "strokeWidth") appState.currentItemStrokeWidth = val;
    pushHistory(prevSnap);
    persistToLocalStorage();
    syncUI();
    render();
  }

  // --- Text Editor Commit ---
  let textEditorOpenedAt = 0;

  function openTextEditor(sx, sy) {
    activeTextCoords = { sx, sy };
    textEditorOpenedAt = Date.now();
    const vp = sceneToViewport(sx, sy);
    textEditorEl.value = "";
    textEditorEl.style.left = `${vp.x}px`;
    textEditorEl.style.top = `${vp.y}px`;
    textEditorEl.style.fontSize = `${appState.currentItemFontSize * appState.zoom.value}px`;
    textEditorEl.classList.remove("hidden");
    textEditorEl.focus();
    requestAnimationFrame(() => {
      if (!textEditorEl.classList.contains("hidden")) {
        textEditorEl.focus();
      }
    });
  }

  function commitTextEditor() {
    if (textEditorEl.classList.contains("hidden") || !activeTextCoords) return;
    const content = textEditorEl.value;
    const coords = activeTextCoords;
    activeTextCoords = null;
    textEditorEl.classList.add("hidden");
    textEditorEl.value = "";

    if (content.trim().length > 0) {
      const prevSnap = snapshotScene();
      const fontSize = appState.currentItemFontSize || 20;
      ctx.save();
      ctx.font = `${fontSize}px "Comic Sans MS", "Chalkboard SE", "Segoe Print", cursive, sans-serif`;
      const lines = content.split("\n");
      const width = Math.max(...lines.map((l) => ctx.measureText(l).width), 20);
      const height = Math.round(lines.length * fontSize * 1.25);
      ctx.restore();

      const el = normalizeElement({
        type: "text",
        x: coords.sx,
        y: coords.sy,
        width: Math.round(width * 100) / 100,
        height,
        text: content,
        originalText: content,
        fontSize,
        fontFamily: appState.currentItemFontFamily || 5,
        strokeColor: appState.currentItemStrokeColor,
        backgroundColor: "transparent",
        roughness: appState.currentItemRoughness,
        strokeWidth: appState.currentItemStrokeWidth,
        opacity: appState.currentItemOpacity,
      });
      elements.push(el);
      pushHistory(prevSnap);
      appState.selectedElementIds = { [el.id]: true };
      if (!appState.activeTool.locked) {
        appState.activeTool.type = "selection";
      }
      persistToLocalStorage();
    } else if (!appState.activeTool.locked) {
      appState.activeTool.type = "selection";
    }
    syncUI();
    render();
  }

  // --- Export / Import (.excalidraw v2 JSON) ---
  function exportExcalidrawJSON() {
    const active = getNonDeletedElements();
    const payload = {
      type: "excalidraw",
      version: 2,
      source: "sketchboard-cr",
      elements: deepClone(active),
      appState: {
        gridSize: appState.gridSize,
        gridStep: appState.gridStep,
        gridModeEnabled: appState.gridModeEnabled,
        viewBackgroundColor: appState.viewBackgroundColor,
      },
      files: {},
    };
    return JSON.stringify(payload, null, 2);
  }

  function importExcalidrawJSON(jsonInput) {
    const parsed = typeof jsonInput === "string" ? JSON.parse(jsonInput) : jsonInput;
    if (!parsed || parsed.type !== "excalidraw" || !Array.isArray(parsed.elements)) {
      throw new Error("Invalid .excalidraw v2 JSON payload");
    }
    const prevSnap = snapshotScene();
    elements = parsed.elements.map(normalizeElement);
    if (parsed.appState && typeof parsed.appState === "object") {
      if (parsed.appState.viewBackgroundColor) {
        appState.viewBackgroundColor = parsed.appState.viewBackgroundColor;
      }
      if (parsed.appState.gridSize !== undefined) {
        appState.gridSize = parsed.appState.gridSize;
      }
    }
    appState.selectedElementIds = {};
    pushHistory(prevSnap);
    persistToLocalStorage();
    syncUI();
    render();
    return { elements: deepClone(elements), appState: deepClone(appState) };
  }

  // --- Pointer Events on Canvas ---
  canvas.addEventListener("pointerdown", (e) => {
    if (!menuDropdown.classList.contains("hidden")) {
      menuDropdown.classList.add("hidden");
    }
    if (!textEditorEl.classList.contains("hidden")) {
      commitTextEditor();
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const vx = e.clientX - rect.left;
    const vy = e.clientY - rect.top;
    const pt = viewportToScene(vx, vy);
    const tool = appState.activeTool.type;

    if (tool === "hand" || e.button === 1) {
      interaction = {
        mode: "pan",
        startVx: vx,
        startVy: vy,
        origScrollX: appState.scrollX,
        origScrollY: appState.scrollY,
      };
      return;
    }

    if (tool === "text") {
      e.preventDefault();
      openTextEditor(pt.x, pt.y);
      return;
    }

    if (tool === "eraser") {
      const hit = hitTestElement(pt.x, pt.y);
      if (hit) {
        const prevSnap = snapshotScene();
        elements = elements.filter((el) => el.id !== hit.id);
        appState.selectedElementIds = {};
        pushHistory(prevSnap);
        persistToLocalStorage();
        syncUI();
        render();
      }
      return;
    }

    if (tool === "selection") {
      const hit = hitTestElement(pt.x, pt.y);
      if (hit) {
        appState.selectedElementIds = { [hit.id]: true };
        interaction = {
          mode: "move",
          elementId: hit.id,
          startSx: pt.x,
          startSy: pt.y,
          origX: hit.x,
          origY: hit.y,
          prevSnap: snapshotScene(),
          moved: false,
        };
      } else {
        appState.selectedElementIds = {};
        interaction = null;
      }
      syncUI();
      render();
      return;
    }

    // Drawing tools: rectangle, diamond, ellipse, arrow, line, freedraw
    const prevSnap = snapshotScene();
    const newEl = normalizeElement({
      type: tool,
      x: pt.x,
      y: pt.y,
      width: 0,
      height: 0,
      strokeColor: appState.currentItemStrokeColor,
      backgroundColor: appState.currentItemBackgroundColor,
      fillStyle: appState.currentItemFillStyle,
      strokeWidth: appState.currentItemStrokeWidth,
      strokeStyle: appState.currentItemStrokeStyle,
      roughness: appState.currentItemRoughness,
      opacity: appState.currentItemOpacity,
      points: tool === "arrow" || tool === "line" ? [[0, 0], [0, 0]] : tool === "freedraw" ? [[0, 0]] : undefined,
      endArrowhead: tool === "arrow" ? "arrow" : null,
    });
    elements.push(newEl);
    interaction = {
      mode: "draw",
      tool,
      elementId: newEl.id,
      startSx: pt.x,
      startSy: pt.y,
      prevSnap,
    };
    render();
  });

  window.addEventListener("pointermove", (e) => {
    if (!interaction) return;
    const rect = canvas.getBoundingClientRect();
    const vx = e.clientX - rect.left;
    const vy = e.clientY - rect.top;

    if (interaction.mode === "pan") {
      const z = appState.zoom.value;
      appState.scrollX = interaction.origScrollX + (vx - interaction.startVx) / z;
      appState.scrollY = interaction.origScrollY + (vy - interaction.startVy) / z;
      render();
      return;
    }

    const pt = viewportToScene(vx, vy);
    const el = elements.find((item) => item.id === interaction.elementId);
    if (!el) return;

    if (interaction.mode === "move") {
      const dx = pt.x - interaction.startSx;
      const dy = pt.y - interaction.startSy;
      if (Math.abs(dx) > 1 || Math.abs(dy) > 1) {
        interaction.moved = true;
        el.x = interaction.origX + dx;
        el.y = interaction.origY + dy;
        el.version += 1;
        el.updated = Date.now();
        render();
      }
      return;
    }

    if (interaction.mode === "draw") {
      const dx = pt.x - interaction.startSx;
      const dy = pt.y - interaction.startSy;
      if (el.type === "arrow" || el.type === "line") {
        el.points = [[0, 0], [dx, dy]];
        el.width = Math.abs(dx);
        el.height = Math.abs(dy);
      } else if (el.type === "freedraw") {
        el.points.push([dx, dy]);
        const xs = el.points.map((p) => p[0]);
        const ys = el.points.map((p) => p[1]);
        el.width = Math.max(...xs) - Math.min(...xs);
        el.height = Math.max(...ys) - Math.min(...ys);
      } else {
        el.x = dx >= 0 ? interaction.startSx : pt.x;
        el.y = dy >= 0 ? interaction.startSy : pt.y;
        el.width = Math.abs(dx);
        el.height = Math.abs(dy);
      }
      el.version += 1;
      render();
    }
  });

  window.addEventListener("pointerup", () => {
    if (!interaction) return;
    const act = interaction;
    interaction = null;

    if (act.mode === "pan") {
      persistToLocalStorage();
      return;
    }

    if (act.mode === "move") {
      if (act.moved) {
        pushHistory(act.prevSnap);
        persistToLocalStorage();
      }
      syncUI();
      render();
      return;
    }

    if (act.mode === "draw") {
      const el = elements.find((item) => item.id === act.elementId);
      if (el) {
        const minDim = el.type === "arrow" || el.type === "line" ? Math.hypot(el.width, el.height) : Math.max(el.width, el.height);
        if (minDim < 3) {
          elements = elements.filter((item) => item.id !== el.id);
        } else {
          if (el.type === "arrow") {
            const startPt = [el.x + el.points[0][0], el.y + el.points[0][1]];
            const endPt = [el.x + el.points[el.points.length - 1][0], el.y + el.points[el.points.length - 1][1]];
            const startTarget = findBindingTarget(startPt[0], startPt[1], el.id);
            const endTarget = findBindingTarget(endPt[0], endPt[1], el.id);
            if (startTarget) {
              el.startBinding = { elementId: startTarget.element.id, focus: 0, gap: startTarget.gap };
              attachBindingToShape(startTarget.element, el.id);
            }
            if (endTarget) {
              el.endBinding = { elementId: endTarget.element.id, focus: 0, gap: endTarget.gap };
              attachBindingToShape(endTarget.element, el.id);
            }
          }
          el.versionNonce = randomInt();
          el.updated = Date.now();
          appState.selectedElementIds = { [el.id]: true };
          pushHistory(act.prevSnap);
          if (!appState.activeTool.locked) {
            appState.activeTool.type = "selection";
          }
          persistToLocalStorage();
        }
      }
      syncUI();
      render();
    }
  });

  // --- Event Listeners for Controls ---
  document.querySelectorAll(".sb-tool-btn[data-tool]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tool = btn.getAttribute("data-tool");
      if (tool === "lock") {
        appState.activeTool.locked = !appState.activeTool.locked;
        syncUI();
        return;
      }
      setActiveTool(tool);
    });
  });

  menuBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    menuDropdown.classList.toggle("hidden");
  });

  menuToggleDark.addEventListener("click", () => {
    setTheme(appState.theme === "dark" ? "light" : "dark");
    menuDropdown.classList.add("hidden");
  });

  toolbarThemeBtn.addEventListener("click", () => {
    setTheme(appState.theme === "dark" ? "light" : "dark");
  });

  function triggerDownloadJSON() {
    const json = exportExcalidrawJSON();
    const blob = new Blob([json], { type: "application/vnd.excalidraw+json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sketchboard-scene.excalidraw";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 500);
  }

  menuExportBtn.addEventListener("click", () => {
    triggerDownloadJSON();
    menuDropdown.classList.add("hidden");
  });

  topExportBtn.addEventListener("click", triggerDownloadJSON);

  menuImportInput.addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        importExcalidrawJSON(String(reader.result || ""));
      } catch (err) {
        console.error(err);
      }
    };
    reader.readAsText(file);
    menuDropdown.classList.add("hidden");
  });

  menuResetBtn.addEventListener("click", () => {
    const prevSnap = snapshotScene();
    elements = [];
    appState.selectedElementIds = {};
    pushHistory(prevSnap);
    persistToLocalStorage();
    syncUI();
    render();
    menuDropdown.classList.add("hidden");
  });

  inspectorEl.querySelectorAll("[data-prop]").forEach((btn) => {
    btn.addEventListener("click", () => {
      mutateSelectedProperty(btn.getAttribute("data-prop"), btn.getAttribute("data-value"));
    });
  });

  opacitySlider.addEventListener("input", () => {
    mutateSelectedProperty("opacity", opacitySlider.value);
  });

  zoomInBtn.addEventListener("click", () => applyZoom(appState.zoom.value + ZOOM_STEP));
  zoomOutBtn.addEventListener("click", () => applyZoom(appState.zoom.value - ZOOM_STEP));
  zoomResetBtn.addEventListener("click", () => applyZoom(1));
  undoBtn.addEventListener("click", undo);
  redoBtn.addEventListener("click", redo);

  textEditorEl.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      commitTextEditor();
    }
  });
  textEditorEl.addEventListener("blur", () => {
    if (Date.now() - textEditorOpenedAt < 120) {
      textEditorEl.focus();
      return;
    }
    commitTextEditor();
  });

  window.addEventListener("keydown", (e) => {
    if (document.activeElement === textEditorEl) return;
    const mod = e.metaKey || e.ctrlKey;
    if (mod && e.key.toLowerCase() === "z") {
      e.preventDefault();
      if (e.shiftKey) redo();
      else undo();
      return;
    }
    if (mod && e.key.toLowerCase() === "y") {
      e.preventDefault();
      redo();
      return;
    }
    const shortcuts = {
      "1": "selection",
      "2": "rectangle",
      "3": "diamond",
      "4": "ellipse",
      "5": "arrow",
      "6": "line",
      "7": "freedraw",
      "8": "text",
      "0": "eraser",
    };
    if (!mod && shortcuts[e.key]) {
      setActiveTool(shortcuts[e.key]);
    }
  });

  window.addEventListener("resize", () => {
    render();
  });

  // --- Public Clean-Room Programmatic API (window.__whiteboardAPI) ---
  window.__whiteboardAPI = {
    getSceneElements: () => deepClone(getNonDeletedElements()),
    getAppState: () => deepClone(appState),
    updateScene: (opts = {}) => {
      const capture = opts.captureUpdate || "NEVER";
      const prevSnap = capture === "IMMEDIATELY" ? snapshotScene() : null;
      if (Array.isArray(opts.elements)) {
        elements = opts.elements.map(normalizeElement);
      }
      if (opts.appState && typeof opts.appState === "object") {
        appState = {
          ...appState,
          ...opts.appState,
          zoom: opts.appState.zoom ? { value: opts.appState.zoom.value } : appState.zoom,
          activeTool: opts.appState.activeTool ? { ...appState.activeTool, ...opts.appState.activeTool } : appState.activeTool,
        };
      }
      if (prevSnap) {
        pushHistory(prevSnap);
      }
      persistToLocalStorage();
      syncUI();
      render();
    },
    exportExcalidrawJSON,
    importExcalidrawJSON,
    setTheme,
    undo,
    redo,
  };

  // Boot
  hydrateFromLocalStorage();
  syncUI();
  render();
})();
