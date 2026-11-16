import csv
import html
import shutil
import time
import webbrowser
from pathlib import Path

from jev_client import ask

CATEGORIES = {
    "meals": "Restaurants, cafes, bars, takeout, and food delivery",
    "groceries": "Supermarkets and grocery stores where most items are food to take home",
    "office_supplies": "Stationery, paper, ink, toner, pens, and small desk items",
    "office_equipment": "Computers, monitors, printers, phones, furniture, and other electronics",
    "travel_transport": "Taxis, rideshare, parking, public transit, trains, and airfare",
    "fuel": "Gasoline or diesel purchased at a gas station",
    "lodging": "Hotels, motels, and short-term rentals",
    "other": "A receipt that does not fit any of the other categories",
    "not_a_receipt": "The image is not a receipt, such as a business card, boarding pass or photo",
}

QUESTIONS = {
    "category": {
        "type": "choice",
        "instructions": "Which expense category does the purchase shown in `receipt` belong to?",
        "criteria": CATEGORIES,
    },
    "sideways": {
        "type": "noul",
        "instructions": "Is the text on `receipt` rotated sideways or upside down instead of reading normally?",
    },
}

CONFIDENCE_THRESHOLD = 0.6
LIVE_DELAY = 1.0  # seconds to pause after each receipt so the live page can be followed, 0 turns it off
PREPARED = Path("receipts/prepared")
SORTED = Path("receipts/sorted")
REPORT = Path("receipts/results.html")
COLUMNS = list(CATEGORIES) + ["_review"]


def write_report(rows, current=None, total=0):
    """Write receipts/results.html, which refreshes itself every second while sorting is running."""
    running = current is not None
    done = len(rows)
    correct = sum(1 for row in rows if row["choice"] == row["expected"])
    reviewed = sum(1 for row in rows if row["folder"] == "_review")
    percent = done / total * 100 if total else 100

    columns = []
    for folder in COLUMNS:
        cards = []
        for row in [row for row in rows if row["folder"] == folder]:
            match = row["choice"] == row["expected"]
            classes = "card correct" if match else "card wrong"
            if running and row is rows[-1]:
                classes += " newest"
            mark = "&#10004;" if match else "&#10008;"
            sideways = "<span class='flag'>sideways</span>" if row["sideways"] >= 0.5 else ""
            cards.append(f"""
          <div class="{classes}">
            <div class="thumb"><img src="prepared/{html.escape(row['filename'])}" alt=""></div>
            <div class="meta">
              <div class="pick">{mark} {html.escape(row['choice'])}</div>
              <div class="bar"><span style="width: {row['confidence'] * 100:.0f}%"></span></div>
              <div class="small">confidence {row['confidence']:.2f}, expected {html.escape(row['expected'])} {sideways}</div>
            </div>
          </div>""")
        title = "Sent to review" if folder == "_review" else folder.replace("_", " ")
        extra = " review" if folder == "_review" else ""
        content = "".join(cards) or "<p class='empty'>Nothing yet</p>"
        columns.append(f"""
        <section class="column{extra}">
          <h2>{html.escape(title)}<span class="count">{len(cards)}</span></h2>{content}
        </section>""")

    if running:
        refresh = '<meta http-equiv="refresh" content="1">'
        status = f"""
      <div class="now">
        <img src="prepared/{html.escape(current.name)}" alt="">
        <div>
          <div class="label"><span class="pulse"></span>Asking Jev</div>
          <div class="file">{html.escape(current.name)}</div>
          <div class="hint">Receipt {done + 1} of {total}</div>
        </div>
      </div>"""
    else:
        refresh = ""
        status = """
      <div class="now">
        <div>
          <div class="label">Finished</div>
          <div class="file">All receipts sorted</div>
        </div>
      </div>"""

    page = f"""<!doctype html>
<html><head><meta charset="utf-8">{refresh}<title>Jev receipt sorting</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ background: #f4f5f7; }}
  body {{ margin: 0; font-family: "Segoe UI", system-ui, sans-serif; color: #1f2933; }}
  header {{ background: #1f2933; color: #fff; padding: 18px 32px; display: flex; align-items: center; gap: 32px; flex-wrap: wrap; }}
  header h1 {{ font-size: 20px; font-weight: 600; margin: 0; }}
  .now {{ display: flex; align-items: center; gap: 14px; }}
  .now img {{ width: 56px; height: 72px; object-fit: cover; border-radius: 6px; border: 2px solid #f59f00; background: #fff; }}
  .label {{ display: flex; align-items: center; gap: 6px; font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: #9fb3c8; }}
  .file {{ font-weight: 600; }}
  .hint {{ font-size: 12px; color: #9fb3c8; }}
  .pulse {{ width: 8px; height: 8px; border-radius: 50%; background: #f59f00; animation: pulse 1s infinite; }}
  @keyframes pulse {{ 50% {{ opacity: 0.2; }} }}
  .stats {{ display: flex; gap: 10px; margin-left: auto; }}
  .stats div {{ min-width: 96px; padding: 8px 14px; border-radius: 8px; background: rgba(255, 255, 255, 0.08); text-align: center; }}
  .stats b {{ display: block; font-size: 22px; }}
  .stats span {{ font-size: 11px; color: #9fb3c8; }}
  .progress {{ height: 4px; background: #334e68; }}
  .progress span {{ display: block; height: 100%; background: #f59f00; }}
  main {{ padding: 24px 32px; }}
  .legend {{ margin: 0 0 16px; font-size: 13px; color: #6b7785; }}
  .board {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 14px; align-items: start; }}
  .column {{ min-height: 140px; padding: 10px; border-radius: 10px; background: #e9ecf0; }}
  .column.review {{ background: #fff4e6; }}
  .column.review h2 {{ text-transform: none; }}
  .column h2 {{ display: flex; justify-content: space-between; margin: 2px 4px 10px; font-size: 13px; text-transform: capitalize; }}
  .count {{ padding: 0 8px; border-radius: 10px; background: #fff; font-size: 12px; color: #6b7785; }}
  .card {{ margin-bottom: 10px; overflow: hidden; border-radius: 8px; border-left: 4px solid #ced4da; background: #fff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08); }}
  .card.correct {{ border-left-color: #2f9e44; }}
  .card.wrong {{ border-left-color: #e03131; }}
  .card.newest {{ box-shadow: 0 0 0 3px #f59f00; }}
  .thumb {{ display: flex; align-items: center; justify-content: center; height: 120px; background: #f1f3f5; }}
  .thumb img {{ max-width: 100%; max-height: 120px; }}
  .meta {{ padding: 8px 10px; }}
  .pick {{ font-size: 13px; font-weight: 600; }}
  .correct .pick {{ color: #2f9e44; }}
  .wrong .pick {{ color: #e03131; }}
  .bar {{ height: 4px; margin: 6px 0; border-radius: 2px; background: #e9ecef; }}
  .bar span {{ display: block; height: 100%; border-radius: 2px; background: #1c7ed6; }}
  .small {{ font-size: 11px; color: #6b7785; }}
  .flag {{ margin-left: 4px; padding: 0 4px; border-radius: 4px; background: #fff3bf; color: #946200; }}
  .empty {{ margin-top: 30px; font-size: 12px; text-align: center; color: #adb5bd; }}
</style></head><body>
<header>
  <h1>Jev receipt sorting</h1>{status}
  <div class="stats">
    <div><b>{done}</b><span>sorted</span></div>
    <div><b>{correct}</b><span>matched my label</span></div>
    <div><b>{reviewed}</b><span>sent to review</span></div>
  </div>
</header>
<div class="progress"><span style="width: {percent:.0f}%"></span></div>
<main>
  <p class="legend">Green edge: Jev's choice matched labels.csv. Red edge: it did not. Blue bar: Jev's confidence. Yellow outline: the receipt Jev just answered. Confidence threshold for sorting: {CONFIDENCE_THRESHOLD}</p>
  <div class="board">{''.join(columns)}</div>
</main>
</body></html>"""

    temporary = REPORT.with_suffix(".tmp")
    temporary.write_text(page, encoding="utf-8")
    temporary.replace(REPORT)


def main():
    with open("receipts/labels.csv", newline="") as file:
        labels = list(csv.DictReader(file))

    rows = []
    write_report(rows, PREPARED / labels[0]["filename"], len(labels))
    webbrowser.open(REPORT.resolve().as_uri())

    for label in labels:
        image = PREPARED / label["filename"]
        write_report(rows, image, len(labels))
        result = ask(image, QUESTIONS, image_name="receipt")
        answer = result["answers"]["category"]
        sideways = result["answers"]["sideways"]["noul"]

        top_two = sorted(answer["probabilities"].items(), key=lambda item: item[1], reverse=True)[:2]
        confident = answer["confidence"] >= CONFIDENCE_THRESHOLD
        folder = answer["choice"] if confident else "_review"

        (SORTED / folder).mkdir(parents=True, exist_ok=True)
        shutil.copy(image, SORTED / folder / image.name)

        rows.append({
            "filename": label["filename"],
            "expected": label["expected"],
            "choice": answer["choice"],
            "confidence": answer["confidence"],
            "sideways": sideways,
            "top_two": " / ".join(f"{name} {probability:.2f}" for name, probability in top_two),
            "folder": folder,
            "input_tokens": result["usage"]["input_tokens"],
            "elapsed_ms": result["elapsed_ms"],
        })
        print(f"{label['filename']:<32} {label['expected']:<18} {answer['choice']:<18} "
              f"{answer['confidence']:.2f}  sideways {sideways:.2f}  {folder}")
        time.sleep(LIVE_DELAY)

    write_report(rows)

    correct = sum(1 for row in rows if row["choice"] == row["expected"])
    sent_to_review = sum(1 for row in rows if row["folder"] == "_review")
    print(f"\n{correct} of {len(rows)} correct, {sent_to_review} sent to review")

    with open("receipts/results.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
