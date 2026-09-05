"""Check which Groq models are available to an API key.

Usage:
	set GROQ_API_KEY=your_key      # PowerShell: $env:GROQ_API_KEY="your_key"
	python src/main.py
	python src/main.py --model grok-3-mini
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv


BASE_URL = "https://api.groq.com/openai/v1"


def main() -> int:
	load_dotenv()
	parser = argparse.ArgumentParser(description="Test models available to a Groq API key")
	parser.add_argument("--model", help="Also send a test request to this model")
	args = parser.parse_args()

	api_key = os.getenv("GROQ_API_KEY")
	if not api_key:
		print("Set GROQ_API_KEY first.", file=sys.stderr)
		return 1

	headers = {"Authorization": f"Bearer {api_key}"}
	try:
		response = requests.get(f"{BASE_URL}/models", headers=headers, timeout=30)
		response.raise_for_status()
		models = response.json().get("data", [])
	except requests.RequestException as exc:
		print(f"Could not list models: {exc}", file=sys.stderr)
		return 1

	print("Models available to this key:")
	for model in models:
		print(f"- {model.get('id', '<unknown>')}")

	if args.model:
		try:
			test = requests.post(
				f"{BASE_URL}/chat/completions",
				headers={**headers, "Content-Type": "application/json"},
				json={
					"model": args.model,
					"messages": [{"role": "user", "content": "Reply with: OK"}],
					"max_tokens": 10,
				},
				timeout=30,
			)
			test.raise_for_status()
			content = test.json()["choices"][0]["message"]["content"]
			print(f"\n{args.model} works: {content}")
		except (requests.RequestException, KeyError, IndexError) as exc:
			print(f"\n{args.model} failed: {exc}", file=sys.stderr)
			return 1

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
