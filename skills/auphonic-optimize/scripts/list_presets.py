#!/usr/bin/env python3
"""
List Auphonic presets and manage saved preset selections.

Usage:
    python3 list_presets.py                     # Fetch and list all presets from Auphonic
    python3 list_presets.py --save UUID          # Save a preset UUID as the default
    python3 list_presets.py --show-saved          # Show currently saved default preset

Environment:
    AUPHONIC_API_KEY must be set (or present in .env at the repo root).
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_DIR / "config.json"
API_BASE = "https://auphonic.com/api"


def parse_args():
    parser = argparse.ArgumentParser(description="List and manage Auphonic presets")
    parser.add_argument(
        "--save", metavar="UUID",
        help="Save a preset UUID as the default and cache its name"
    )
    parser.add_argument(
        "--show-saved", action="store_true",
        help="Show the currently saved default preset"
    )
    return parser.parse_args()


def load_dotenv():
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        env_path = Path.cwd() / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


def load_config() -> dict:
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"default_preset": None, "presets": {}}


def save_config(config: dict):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def get_api_key() -> str:
    api_key = os.environ.get("AUPHONIC_API_KEY")
    if not api_key:
        print("Error: AUPHONIC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    return api_key


def fetch_presets(api_key: str) -> list[dict]:
    resp = requests.get(
        f"{API_BASE}/presets.json",
        params={"minimal_data": "1"},
        headers={"Authorization": f"bearer {api_key}"},
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"Error: Auphonic API returned {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    body = resp.json()
    presets = body.get("data", [])

    result = []
    for p in presets:
        result.append({
            "uuid": p.get("uuid", ""),
            "name": p.get("preset_name", "Untitled"),
            "created": (p.get("creation_time") or "")[:10],
            "is_multitrack": p.get("is_multitrack", False),
        })
    return result


def handle_show_saved():
    config = load_config()
    default_uuid = config.get("default_preset")
    if not default_uuid:
        print(json.dumps({"status": "no_default", "message": "No default preset saved"}))
        return
    name = config.get("presets", {}).get(default_uuid, "Unknown")
    print(json.dumps({"status": "ok", "uuid": default_uuid, "name": name}))


def handle_save(uuid: str, api_key: str):
    config = load_config()

    cached_name = config.get("presets", {}).get(uuid)
    if not cached_name:
        presets = fetch_presets(api_key)
        matched = [p for p in presets if p["uuid"] == uuid]
        if not matched:
            print(f"Error: Preset UUID '{uuid}' not found in your Auphonic account", file=sys.stderr)
            sys.exit(1)
        cached_name = matched[0]["name"]

    config["default_preset"] = uuid
    config.setdefault("presets", {})[uuid] = cached_name
    save_config(config)

    print(json.dumps({"status": "saved", "uuid": uuid, "name": cached_name}))


def handle_list(api_key: str):
    presets = fetch_presets(api_key)
    config = load_config()

    for p in presets:
        config.setdefault("presets", {})[p["uuid"]] = p["name"]
    save_config(config)

    print(json.dumps(presets, indent=2))


def main():
    args = parse_args()
    load_dotenv()

    if args.show_saved:
        handle_show_saved()
        return

    api_key = get_api_key()

    if args.save:
        handle_save(args.save, api_key)
    else:
        handle_list(api_key)


if __name__ == "__main__":
    main()
