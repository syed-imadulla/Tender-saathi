import requests
import json
import sys

def test_api(text):
    url = "http://localhost:5000/api/analyze/text"
    payload = {"text": text}
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error {response.status_code}: {response.text}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = sys.argv[1]
    else:
        text = "Supply and installation of CPVC pipes and fittings for domestic hot and cold water distribution system, conforming to IS 15778."
    test_api(text)
