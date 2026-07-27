"""Usage: python -m app.exporters.txt_export <input.txt> <output.txt>"""
import sys

from app.exporters.txt_export.converter import render_transcript_to_txt


def main() -> None:
    if len(sys.argv) != 3:
        print("Usage: python -m app.exporters.txt_export <input.txt> <output.txt>")
        raise SystemExit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    with open(input_path, encoding="utf-8") as f:
        text = f.read()

    txt_bytes = render_transcript_to_txt(text)

    with open(output_path, "wb") as f:
        f.write(txt_bytes)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
