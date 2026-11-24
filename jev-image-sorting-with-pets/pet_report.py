import html
import json
import time
import webbrowser
from pathlib import Path

TITLES = {
    "breed37": "All 37 breeds in one question",
    "split": "Breeds split by species",
    "head": "Head boxes",
}
HARD_PAIRS = [
    ("american_pit_bull_terrier", "staffordshire_bull_terrier"),
    ("ragdoll", "birman"),
]
EDGES = ("top", "bottom", "left", "right")
STYLE = """
* { box-sizing: border-box; }
body { margin: 0; background: #f4f5f7; color: #1f2933; font: 13px "Segoe UI", system-ui, sans-serif; }
header { display: flex; flex-wrap: wrap; align-items: center; gap: 14px 28px; padding: 16px 28px; background: #1f2933; color: #fff; }
h1 { margin: 0; font-size: 20px; }
h2 { margin: 24px 0 10px; font-size: 16px; }
.now { display: flex; align-items: center; gap: 12px; color: #9fb3c8; }
.now img { width: 64px; height: 64px; object-fit: cover; border: 2px solid #f59f00; border-radius: 6px; }
.stats { display: flex; gap: 10px; margin-left: auto; }
.stats div { min-width: 100px; padding: 6px 12px; border-radius: 8px; background: #334e68; text-align: center; }
.stats b { display: block; font-size: 22px; }
.progress { height: 4px; background: #334e68; }
.progress i { display: block; height: 100%; background: #f59f00; }
main { padding: 12px 28px 28px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; align-items: start; }
.pair { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; max-width: 1100px; margin-bottom: 12px; }
.single { max-width: 520px; }
.card { overflow: hidden; border-left: 5px solid #adb5bd; border-radius: 8px; background: #fff; }
.card.good { border-left-color: #2f9e44; }
.card.bad { border-left-color: #e03131; }
.card.newest { outline: 3px solid #f59f00; }
.thumb { display: block; width: 100%; height: 170px; object-fit: contain; background: #e9ecef; }
.boxed { position: relative; }
.boxed img { display: block; width: 100%; height: auto; }
.box { position: absolute; border: 3px solid; }
.box.jev { border-color: #ff2d95; }
.box.label { border-color: #00c2ff; border-style: dashed; }
.meta { padding: 8px 10px; line-height: 1.5; overflow-wrap: anywhere; }
.bar { height: 5px; margin: 3px 0 6px; background: #e9ecef; }
.bar i { display: block; height: 100%; background: #1c7ed6; }
"""


def name_of(breed):
    return html.escape(breed.replace("_", " ").title())


def bar(text, value):
    return f'<div>{text} {value:.2f}</div><div class="bar"><i style="width:{value * 100:.1f}%"></i></div>'


def box_overlay(box, kind):
    return (f'<span class="box {kind}" style="left:{box["left"] * 100:.2f}%;top:{box["top"] * 100:.2f}%;'
            f'width:{(box["right"] - box["left"]) * 100:.2f}%;'
            f'height:{(box["bottom"] - box["top"]) * 100:.2f}%"></span>')


def card(mode, row, newest=False, pair=None):
    source = "prepared/" + html.escape(row["filename"])
    mark = "&#10004;" if row["correct"] else "&#10008;"
    if mode == "head":
        boxes = box_overlay({edge: row[f"label_{edge}"] for edge in EDGES}, "label")
        boxes += box_overlay({edge: row[f"box_{edge}"] for edge in EDGES}, "jev")
        picture = f'<div class="boxed"><img src="{source}">{boxes}</div>'
        details = f"<b>{mark} IoU {row['iou']:.3f}</b><div>{name_of(row['breed'])}</div>"
    else:
        picture = f'<img class="thumb" src="{source}">'
        details = f"<b>{mark} {name_of(row['predicted'])}</b><div>Expected {name_of(row['breed'])}</div>"
        if mode == "split":
            species = "Cat" if row["is_cat"] >= 0.5 else "Dog"
            wrong = "" if row["species_correct"] else " (wrong species)"
            details += f"<div>{species}{wrong}, is_cat {row['is_cat']:.2f}</div>"
    details += bar("Confidence", row["confidence"])
    if pair:
        probabilities = json.loads(row["probabilities"])
        details += "".join(bar(name_of(breed), probabilities.get(breed, 0.0)) for breed in pair)
    details += f"<small>{html.escape(row['filename'])}</small>"
    classes = ("good" if row["correct"] else "bad") + (" newest" if newest else "")
    return f'<div class="card {classes}">{picture}<div class="meta">{details}</div></div>'


def save_page(path, title, header, body, running=False, percent=100):
    refresh = '<meta http-equiv="refresh" content="1">' if running else ""
    page = (f'<!doctype html><html><head><meta charset="utf-8">{refresh}<title>{title}</title>'
            f"<style>{STYLE}</style></head><body><header><h1>{title}</h1>{header}</header>"
            f'<div class="progress"><i style="width:{percent:.0f}%"></i></div><main>{body}</main></body></html>')
    temporary = path.with_suffix(".tmp")
    temporary.write_text(page, encoding="utf-8")
    # Windows refuses to replace a file while the browser is reading it
    for _ in range(100):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            time.sleep(0.05)
    print(f"Could not update {path}")


def write_report(mode, rows, current=None, total=0):
    """Write pets/results-<mode>.html, which refreshes every second until the run finishes."""
    running = current is not None
    if running:
        status = (f'<div class="now"><img src="prepared/{html.escape(current)}">'
                  f"<span>Asking Jev about photo {len(rows) + 1} of {total}<br>{html.escape(current)}</span></div>")
    else:
        status = '<div class="now">Finished</div>'

    def average(key):
        return f"{sum(row[key] for row in rows) / len(rows):.2f}" if rows else "-"

    stats = [(len(rows), "photos done"),
             (sum(row["correct"] for row in rows), "hits" if mode == "head" else "correct"),
             (average("confidence"), "average confidence")]
    if mode == "split":
        stats.append((sum(row["species_correct"] for row in rows), "species correct"))
    if mode == "head":
        stats.append((average("iou"), "average IoU"))
    tiles = "".join(f"<div><b>{value}</b>{label}</div>" for value, label in stats)

    newest = rows[-1] if running and rows else None
    ordered = rows[::-1] if running else rows
    body = "<p>A green edge is a correct answer and a red edge is a wrong one.</p>"
    if mode == "head":
        body = ("<p>The solid pink box is Jev's answer and the dashed blue box is the dataset's label. "
                "A green edge is an IoU of 0.5 or higher.</p>")
        if not running:
            ordered = sorted(rows, key=lambda row: row["iou"], reverse=True)
        groups = [("Newest first" if running else "Highest to lowest IoU", ordered)]
    else:
        if mode == "split" and not running:
            body += "<h2>Hard pairs</h2>"
            for pair in HARD_PAIRS:
                cards = [card(mode, row, pair=pair) for breed in pair for row in rows if row["breed"] == breed]
                body += f'<div class="pair">{"".join(cards)}</div>'
        if running:
            groups = [("Newest first", ordered)]
        else:
            groups = [("Cats", [row for row in rows if row["species"] == "cat"]),
                      ("Dogs", [row for row in rows if row["species"] == "dog"])]
    for heading, group in groups:
        cards = "".join(card(mode, row, row is newest) for row in group)
        body += f'<h2>{heading}</h2><div class="grid">{cards}</div>'

    path = Path(f"pets/results-{mode}.html")
    percent = len(rows) / total * 100 if total else 100
    save_page(path, TITLES[mode], f'{status}<div class="stats">{tiles}</div>', body, running, percent)
    return path


def write_presence_report(image_path, answers):
    """Write a page with the Box answer drawn on the image next to the presence answer."""
    image = Path(image_path).resolve()
    present = answers["has_animal"]["noul"]
    if present >= 0.7:
        verdict, edge = "An animal is present so the box can be used", "good"
    elif present <= 0.3:
        verdict, edge = "No animal is present so the box should be discarded", "bad"
    else:
        verdict, edge = "The presence answer is unclear so the box needs a review", ""
    body = (f'<div class="single card {edge}"><div class="boxed"><img src="{image.as_uri()}">'
            f'{box_overlay(answers["head"]["box"], "jev")}</div><div class="meta"><b>{verdict}</b>'
            f'{bar("has_animal", present)}{bar("Box confidence", answers["head"]["confidence"])}'
            f"<small>{html.escape(image.name)}</small></div></div>")
    path = Path(f"pets/presence-{image.stem}.html")
    save_page(path, "Box presence check", "", body)
    return path


def open_report(path):
    webbrowser.open(path.resolve().as_uri())
