"""CLI entry point for the improving-pdf tool."""

import argparse
import sys

from improving_pdf_tool.generator import html_to_pdf


def main() -> None:
    """Main CLI entry point for improving-pdf command."""
    parser = argparse.ArgumentParser(
        prog="improving-pdf",
        description="Convert HTML (or Markdown) to a branded Improving PDF document.",
    )
    parser.add_argument(
        "input",
        help="Path to the input file (.html or .md).",
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Path for the output PDF file.",
    )

    args = parser.parse_args()
    input_path: str = args.input
    output_path: str = args.output

    if input_path.endswith((".html", ".htm")):
        result = html_to_pdf(input_path, output_path)
        print(f"PDF generated: {result}")
    else:
        print(f"Error: Unsupported file type. Expected .html or .htm, got: {input_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
