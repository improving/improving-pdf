"""Core HTML-to-PDF generation logic using Playwright's headless Chromium."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


MERMAID_TIMEOUT_MS = 10000


def _wait_for_mermaid(page) -> None:
    """Wait for all Mermaid diagrams to finish rendering.

    Checks if any .mermaid elements exist on the page. If so, waits for each
    to receive a [data-processed] attribute (set by mermaid.js after rendering),
    with a timeout fallback.
    """
    mermaid_count = page.eval_on_selector_all(
        ".mermaid", "elements => elements.length"
    )
    if mermaid_count == 0:
        return

    for i in range(mermaid_count):
        try:
            page.wait_for_selector(
                f".mermaid:nth-of-type({i + 1})[data-processed]",
                timeout=MERMAID_TIMEOUT_MS,
            )
        except Exception:
            # If a specific diagram times out, fall back to a general wait
            page.wait_for_timeout(2000)
            break


def html_to_pdf(html_path: str, pdf_path: str) -> str:
    """Convert an HTML file to PDF using headless Chromium.

    Args:
        html_path: Path to the input HTML file.
        pdf_path: Path where the output PDF will be written.

    Returns:
        The absolute path to the generated PDF file.
    """
    html_path = str(Path(html_path).resolve())
    pdf_path = str(Path(pdf_path).resolve())

    if not os.path.isfile(html_path):
        raise FileNotFoundError(f"HTML file not found: {html_path}")

    file_url = Path(html_path).as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        _wait_for_mermaid(page)
        page.pdf(
            path=pdf_path,
            format="Letter",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()

    return pdf_path
