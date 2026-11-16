import json
import sys

from jev_client import ask

questions = {
    "is_receipt": {
        "type": "noul",
        "instructions": "Is `receipt` a photo or scan of a purchase receipt?",
    }
}

result = ask(sys.argv[1], questions, image_name="receipt")
print(json.dumps(result, indent=2))
