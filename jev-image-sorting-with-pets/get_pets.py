import csv
import random
import shutil
import tarfile
import urllib.request
import xml.etree.ElementTree as ElementTree
from pathlib import Path

BASE_URL = "https://thor.robots.ox.ac.uk/~vgg/data/pets"
DOWNLOADS = Path("pets/downloads")
RAW = Path("pets/raw")
PHOTOS_PER_BREED = 2


def download_and_extract(name):
    archive = DOWNLOADS / name
    if not archive.exists():
        print(f"Downloading {name}")
        partial = DOWNLOADS / f"{name}.part"
        urllib.request.urlretrieve(f"{BASE_URL}/{name}", partial)
        partial.replace(archive)
    with tarfile.open(archive) as tar:
        tar.extractall(DOWNLOADS, filter="data")


def head_box(xml_path):
    root = ElementTree.parse(xml_path).getroot()
    width = float(root.find("size/width").text)
    height = float(root.find("size/height").text)
    box = root.find("object/bndbox")
    return {
        "top": float(box.find("ymin").text) / height,
        "bottom": float(box.find("ymax").text) / height,
        "left": float(box.find("xmin").text) / width,
        "right": float(box.find("xmax").text) / width,
    }


def main():
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    RAW.mkdir(parents=True, exist_ok=True)
    download_and_extract("images.tar.gz")
    download_and_extract("annotations.tar.gz")

    breeds = {}
    for line in (DOWNLOADS / "annotations" / "list.txt").read_text().splitlines():
        if line.startswith("#"):
            continue
        name, _, species, _ = line.split()
        if not (DOWNLOADS / "annotations" / "xmls" / f"{name}.xml").exists():
            continue
        breed = name.rsplit("_", 1)[0].lower()
        breeds.setdefault(breed, []).append((name, "cat" if species == "1" else "dog"))

    picker = random.Random(42)
    rows = []
    for breed, photos in sorted(breeds.items()):
        for name, species in picker.sample(photos, PHOTOS_PER_BREED):
            shutil.copy(DOWNLOADS / "images" / f"{name}.jpg", RAW / f"{name}.jpg")
            box = head_box(DOWNLOADS / "annotations" / "xmls" / f"{name}.xml")
            rows.append({"filename": f"{name}.jpg", "species": species, "breed": breed, **box})

    with open("pets/labels.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Copied {len(rows)} photos from {len(breeds)} breeds")


if __name__ == "__main__":
    main()
