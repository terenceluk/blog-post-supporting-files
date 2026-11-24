import csv
import json
import sys
import time
from pathlib import Path

from jev_client import ask
from pet_report import open_report, write_report

CAT_BREEDS = [
    "abyssinian", "bengal", "birman", "bombay", "british_shorthair", "egyptian_mau",
    "maine_coon", "persian", "ragdoll", "russian_blue", "siamese", "sphynx",
]
DOG_BREEDS = [
    "american_bulldog", "american_pit_bull_terrier", "basset_hound", "beagle", "boxer",
    "chihuahua", "english_cocker_spaniel", "english_setter", "german_shorthaired",
    "great_pyrenees", "havanese", "japanese_chin", "keeshond", "leonberger",
    "miniature_pinscher", "newfoundland", "pomeranian", "pug", "saint_bernard", "samoyed",
    "scottish_terrier", "shiba_inu", "staffordshire_bull_terrier", "wheaten_terrier",
    "yorkshire_terrier",
]
PREPARED = Path("pets/prepared")
LIVE_DELAY = 1.0  # seconds to pause after each photo, 0 turns it off


def breed_criteria(breeds):
    return {breed: breed.replace("_", " ").title() for breed in breeds}


def questions_for(mode):
    if mode == "breed37":
        return {
            "breed": {
                "type": "choice",
                "instructions": "Which breed is the cat or dog in `photo`?",
                "criteria": breed_criteria(CAT_BREEDS + DOG_BREEDS),
            }
        }
    if mode == "split":
        return {
            "is_cat": {"type": "noul", "instructions": "Is the animal in `photo` a cat?"},
            "cat_breed": {
                "type": "choice",
                "instructions": "Assuming the animal in `photo` is a cat, which breed is it?",
                "criteria": breed_criteria(CAT_BREEDS),
            },
            "dog_breed": {
                "type": "choice",
                "instructions": "Assuming the animal in `photo` is a dog, which breed is it?",
                "criteria": breed_criteria(DOG_BREEDS),
            },
        }
    if mode == "head":
        return {"head": {"type": "box", "instructions": "the head of the cat or dog in `photo`"}}
    raise SystemExit("Mode must be breed37, split or head")


def iou(a, b):
    """Intersection over union of two boxes expressed as 0 to 1 fractions."""
    overlap_width = max(0.0, min(a["right"], b["right"]) - max(a["left"], b["left"]))
    overlap_height = max(0.0, min(a["bottom"], b["bottom"]) - max(a["top"], b["top"]))
    overlap = overlap_width * overlap_height
    area_a = (a["right"] - a["left"]) * (a["bottom"] - a["top"])
    area_b = (b["right"] - b["left"]) * (b["bottom"] - b["top"])
    return overlap / (area_a + area_b - overlap)


def main(mode):
    questions = questions_for(mode)
    with open("pets/labels.csv", newline="") as file:
        labels = list(csv.DictReader(file))

    rows = []
    open_report(write_report(mode, rows, labels[0]["filename"], len(labels)))
    for label in labels:
        write_report(mode, rows, label["filename"], len(labels))
        result = ask(PREPARED / label["filename"], questions, image_name="photo")
        answers = result["answers"]
        row = {"filename": label["filename"], "species": label["species"], "breed": label["breed"]}

        if mode == "breed37":
            row["predicted"] = answers["breed"]["choice"]
            row["confidence"] = answers["breed"]["confidence"]
            row["correct"] = row["predicted"] == label["breed"]
        elif mode == "split":
            row["is_cat"] = answers["is_cat"]["noul"]
            picked = answers["cat_breed"] if row["is_cat"] >= 0.5 else answers["dog_breed"]
            row["species_correct"] = ("cat" if row["is_cat"] >= 0.5 else "dog") == label["species"]
            row["predicted"] = picked["choice"]
            row["confidence"] = picked["confidence"]
            row["probabilities"] = json.dumps(picked["probabilities"])
            row["correct"] = row["predicted"] == label["breed"]
        else:
            truth = {edge: float(label[edge]) for edge in ("top", "bottom", "left", "right")}
            row["iou"] = round(iou(answers["head"]["box"], truth), 3)
            row["confidence"] = answers["head"]["confidence"]
            row["correct"] = row["iou"] >= 0.5
            for edge in truth:
                row[f"box_{edge}"] = answers["head"]["box"][edge]
                row[f"label_{edge}"] = truth[edge]

        row["input_tokens"] = result["usage"]["input_tokens"]
        row["elapsed_ms"] = result["elapsed_ms"]
        rows.append(row)
        hidden = ("probabilities", "box_", "label_")
        print({key: value for key, value in row.items() if not key.startswith(hidden)})
        time.sleep(LIVE_DELAY)
    write_report(mode, rows)

    correct = sum(1 for row in rows if row["correct"])
    average_tokens = sum(row["input_tokens"] for row in rows) / len(rows)
    average_ms = sum(row["elapsed_ms"] for row in rows) / len(rows)
    print(f"\n{mode}: {correct} of {len(rows)} correct, "
          f"{average_tokens:.0f} input tokens and {average_ms:.0f} ms per request on average")
    print(f"Average confidence: {sum(row['confidence'] for row in rows) / len(rows):.2f}")
    if mode == "split":
        print(f"Species correct: {sum(row['species_correct'] for row in rows)} of {len(rows)}")
    if mode == "head":
        for name, hit in (("Hits", True), ("Misses", False)):
            scores = [row["confidence"] for row in rows if row["correct"] == hit]
            average = f"{sum(scores) / len(scores):.2f}" if scores else "n/a"
            below = sum(score < 0.6 for score in scores)
            print(f"{name}: {len(scores)} photos, average confidence {average}, {below} below 0.6")

    with open(f"pets/results-{mode}.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main(sys.argv[1])
