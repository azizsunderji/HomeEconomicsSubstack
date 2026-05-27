"""Headless render helper: loads a local HTML chart and saves PNG + inline SVG.

Usage:
    python render_chart.py <html_filename_in_outputs> [--svg]

Examples:
    python render_chart.py whymove_voronoi_nyc.html
    python render_chart.py whymove_voronoi_nyc.html --svg
"""
from __future__ import annotations
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT = Path("/Users/azizsunderji/Dropbox/Home Economics/2026_05_18_KidsLeavingCity")
OUTPUTS = PROJECT / "outputs"


def render(html_name: str, save_svg: bool = False) -> None:
    html_path = OUTPUTS / html_name
    if not html_path.exists():
        sys.exit(f"Not found: {html_path}")

    stem = html_path.stem
    png_path = OUTPUTS / f"{stem}.png"
    svg_path = OUTPUTS / f"{stem}.svg"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1300, "height": 1200}, device_scale_factor=2)
        page = ctx.new_page()
        page.goto(html_path.as_uri())
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(800)  # voronoi treemap convergence

        svg_handle = page.query_selector("svg#chart") or page.query_selector("svg")
        if svg_handle is None:
            sys.exit("No <svg> element on page.")
        bbox = svg_handle.bounding_box()
        svg_handle.screenshot(path=str(png_path))
        print(f"PNG: {png_path}  ({bbox['width']:.0f}x{bbox['height']:.0f})")

        if save_svg:
            svg_xml = page.evaluate(
                """() => {
                    const svg = document.querySelector('svg#chart') || document.querySelector('svg');
                    const clone = svg.cloneNode(true);
                    if (!clone.getAttribute('xmlns')) clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
                    return new XMLSerializer().serializeToString(clone);
                }"""
            )
            svg_path.write_text(svg_xml)
            print(f"SVG: {svg_path}")

        browser.close()


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit("Usage: python render_chart.py <html_filename_in_outputs> [--svg]")
    name = args[0]
    save_svg = "--svg" in args
    render(name, save_svg=save_svg)
