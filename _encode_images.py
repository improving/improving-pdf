"""Temporary helper script to base64-encode brand images. Delete after use."""
import base64
import os

IMAGE_DIR = "images"
IMAGES = {
    "HEADER_IMG": "new-header.png",
    "FOOTER_IMG": "new-footer.png",
    "H2_BACKGROUND_IMG": "h2-background.png",
    "BG_DECORATION_IMG": "bg-image.png",
}

output_lines = []
for var_name, filename in IMAGES.items():
    filepath = os.path.join(IMAGE_DIR, filename)
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    output_lines.append(f'{var_name} = "data:image/png;base64,{b64}"')
    print(f"Encoded {filename} -> {var_name} ({len(b64)} chars)")

output_path = os.path.join("assets", "base64-images.txt")
os.makedirs("assets", exist_ok=True)
with open(output_path, "w") as f:
    f.write("\n\n".join(output_lines) + "\n")

print(f"\nWritten to {output_path}")
