import sys
from pathlib import Path

from PIL import Image, ImageOps

MIN_SIDE = 280
MAX_SIDE = 1568
EXTENSIONS = {".jpg", ".jpeg", ".png"}


def prepare(source, destination):
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original).convert("RGB")

    width, height = image.size
    scale = 1.0
    if max(width, height) > MAX_SIDE:
        scale = MAX_SIDE / max(width, height)
    if min(width, height) * scale < MIN_SIDE:
        scale = MIN_SIDE / min(width, height)
    if max(width, height) * scale > MAX_SIDE:
        scale = MAX_SIDE / max(width, height)

    new_size = (round(width * scale), round(height * scale))
    image = image.resize(new_size, Image.Resampling.LANCZOS)

    if min(new_size) < MIN_SIDE:
        padded = Image.new("RGB", (max(new_size[0], MIN_SIDE), max(new_size[1], MIN_SIDE)), "white")
        padded.paste(image, (0, 0))
        image = padded

    image.save(destination, "JPEG", quality=90)
    return (width, height), image.size


def main(source_folder, destination_folder):
    destination = Path(destination_folder)
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(source_folder).iterdir()):
        if path.suffix.lower() not in EXTENSIONS:
            continue
        before, after = prepare(path, destination / f"{path.stem}.jpg")
        print(f"{path.name:<40} {before[0]}x{before[1]} -> {after[0]}x{after[1]}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
