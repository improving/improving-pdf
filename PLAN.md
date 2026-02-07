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

> **IMPLEMENTATION DISCIPLINE — READ THIS FIRST**
>
> Follow these rules strictly when executing this plan:
>
> 1. **One checkbox at a time.** Complete each `- [ ]` item individually. Do NOT combine or batch multiple checkboxes into a single action.
> 2. **Commit after every checkbox.** After completing each checkbox, stage and commit the changes with a descriptive message referencing the phase and step (e.g., `phase-1: base64-encode brand images`).
> 3. **Push after every phase.** After all checkboxes in a phase are complete and committed, push to origin.
> 4. **Self-review after every phase.** After pushing, carefully examine all code and files produced during that phase. Verify they meet the expectations described in this plan. Check for:
>    - Correctness: Does the output match what the plan describes?
>    - Completeness: Are any details from the plan missing?
>    - Consistency: Does the new code integrate properly with prior phases?
>    - Quality: Is the code clean, well-structured, and free of obvious issues?
> 5. **Fix before moving on.** If the self-review identifies any concerns, commit a follow-up fix with the message `phase-N: code review fix — <description>` and push again. Do NOT proceed to the next phase until the current phase passes review.
> 6. **Mark checkboxes as you go.** Update this file to change `- [ ]` to `- [x]` for each completed item, included in that item's commit.

### Phase 1: Prepare Brand Assets

- [x] Base64-encode all four brand images (`new-header.png`, `new-footer.png`, `h2-background.png`, `bg-image.png`) as data-URIs for self-contained output.
- [x] Store these as constants in `src/improving_pdf_tool/assets/images.py`.

### Phase 2: Build the HTML Template

Create a canonical HTML template that the SKILL instructs Claude to populate:

- [x] Create `<head>` with embedded `<style>` block: brand colors, typography, heading styles, table styles, print rules.
- [x] Add `@page { size: letter; margin: 0; }` and print-specific rules.
- [x] Wire H2 background and page decoration via base64 data-URIs.
- [x] Add conditional Mermaid CDN `<script>` tag (only when mermaid blocks are present).
- [x] Create `<body>` with print-ready structure: `<table class="print-table">` with `<thead>` header image, `<tbody>` content, fixed footer, background decoration.
- [x] Add screen preview styles (box shadow, centered page) so the file looks reasonable in a browser.
- [x] Convert all Tailwind utility classes to equivalent plain CSS.

### Phase 3: Build the Python PDF Tool

Create the core `generator.py` and `cli.py` modules:

- [x] Implement `generator.py`: accept HTML file path, launch headless Chromium via Playwright, load the HTML.
- [x] Add Mermaid wait logic: poll for `[data-processed]` attributes or use a timeout before PDF capture.
- [x] Call `page.pdf()` with `format="Letter"`, `print_background=True`, zero margins (handled by CSS).
- [x] Implement `cli.py` with argparse: `improving-pdf input.html -o output.pdf`.
- [x] Add optional `.md` input mode: convert Markdown using the embedded template, then render to PDF.
- [x] Add auto-install of Chromium on first run (`playwright install chromium` if missing).

### Phase 4: Define the SKILL Instructions

Write `skill.md` — the Claude SKILL instruction file:

- [ ] Define role: document formatter that produces branded HTML and invokes the Python tool for PDF.
- [ ] Document Markdown → HTML conversion rules:
  - [ ] Standard elements: headings, paragraphs, lists, tables, code blocks, blockquotes, HR, links, images, bold, italic.
  - [ ] First `# H1` → `<h1 class="doc-title">`.
  - [ ] First `## H2` immediately after H1 → `<h2 class="doc-subtitle">`.
  - [ ] All other `## H2` → standard section header (gradient background via CSS).
  - [ ] Mermaid fenced code blocks → `<div class="mermaid">` with unique IDs; include mermaid.js CDN + init script.
  - [ ] Strip HTML comments from Markdown.
- [ ] Document template assembly: insert converted HTML into the template.
- [ ] Document output format: save HTML to disk, invoke `improving-pdf` to produce the PDF.
- [ ] Document self-bootstrapping: check for package, `pip install` from GitHub if missing.
- [ ] Provide user-facing output guidance: path to generated PDF, optionally keep intermediate HTML.

### Phase 5: Package as Installable Python Tool

Package the tool for `pip install` from GitHub:

- [ ] Create `pyproject.toml` with metadata, `playwright` dependency, and `improving-pdf` CLI entry point.
- [ ] Create `src/improving_pdf_tool/__init__.py` with `__version__`.
- [ ] Bundle brand assets (base64 images) and HTML template as package data.
- [ ] Verify install works: `pip install git+https://github.com/improving/improving-pdf.git`.
- [ ] Verify CLI works after install: `improving-pdf input.html -o output.pdf`.
- [ ] Add self-bootstrapping logic to SKILL: `pip show improving-pdf-tool > /dev/null 2>&1 || pip install git+https://github.com/improving/improving-pdf.git`.
- [ ] Confirm Chromium auto-install triggers on first run.
- [ ] Tag initial release for reproducible installs (`pip install ...@v1.0.0`).

### Phase 6: Handle Edge Cases & Refinements

- [ ] Verify page-break rules for long documents: `page-break-inside: avoid` on paragraphs, list items, tables, code blocks; `page-break-after: avoid` on headings.
- [ ] Handle no-content fallback: SKILL prompts for Markdown if none provided.
- [ ] Handle `![alt](url)` image references in Markdown → `<img>` tags; note external URLs must be accessible.
- [ ] Optional: support TOC generation from headings if user requests.
- [ ] Ensure SKILL handles being invoked repeatedly in one conversation.

### Phase 7: Release Automation

Create the `/release` Claude command (`.windsurf/workflows/release.md`):

- [x] Create `.windsurf/workflows/release.md` with full release workflow.
- [ ] Verify workflow prompts for bump type (`major`, `minor`, `patch`).
- [ ] Verify workflow reads current version from `src/improving_pdf_tool/__init__.py`.
- [ ] Verify workflow updates version in both `__init__.py` and `pyproject.toml`.
- [ ] Verify workflow commits, tags, pushes, and creates GitHub release via `gh`.
- [ ] Verify workflow prints install command for new version.
- [ ] Verify workflow reminds to update pinned version in `skill.md` if applicable.

### Phase 8: Testing & Validation

- [ ] Create `test/sample-input.md` with the sample content from `loadSampleContent()` in the current file.
- [ ] Generate PDF from sample content and compare side-by-side with current tool's output.
- [ ] Verify header and footer appear on every printed page.
- [ ] Verify H2 gradient background renders correctly.
- [ ] Verify brand colors match (`#0054a6`, `#0097a7`).
- [ ] Verify page breaks don't split headings from their content.
- [ ] Verify Mermaid diagrams render (if present).
- [ ] Verify background decoration appears at page bottom.
- [ ] Test installed CLI: `improving-pdf test/sample-input.md -o test/result.pdf`.
- [ ] Test self-bootstrap flow: fresh venv → SKILL triggers install → generates PDF.
- [ ] Verify Playwright output matches manual Chrome Print to PDF.
- [ ] Test `/release` workflow: bump a patch version, verify tag and GitHub release are created.

---

## File Structure (Final)

```
pdf-skill/
├── .windsurf/
│   └── workflows/
│       └── release.md       # /release command — cut a new versioned release
├── PLAN.md                  # This file
├── skill.md                 # The Claude SKILL instructions
├── pyproject.toml           # Python package config + CLI entry point
├── README.md                # Setup & usage instructions for coworkers
├── src/
│   └── improving_pdf_tool/
│       ├── __init__.py      # Contains __version__
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
7. **Distribution** — Installable Python package from `pip install git+https://github.com/improving/improving-pdf.git`. The SKILL self-bootstraps by checking for the package and installing it if absent. Brand assets are bundled inside the package so coworkers need nothing beyond the `pip install`. **Decided: GitHub + pip.**
8. **Release process** — Automated via `/release` Claude command. Bumps version, commits, tags, pushes, and creates a GitHub release. Requires `gh` CLI. **Decided: Windsurf workflow.**
