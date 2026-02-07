"""Core HTML-to-PDF generation logic using Playwright's headless Chromium."""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright


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
        page.pdf(path=pdf_path)
        browser.close()

    return pdf_path
