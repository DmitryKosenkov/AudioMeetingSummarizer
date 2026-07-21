"""Usage: python -m app.exporters.docx_export <input.md> <output.docx>"""
import sys

from app.exporters.docx_export.converter import render_markdown_summary_to_docx


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m app.exporters.docx_export <input.md> <output.docx>")
        raise SystemExit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    with open(input_path, encoding="utf-8") as f:
        markdown_text = f.read()

    docx_bytes = render_markdown_summary_to_docx(markdown_text)

    with open(output_path, "wb") as f:
        f.write(docx_bytes)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
