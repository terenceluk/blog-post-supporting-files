import json
import os
import time
import uuid
from pathlib import Path

import requests

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.14.0"


def ask(image_path, questions, image_name="photo"):
    """Send one image and a set of questions to Jev and return the parsed response."""
    reference = str(uuid.uuid4())
    body = {
        "model": MODEL,
        "state": {image_name: reference},
        "assets": {reference: {"type": "image", "part": "image"}},
        "questions": questions,
    }

    image_path = Path(image_path)
    files = [
        ("request", (None, json.dumps(body), "application/json")),
        ("image", (image_path.name, image_path.read_bytes(), "image/jpeg")),
    ]
    headers = {
        "Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}",
        "TypeSafe-Danger-Zone-Images": "true",
    }

    started = time.perf_counter()
    response = requests.post(API_URL, headers=headers, files=files, timeout=60)
    elapsed_ms = round((time.perf_counter() - started) * 1000)

    if response.status_code != 200:
        raise RuntimeError(f"{response.status_code} from Jev: {response.text}")

    result = response.json()
    result["elapsed_ms"] = elapsed_ms
    return result
