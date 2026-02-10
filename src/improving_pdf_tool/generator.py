"""Core HTML-to-PDF generation logic using Playwright's headless Chromium."""

import base64
import importlib.resources
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


MERMAID_CDN_URL = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"


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


def _prerender_mermaid_to_svgs(diagrams: list[str]) -> list[str]:
    """Pre-render Mermaid diagram sources to SVG strings using Playwright.

    Launches a minimal HTML page with the Mermaid CDN, calls mermaid.render()
    for each diagram, and returns the resulting SVG strings. Each SVG is cleaned
    up to remove fixed width/height attributes so it can be scaled via CSS.

    Args:
        diagrams: List of Mermaid diagram source strings.

    Returns:
        List of SVG strings, one per input diagram. On render failure, the
        corresponding entry contains an error placeholder.
    """
    if not diagrams:
        return []

    _ensure_chromium_installed()

    render_page = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head><body>
<script type="module">
import mermaid from '{MERMAID_CDN_URL}';
mermaid.initialize({{ startOnLoad: false, theme: 'default', securityLevel: 'loose',
    flowchart: {{ useMaxWidth: true, htmlLabels: true }}, sequence: {{ useMaxWidth: true }} }});
window.renderDiagram = async function(id, source) {{
    try {{
        const {{ svg }} = await mermaid.render(id, source);
        return svg;
    }} catch (e) {{
        return '<div style="color:red;">Diagram error: ' + e.message + '</div>';
    }}
}};
window.__mermaidReady = true;
</script></body></html>"""

    svgs = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(render_page)
        page.wait_for_function("() => window.__mermaidReady === true", timeout=15000)

        for i, source in enumerate(diagrams):
            svg = page.evaluate(
                "([id, src]) => window.renderDiagram(id, src)",
                [f"mermaid-pre-{i}", source],
            )
            # Clean SVG: remove fixed width/height, ensure viewBox is present
            svg = _clean_svg_for_embedding(svg)
            svgs.append(svg)

        browser.close()

    return svgs


def _clean_svg_for_embedding(svg: str) -> str:
    """Remove fixed width/height attributes from an SVG so it scales via CSS.

    Preserves the viewBox attribute for proper aspect-ratio scaling. If no
    viewBox exists, attempts to create one from the width/height values.
    """
    if not svg.strip().startswith("<svg"):
        return svg  # error placeholder, leave as-is

    # Extract width/height before removing them (for viewBox fallback)
    w_match = re.search(r'\bwidth="([\d.]+)', svg)
    h_match = re.search(r'\bheight="([\d.]+)', svg)

    # Add viewBox if missing
    if 'viewBox' not in svg and w_match and h_match:
        w, h = w_match.group(1), h_match.group(1)
        svg = svg.replace("<svg", f'<svg viewBox="0 0 {w} {h}"', 1)

    # Remove fixed width/height attributes so CSS controls sizing
    svg = re.sub(r'\s*width="[^"]*"', '', svg, count=1)
    svg = re.sub(r'\s*height="[^"]*"', '', svg, count=1)
    # Remove style width/height if present (mermaid sometimes adds these)
    svg = re.sub(r'style="[^"]*"', '', svg, count=1)

    return svg


def _load_template() -> str:
    """Load the HTML template from the package."""
    ref = importlib.resources.files("improving_pdf_tool").joinpath("template.html")
    return ref.read_text(encoding="utf-8")


def _render_template(html_content: str, title: str = "Document") -> str:
    """Render the branded HTML template with the given content.

    Replaces all {{PLACEHOLDER}} tokens in the template with actual values:
    brand images (base64), content, title, etc.
    """
    from improving_pdf_tool.assets.images import (
        BG_DECORATION_IMG,
        FOOTER_IMG,
        H2_BACKGROUND_IMG,
        HEADER_IMG,
    )

    template = _load_template()

    result = template.replace("{{TITLE}}", title)
    result = result.replace("{{YEAR}}", str(datetime.now().year))
    result = result.replace("{{CONTENT}}", html_content)
    result = result.replace("{{HEADER_IMG}}", HEADER_IMG)
    result = result.replace("{{FOOTER_IMG}}", FOOTER_IMG)
    result = result.replace("{{H2_BACKGROUND_IMG}}", H2_BACKGROUND_IMG)
    result = result.replace("{{BG_DECORATION_IMG}}", BG_DECORATION_IMG)
    result = result.replace("{{MERMAID_SCRIPT}}", "")

    return result


def _extract_mermaid_blocks(html: str) -> tuple[str, list[str]]:
    """Extract fenced mermaid code blocks from HTML, replacing with placeholders.

    The markdown library renders ```mermaid blocks as
    <pre><code class="language-mermaid">...</code></pre>.
    This function extracts the diagram source and replaces each block with a
    numbered placeholder for later substitution with rendered SVGs.

    Returns:
        A tuple of (html_with_placeholders, list_of_diagram_sources).
    """
    diagrams = []

    def _replace(match):
        code = match.group(1)
        # Unescape HTML entities that the markdown library may have applied
        code = code.replace("&lt;", "<").replace("&gt;", ">")
        code = code.replace("&amp;", "&").replace("&quot;", '"')
        idx = len(diagrams)
        diagrams.append(code)
        return f'{{{{MERMAID_PLACEHOLDER_{idx}}}}}'

    html_with_placeholders = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        _replace,
        html,
        flags=re.DOTALL,
    )

    return html_with_placeholders, diagrams


def _embed_mermaid_svgs(html: str, svgs: list[str]) -> str:
    """Replace mermaid placeholders with pre-rendered SVG images.

    Each SVG is base64-encoded and embedded as an <img> tag with sizing
    constraints to prevent overflow in both dimensions.
    """
    for i, svg in enumerate(svgs):
        placeholder = f'{{{{MERMAID_PLACEHOLDER_{i}}}}}'
        svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        img_tag = (
            f'<img class="mermaid-img" '
            f'src="data:image/svg+xml;base64,{svg_b64}" '
            f'alt="Diagram {i + 1}">'
        )
        html = html.replace(placeholder, img_tag)
    return html


def _wrap_mermaid_with_headings(html: str) -> str:
    """Wrap each mermaid <img> and its immediately preceding context in a .mermaid-figure.

    This keeps the heading/label and diagram together as a single unit for
    page-break-inside: avoid, preventing orphaned headings or labels.

    Splits the HTML into block-level chunks, then for each mermaid img chunk,
    looks at the immediately preceding chunk and wraps them together if it is
    a heading or paragraph.
    """
    # Split HTML into block-level chunks while preserving separators.
    # This splits on boundaries between block elements (before opening tags
    # of h1-h6, p, div, ul, ol, table, blockquote, hr, pre, img).
    block_tag = re.compile(
        r'(?=<(?:h[1-6]|p|div|ul|ol|table|blockquote|hr|pre|img)[\s>])'
    )
    chunks = block_tag.split(html)

    # Process chunks: find mermaid img chunks and merge with preceding context
    result = []
    i = 0
    while i < len(chunks):
        chunk = chunks[i]

        if '<img class="mermaid-img"' in chunk:
            # Look back at the previous chunk to see if it should be wrapped together
            if result:
                prev = result[-1]
                prev_stripped = prev.strip()
                # Wrap with preceding chunk if it's a heading or a short <p> (label)
                is_heading = bool(re.match(r'<h[1-6][\s>]', prev_stripped))
                is_paragraph = bool(re.match(r'<p[\s>]', prev_stripped))

                if is_heading or is_paragraph:
                    result.pop()
                    result.append(
                        f'<div class="mermaid-figure">{prev}{chunk}</div>'
                    )
                else:
                    result.append(
                        f'<div class="mermaid-figure">{chunk}</div>'
                    )
            else:
                result.append(f'<div class="mermaid-figure">{chunk}</div>')
        else:
            result.append(chunk)

        i += 1

    return ''.join(result)


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

    # Extract mermaid blocks and pre-render to SVG
    html_content, mermaid_sources = _extract_mermaid_blocks(html_content)
    if mermaid_sources:
        svgs = _prerender_mermaid_to_svgs(mermaid_sources)
        html_content = _embed_mermaid_svgs(html_content, svgs)

    # Apply heading classes (doc-title, doc-subtitle)
    html_content = _apply_heading_classes(html_content)

    # Wrap mermaid diagrams with their headings for page-break control
    if mermaid_sources:
        html_content = _wrap_mermaid_with_headings(html_content)

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
        page.pdf(
            path=pdf_path,
            format="Letter",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()

    return pdf_path
