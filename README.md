# Improving PDF Tool

Convert Markdown to professionally branded Improving PDF documents.

## Installation

```bash
pip install git+https://github.com/improving/improving-pdf.git
```

Or pin to a specific version:

```bash
pip install git+https://github.com/improving/improving-pdf.git@v1.0.0
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

## How It Works

1. Reads Markdown (or pre-built HTML) input.
2. Converts Markdown to HTML with Improving brand styling (colors, header/footer images, section headers).
3. Renders the HTML to PDF using headless Chromium via [Playwright](https://playwright.dev/python/).
4. Outputs a print-ready, letter-sized PDF with repeating headers/footers on every page.

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
