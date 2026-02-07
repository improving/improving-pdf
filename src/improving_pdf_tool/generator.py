"""Core HTML-to-PDF generation logic using Playwright's headless Chromium."""

import importlib.resources
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


MERMAID_TIMEOUT_MS = 10000


_chromium_checked = False


def _ensure_chromium_installed() -> None:
    """Ensure Playwright's Chromium browser is installed.

    On the first call, runs 'playwright install chromium' which is
    idempotent — it's a no-op if already installed, and installs
    if missing. Subsequent calls within the same process are skipped.
    """
    global _chromium_checked
    if _chromium_checked:
        return

    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        print(
            f"Warning: Failed to verify/install Chromium: {exc}",
            file=sys.stderr,
        )

    _chromium_checked = True


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


MERMAID_SCRIPT_BLOCK = """<script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
        flowchart: { useMaxWidth: true, htmlLabels: true },
        sequence: { useMaxWidth: true }
    });
    async function renderAll() {
        for (const div of document.querySelectorAll('.mermaid:not([data-processed])')) {
            try {
                const { svg } = await mermaid.render(div.id + '-svg', div.textContent);
                div.innerHTML = svg;
                div.setAttribute('data-processed', 'true');
            } catch (e) {
                div.innerHTML = '<div style="color:red;">Diagram error: ' + e.message + '</div>';
            }
        }
    }
    renderAll();
</script>"""


def _load_template() -> str:
    """Load the HTML template from the package."""
    ref = importlib.resources.files("improving_pdf_tool").joinpath("template.html")
    return ref.read_text(encoding="utf-8")


def _render_template(html_content: str, title: str = "Document") -> str:
    """Render the branded HTML template with the given content.

    Replaces all {{PLACEHOLDER}} tokens in the template with actual values:
    brand images (base64), content, title, and optional mermaid script.
    """
    from improving_pdf_tool.assets.images import (
        BG_DECORATION_IMG,
        FOOTER_IMG,
        H2_BACKGROUND_IMG,
        HEADER_IMG,
    )

    template = _load_template()

    has_mermaid = '<div class="mermaid"' in html_content
    mermaid_script = MERMAID_SCRIPT_BLOCK if has_mermaid else ""

    result = template.replace("{{TITLE}}", title)
    result = result.replace("{{CONTENT}}", html_content)
    result = result.replace("{{HEADER_IMG}}", HEADER_IMG)
    result = result.replace("{{FOOTER_IMG}}", FOOTER_IMG)
    result = result.replace("{{H2_BACKGROUND_IMG}}", H2_BACKGROUND_IMG)
    result = result.replace("{{BG_DECORATION_IMG}}", BG_DECORATION_IMG)
    result = result.replace("{{MERMAID_SCRIPT}}", mermaid_script)

    return result


def _convert_mermaid_blocks(html: str) -> str:
    """Convert fenced mermaid code blocks to mermaid div elements.

    The markdown library renders ```mermaid blocks as
    <pre><code class="language-mermaid">...</code></pre>.
    Mermaid.js requires <div class="mermaid" id="...">...</div>.
    """
    counter = 0

    def _replace(match):
        nonlocal counter
        counter += 1
        code = match.group(1)
        # Unescape HTML entities that the markdown library may have applied
        code = code.replace("&lt;", "<").replace("&gt;", ">")
        code = code.replace("&amp;", "&").replace("&quot;", '"')
        return f'<div class="mermaid" id="mermaid-{counter}">{code}</div>'

    return re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        _replace,
        html,
        flags=re.DOTALL,
    )


def _markdown_to_html(markdown_text: str) -> str:
    """Convert Markdown text to HTML using the 'markdown' library.

    Raises ImportError if the 'markdown' package is not installed.
    """
    try:
        import markdown
    except ImportError:
        raise ImportError(
            "The 'markdown' package is required for .md input. "
            "Install it with: pip install markdown"
        )

    return markdown.markdown(
        markdown_text,
        extensions=["tables", "fenced_code", "toc"],
    )


def _apply_heading_classes(html: str) -> str:
    """Apply doc-title and doc-subtitle classes to the first H1 and first H2.

    Mirrors the heading classification logic from the original pdf-creation.html:
    - First <h1> gets class="doc-title"
    - First <h2> immediately after the first <h1> gets class="doc-subtitle"
    """
    # Add doc-title to the first h1 (may have attributes like id from toc extension)
    html = re.sub(
        r"<h1([^>]*)>(.*?)</h1>",
        r'<h1\1 class="doc-title">\2</h1>',
        html,
        count=1,
    )

    # Add doc-subtitle to the first h2 that immediately follows the doc-title h1
    html = re.sub(
        r'(<h1[^>]*class="doc-title"[^>]*>.*?</h1>\s*)<h2([^>]*)>(.*?)</h2>',
        r'\1<h2\2 class="doc-subtitle">\3</h2>',
        html,
        count=1,
        flags=re.DOTALL,
    )

    return html


def markdown_to_pdf(md_path: str, pdf_path: str) -> str:
    """Convert a Markdown file to a branded PDF.

    Reads the Markdown file, converts to HTML, injects into the branded
    template, writes a temporary HTML file, and renders to PDF.

    Args:
        md_path: Path to the input Markdown file.
        pdf_path: Path where the output PDF will be written.

    Returns:
        The absolute path to the generated PDF file.
    """
    md_path = str(Path(md_path).resolve())
    if not os.path.isfile(md_path):
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    with open(md_path, "r", encoding="utf-8") as f:
        markdown_text = f.read()

    # Strip HTML comments
    markdown_text = re.sub(r"<!--[\s\S]*?-->", "", markdown_text)

    # Convert markdown to HTML
    html_content = _markdown_to_html(markdown_text)

    # Convert fenced mermaid code blocks to mermaid div elements
    html_content = _convert_mermaid_blocks(html_content)

    # Apply heading classes (doc-title, doc-subtitle)
    html_content = _apply_heading_classes(html_content)

    # Extract title from first H1 if present
    title_match = re.search(r'<h1[^>]*>(.*?)</h1>', html_content)
    title = title_match.group(1) if title_match else "Document"

    # Render into branded template
    full_html = _render_template(html_content, title=title)

    # Write to temp file and convert to PDF
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(full_html)
        tmp_path = tmp.name

    try:
        return html_to_pdf(tmp_path, pdf_path)
    finally:
        os.unlink(tmp_path)


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

    _ensure_chromium_installed()

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
