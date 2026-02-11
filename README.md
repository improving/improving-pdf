# Improving PDF Tool

Convert Markdown to professionally branded Improving PDF documents.

## Installation

```bash
pip install git+https://github.com/improving/improving-pdf.git
```

Or pin to a specific version:

```bash
pip install git+https://github.com/improving/improving-pdf.git@v1.1.2
```

## Usage

### From Markdown

```bash
improving-pdf document.md -o document.pdf
```

### From HTML

```bash
improving-pdf document.html -o document.pdf
```

Supported input extensions: `.md`, `.markdown`, `.txt`, `.html`, `.htm`

## Features

- **Branded styling** — Improving colors, header/footer images, and section headers applied automatically.
- **Images** — Relative image paths (e.g., `./images/diagram.png`) are resolved against the source markdown file's directory and embedded in the PDF.
- **Mermaid diagrams** — Fenced ` ```mermaid ` code blocks are pre-rendered to SVG via headless Chromium and embedded inline.
- **H2 page breaks** — Each `##` heading starts a new page in the PDF for clean section separation.
- **Repeating headers/footers** — Branded header and footer appear on every page.
- **Letter-sized output** — Print-ready PDF at US Letter dimensions with zero-margin full-bleed layout.

## How It Works

1. Reads Markdown (or pre-built HTML) input.
2. Converts Markdown to HTML using the [markdown](https://python-markdown.github.io/) library (tables, fenced code, TOC extensions).
3. Pre-renders any Mermaid diagram blocks to SVG using headless Chromium.
4. Copies referenced images into a temporary directory alongside the rendered HTML so relative paths resolve correctly.
5. Injects content into the branded Improving template (base64-embedded brand assets).
6. Renders the final HTML to PDF via [Playwright](https://playwright.dev/python/) headless Chromium (`page.pdf()`).
7. Outputs a print-ready, letter-sized PDF with repeating headers/footers on every page.

## Claude SKILL

This repository includes a Claude SKILL (`skill.md`) that instructs Claude to use this tool for producing branded PDF documents from Markdown content. The SKILL handles self-bootstrapping (installing the tool if missing) and guides Claude through the full conversion workflow.

## Development

```bash
git clone https://github.com/improving/improving-pdf.git
cd improving-pdf
pip install -e .
playwright install chromium
```

## Release

Use the `/release` workflow command to cut a new versioned release.
