#!/usr/bin/env python3
"""
Visual Tolerance Comparator (07) against 05_ui/screenshots baselines.
Captures the live Admin UI at 1440x900@1x using Playwright and computes
normalized pixel difference ratio against the reference screenshot.
"""
import io
import pathlib
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright


def normalized_diff_ratio(img_a: Image.Image, img_b: Image.Image) -> float:
    a = img_a.convert("RGB")
    b = img_b.convert("RGB").resize(a.size)
    diff = ImageChops.difference(a, b)
    hist = diff.histogram()
    # 3 channels * 256 bins; compute mean absolute error normalized to [0, 1]
    total_pixels = a.size[0] * a.size[1] * 3
    total_abs = 0
    for ch in range(3):
        offset = ch * 256
        for val in range(256):
            total_abs += val * hist[offset + val]
    return total_abs / (total_pixels * 255.0)


def compare_login_screen(base_url: str, reference_png: pathlib.Path) -> float:
    ref = Image.open(reference_png)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(base_url.rstrip("/") + "/_/", wait_until="networkidle")
        page.wait_for_selector("input[type='password']", timeout=10000)
        page.wait_for_timeout(400)
        live_bytes = page.screenshot(full_page=False)
        browser.close()
    live = Image.open(io.BytesIO(live_bytes))
    return normalized_diff_ratio(ref, live)
