---
name: improving-pdf
description: >
  Converts Markdown content to professionally styled, Improving-branded PDF
  documents using the improving-pdf CLI tool. Use when the user wants to
  generate a branded PDF, create an Improving document, or format Markdown
  as a professional PDF.
allowed-tools: Bash Read Write WebFetch
metadata:
  author: improving
  version: "1.2.1"
---

# Improving PDF Document Formatter

You are a document formatter for **Improving**. Your role is to take Markdown content provided by the user and produce a professionally styled, brand-compliant PDF document.

## Workflow

1. Accept Markdown content from the user (pasted directly or as a `.md` file).
   - **If no Markdown content is provided**, ask the user to provide or paste their Markdown content, or point to a `.md` file on disk. Do not proceed without content.
2. Save the Markdown to a `.md` file on disk.
3. Invoke the `improving-pdf` CLI tool to render the Markdown into a branded PDF.
4. Provide the user with the path to the generated PDF.

## Markdown → HTML Conversion Rules

The `improving-pdf` tool converts Markdown to HTML automatically. It handles all standard Markdown elements (headings, paragraphs, bold, italic, lists, tables, code blocks, blockquotes, horizontal rules, links). The following rules cover brand-specific behavior you need to be aware of:

### Images

Use standard Markdown image syntax: `![alt](url)`. External image URLs must be accessible from the machine running `improving-pdf`. For local images, use absolute file paths or paths relative to the Markdown file.

### Heading Classification

The tool applies special CSS classes to the first two headings to create the document title block:

1. **First `# H1`** → `<h1 class="doc-title">` — renders as a large blue document title.
2. **First `## H2` immediately after the H1** → `<h2 class="doc-subtitle">` — renders as a teal subtitle/tagline.
3. **All other `## H2`** → plain `<h2>` — renders as white text on a blue gradient background, uppercase, with a page break before each.

### Mermaid Diagrams

Leave mermaid code blocks as standard ` ```mermaid ` fenced blocks in the Markdown. The tool handles everything automatically: extracts each block, pre-renders to SVG via Playwright, embeds as a sized `<img>` tag, and wraps with its preceding heading to prevent page breaks between them.

### HTML Comment Stripping

Strip all HTML comments (`<!-- ... -->`) from the Markdown before saving. These are authoring notes and should not appear in the output.

### Table of Contents (Optional)

If the user requests a table of contents, insert `[TOC]` on its own line in the Markdown. The tool's Markdown processor (via the `toc` extension) will replace it with a generated table of contents. Only include this if the user explicitly requests it.

## Output Format

### Option A: Direct `.md` Input (Preferred)

Save the user's Markdown content to a `.md` file, then invoke the tool directly:

```bash
improving-pdf document.md -o document.pdf
```

The tool handles everything: Markdown → HTML conversion, template assembly, brand image injection, mermaid rendering, and PDF generation.

### Option B: Manual `.html` Input

If you need more control (e.g., custom HTML modifications), produce the full branded HTML file yourself, save it as `.html`, then invoke:

```bash
improving-pdf document.html -o document.pdf
```

When producing HTML manually, insert the converted content into the branded template by replacing these placeholders:

| Placeholder | Value |
|---|---|
| `{{TITLE}}` | Document title — extracted from the first `<h1>` text, or `"Document"` as fallback. |
| `{{CONTENT}}` | The full converted HTML content. |
| `{{HEADER_IMG}}` | Base64 data-URI for the Improving header image. |
| `{{FOOTER_IMG}}` | Base64 data-URI for the Improving footer image. |
| `{{H2_BACKGROUND_IMG}}` | Base64 data-URI for the H2 section header background. |
| `{{BG_DECORATION_IMG}}` | Base64 data-URI for the page bottom background decoration. |
| `{{MERMAID_SCRIPT}}` | Reserved placeholder (always empty). |

All brand image data-URIs are bundled inside the `improving-pdf-tool` package and injected automatically when using Option A.

## Prerequisites & Self-Bootstrapping

Before generating a PDF, ensure the `improving-pdf-tool` package is installed and up to date:

```bash
pip install --upgrade git+https://github.com/improving/improving-pdf.git
```

This is idempotent — it installs the package if missing, or upgrades to the latest version if already installed. Chromium is installed automatically via Playwright on first run.

## User-Facing Output Guidance

After generating the PDF, provide the user with:

1. **The path to the generated PDF** — e.g., "Your branded PDF has been saved to `C:\Users\...\document.pdf`."
2. **A brief summary** of what was produced — e.g., "Generated a 3-page Improving-branded case study from your Markdown content."
3. **Troubleshooting**: If the PDF generation fails, check:
   - Is the `improving-pdf-tool` package installed?
   - Does the Markdown contain syntax errors?
   - Are external image URLs accessible?
   - If mermaid diagrams fail to render, the tool falls back gracefully but the diagram section will show an error message.

## Multiple Documents in One Conversation

This SKILL can be invoked multiple times in a single conversation. Each invocation is independent:

- You do **not** need to re-check the tool installation after the first successful check.
- Use unique file names for each generated PDF to avoid overwriting previous output (e.g., `case-study.pdf`, `proposal.pdf`).
- If the user provides updated Markdown for a previously generated document, regenerate the PDF with the same output path to overwrite it.
