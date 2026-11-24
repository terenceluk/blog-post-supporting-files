import json
import sys

from jev_client import ask
from pet_report import open_report, write_presence_report

questions = {
    "has_animal": {"type": "noul", "instructions": "Is there a cat or dog in `photo`?"},
    "head": {"type": "box", "instructions": "the head of the cat or dog in `photo`"},
}

result = ask(sys.argv[1], questions, image_name="photo")
print(json.dumps(result["answers"], indent=2))
open_report(write_presence_report(sys.argv[1], result["answers"]))
