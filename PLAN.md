# PLAN: Claude SKILL — Markdown to Branded PDF

## Goal

Create a Claude SKILL (a reusable system-prompt / instruction file) that, when given Markdown content, produces a **branded PDF document** using a standalone Python tool. Claude generates styled HTML, and a Python script powered by **Playwright** renders it to PDF via headless Chromium — no manual browser interaction required.

---

## How the Current Implementation Works

`pdf-creation.html` is a single-page browser app:

1. **Input**: User pastes or drag-drops a `.md` file into a textarea.
2. **Parsing**: `marked.js` converts Markdown → HTML client-side; `mermaid.js` renders diagrams.
3. **Styling**: CSS applies Improving brand identity:
   - CSS variables: `--improving-blue: #0054a6`, `--improving-teal: #0097a7`, `--improving-light-blue: #e8f4fc`
   - `H1` → large blue document title (`doc-title` class)
   - First `H2` immediately after `H1` → teal subtitle (`doc-subtitle` class)
   - Subsequent `H2`s → white text on a gradient background image, uppercase
   - `H3` → teal, uppercase; `H4` → dark gray
   - Tables with blue header row, alternating row stripes
   - Blockquotes with teal left border
   - Code blocks in light gray
4. **Brand images** (in `images/`):
   - `new-header.png` — full-width header graphic on every page
   - `new-footer.png` — full-width footer graphic on every page
   - `h2-background.png` — stretched behind every H2 section header
   - `bg-image.png` — tiled decorative background at page bottom (50% opacity)
5. **Print layout**: `@page` with letter size, zero margin; repeating header via `<table><thead>`, fixed-position footer, page-break avoidance rules.

---

## What the SKILL Must Do Differently

The SKILL eliminates the client-side editor and runtime Markdown parsing. **Claude performs the Markdown → HTML conversion itself**, and a **standalone Python tool** handles the HTML → PDF step automatically via Playwright's headless Chromium.

| Aspect | Current (HTML app) | SKILL + Python Tool |
|---|---|---|
| Markdown parsing | `marked.js` at runtime | Claude converts MD → HTML directly |
| Mermaid diagrams | `mermaid.js` at runtime | Playwright renders mermaid.js in headless Chromium before PDF capture |
| Editor UI | Textarea + drag-drop | Not needed — removed entirely |
| Brand images | Relative `images/` paths | Base64 data-URIs embedded inline (self-contained) |
| PDF generation | Manual: open browser → Print → Save as PDF | Automatic: Playwright `page.pdf()` in headless Chromium |
| Output | Live preview + manual print | `.pdf` file written directly to disk |

---

## Implementation Steps

### Phase 1: Prepare Brand Assets

1. **Base64-encode all four brand images** (`new-header.png`, `new-footer.png`, `h2-background.png`, `bg-image.png`) so the SKILL can reference them as data-URIs, making the output fully self-contained.
2. Store these as constants/snippets the SKILL template can inject.

### Phase 2: Build the HTML Template

Create a canonical HTML template that the SKILL instructs Claude to populate. The template includes:

1. **`<head>`** — meta tags, embedded `<style>` block with:
   - All CSS from the current file (brand colors, typography, heading styles, table styles, print rules)
   - `@page { size: letter; margin: 0; }` and print-specific rules
   - H2 background, page decoration via base64 data-URIs
   - Mermaid CDN `<script>` tag (only if the Markdown contains mermaid code blocks)
2. **`<body>`** — no editor panel; only the print-ready structure:
   - `<table class="print-table">` with `<thead>` containing the header image (for repeating header)
   - `<tbody>` containing the converted HTML content with appropriate classes
   - Fixed-position footer `<div>` with the footer image
   - Background decoration `<div>`
3. **Screen preview styles** — light styling so the file looks reasonable when opened in a browser (box shadow, centered page, etc.), not just in print.

### Phase 3: Build the Python PDF Tool

Create `generate_pdf.py` — a standalone CLI tool that takes an HTML file (or raw Markdown) and produces a PDF:

1. **Dependencies**: `playwright` (with Chromium browser installed).
2. **Core workflow**:
   - Accept input: path to an `.html` file (or optionally a `.md` file, converting it using the embedded template).
   - Launch headless Chromium via Playwright.
   - Load the HTML file (`page.goto("file:///...")`).
   - Wait for Mermaid diagrams to finish rendering (poll for `[data-processed]` attributes or use a timeout).
   - Call `page.pdf()` with options: `format="Letter"`, `print_background=True`, `margin=None` (margins handled by CSS).
   - Write the PDF to the specified output path.
   - Close the browser.
3. **CLI interface** (e.g., via `argparse`):
   ```
   python generate_pdf.py input.html -o output.pdf
   python generate_pdf.py input.md -o output.pdf   # optional: MD mode
   ```
4. **Setup script / instructions**: `pip install playwright && playwright install chromium`.

### Phase 4: Define the SKILL Instructions

Write the SKILL as a Markdown instruction file (e.g., `skill.md`) that tells Claude:

1. **Role**: "You are a document formatter. Given Markdown content, produce a single self-contained HTML file styled with Improving branding, then invoke the Python tool to generate the final PDF."
2. **Markdown → HTML conversion rules**:
   - Convert standard Markdown elements (headings, paragraphs, lists, tables, code blocks, blockquotes, horizontal rules, links, images, bold, italic).
   - First `# H1` → `<h1 class="doc-title">`.
   - First `## H2` immediately after the H1 → `<h2 class="doc-subtitle">`.
   - All other `## H2` → standard section header (gets gradient background via CSS).
   - Mermaid fenced code blocks (` ```mermaid `) → `<div class="mermaid">` with unique IDs; include mermaid.js CDN + init script.
   - Strip HTML comments from the Markdown.
3. **Template assembly**: Insert the converted HTML into the template at the content insertion point.
4. **Output format**: Save the HTML file to disk, then invoke `generate_pdf.py` to produce the PDF.
5. **User-facing output**: Provide the path to the generated PDF. Optionally keep the intermediate HTML for inspection.

### Phase 5: Package as Installable Python Tool

Package the tool so coworkers can install it from a public GitHub URL with zero manual setup. The SKILL itself handles bootstrapping.

1. **Project structure for packaging**:
   - `pyproject.toml` with metadata, dependencies (`playwright`), and a CLI entry point (e.g., `improving-pdf`).
   - Brand assets (base64-encoded images) and the HTML template bundled as **package data** so they ship with the install.
   - A `src/improving_pdf_tool/` package layout:
     ```
     src/improving_pdf_tool/
     ├── __init__.py
     ├── cli.py              # argparse entry point
     ├── generator.py         # core HTML→PDF logic
     ├── template.html        # branded HTML template
     └── assets/
         └── images.py        # base64-encoded brand image constants
     ```
2. **CLI entry point** (`improving-pdf`):
   ```
   improving-pdf input.md -o output.pdf
   improving-pdf input.html -o output.pdf
   ```
3. **Auto-install Chromium on first run**: The tool checks for Chromium and runs `playwright install chromium` automatically if missing. This can be a first-run check in `generator.py` or a `post_install` hook.
4. **Install from GitHub**:
   ```
   pip install git+https://github.com/your-org/improving-pdf-tool.git
   ```
5. **Self-bootstrapping in the SKILL**: The SKILL instructions tell Claude to check for the tool and install it before use:
   ```bash
   pip show improving-pdf-tool > /dev/null 2>&1 || pip install git+https://github.com/your-org/improving-pdf-tool.git
   ```
   In agentic environments (Windsurf, Claude Code), Claude runs this as a shell command. The SKILL treats it as a prerequisite step before generating the PDF.
6. **Versioning**: Tag releases on GitHub so installs are reproducible (`pip install git+https://...@v1.0.0`).

### Phase 6: Handle Edge Cases & Refinements

1. **Long documents**: Ensure page-break rules work. `page-break-inside: avoid` on paragraphs, list items, tables, code blocks. `page-break-after: avoid` on headings.
2. **No-content fallback**: If the user provides no Markdown, Claude should prompt for it.
3. **Image references in Markdown**: If the user's Markdown contains `![alt](url)` image references, convert them to `<img>` tags. Note in the SKILL that external image URLs must be accessible.
4. **Table of contents**: Optional — the SKILL could offer to generate a TOC from headings if the user asks.
5. **Multiple documents**: The SKILL should handle being invoked repeatedly in one conversation.

### Phase 7: Testing & Validation

1. Feed the sample content (from `loadSampleContent()` in the current file) through the SKILL + Python tool and compare the output PDF side-by-side with the current tool's output.
2. Verify:
   - Header and footer appear on every printed page
   - H2 gradient background renders correctly
   - Brand colors match (`#0054a6`, `#0097a7`)
   - Page breaks don't split headings from their content
   - Mermaid diagrams render (if present)
   - Background decoration appears at page bottom
3. Test the installed CLI: `improving-pdf test/sample-input.md -o test/result.pdf`
4. Test the self-bootstrap flow: fresh venv → SKILL triggers install → generates PDF.
5. Verify Playwright produces identical output to manual Chrome Print to PDF.

---

## File Structure (Final)

```
pdf-skill/
├── PLAN.md                  # This file
├── skill.md                 # The Claude SKILL instructions
├── pyproject.toml           # Python package config + CLI entry point
├── README.md                # Setup & usage instructions for coworkers
├── src/
│   └── improving_pdf_tool/
│       ├── __init__.py
│       ├── cli.py           # CLI entry point (improving-pdf command)
│       ├── generator.py     # Core HTML→PDF logic (Playwright)
│       ├── template.html    # Branded HTML template
│       └── assets/
│           └── images.py    # Base64-encoded brand image constants
├── images/                  # Original brand assets (source of truth)
│   ├── new-header.png
│   ├── new-footer.png
│   ├── h2-background.png
│   └── bg-image.png
└── test/
    ├── sample-input.md      # Test Markdown input
    ├── sample-output.html   # Expected HTML output for comparison
    └── sample-output.pdf    # Expected PDF output for comparison
```

---

## Key Design Decisions to Confirm

1. **Base64 images vs. external references** — Base64 makes the file self-contained but large (~80KB+ for the header image alone). Alternative: host images at a stable URL and reference them. **Recommendation: Base64** for portability, since these are small images.
2. **Mermaid support** — Playwright's headless Chromium executes JavaScript, so mermaid.js renders naturally. The Python tool waits for rendering to complete before capturing the PDF. **Recommendation: Keep mermaid.js CDN reference, only included when mermaid blocks are detected.**
3. **Tailwind CSS** — The current file loads Tailwind via CDN for utility classes (`px-10`, `py-6`, etc.). The SKILL output should replace these with plain CSS to avoid the CDN dependency. **Recommendation: Convert all Tailwind utilities to equivalent inline/embedded CSS.**
4. **Screen vs. Print styling** — The output file should look presentable when opened in a browser (not just when printed). Include a minimal screen layout that approximates the printed appearance.
5. **PDF generation engine** — Playwright with headless Chromium. Uses the same rendering engine as Chrome's Print to PDF, ensuring pixel-identical output. **Decided: Playwright.**
6. **Tool invocation model** — The SKILL instructs Claude to save the HTML to disk and then run `improving-pdf` to produce the PDF. Claude can do this via a shell command in agentic environments (Windsurf, Claude Code) or provide the user with the command to run manually.
7. **Distribution** — Installable Python package from a public GitHub URL via `pip install git+https://...`. The SKILL self-bootstraps by checking for the package and installing it if absent. Brand assets are bundled inside the package so coworkers need nothing beyond the `pip install`. **Decided: GitHub + pip.**
