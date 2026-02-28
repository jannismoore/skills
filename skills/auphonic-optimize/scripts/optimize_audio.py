#!/usr/bin/env python3
"""
Upload an audio file to Auphonic for optimization, poll until done, and download the result.

Usage:
    python3 optimize_audio.py \
        --file "raw/recording.mp3" \
        --project-dir "projects/2026-02-28-my-project" \
        --preset "ceigtvDv8jH6NaK52Z5eXH"

    python3 optimize_audio.py \
        --file "raw/recording.mp3" \
        --project-dir "projects/2026-02-28-my-project"
        # (uses default preset from config.json)

The --file argument is a path relative to the project directory.
The --project-dir argument is relative to repo root.

Environment:
    AUPHONIC_API_KEY must be set (or present in .env at the repo root).
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[4]
SKILL_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = SKILL_DIR / "config.json"
API_BASE = "https://auphonic.com/api"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".aac", ".flac", ".m4a", ".ogg", ".opus", ".wma"}

STATUS_DONE = 3
STATUS_ERROR = 9
STATUS_INCOMPLETE = 13
POLL_INTERVAL = 10
MAX_POLL_TIME = 600


def parse_args():
    parser = argparse.ArgumentParser(description="Optimize audio via Auphonic")
    parser.add_argument(
        "--file", required=True,
        help="Audio file path relative to the project dir (e.g., raw/recording.mp3)"
    )
    parser.add_argument(
        "--project-dir", required=True,
        help="Project directory relative to repo root (e.g., projects/2026-02-28-my-project)"
    )
    parser.add_argument(
        "--preset",
        help="Auphonic preset UUID (falls back to config.json default)"
    )
    parser.add_argument(
        "--title",
        help="Production title (defaults to filename)"
    )
    parser.add_argument(
        "--output-dir", default="audio/optimized",
        help="Subdirectory within project for the result (default: audio/optimized)"
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


def get_api_key() -> str:
    api_key = os.environ.get("AUPHONIC_API_KEY")
    if not api_key:
        print("Error: AUPHONIC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    return api_key


def resolve_preset(args_preset: str | None) -> str:
    if args_preset:
        return args_preset
    config = load_config()
    default = config.get("default_preset")
    if not default:
        print("Error: No --preset provided and no default preset saved in config.json", file=sys.stderr)
        print("Run list_presets.py --save UUID to set a default first.", file=sys.stderr)
        sys.exit(1)
    return default


def upload_and_start(api_key: str, file_path: Path, preset_uuid: str, title: str) -> dict:
    """Upload audio and start production in a single Simple API request."""
    print(f"Uploading {file_path.name} to Auphonic...", file=sys.stderr)

    with open(file_path, "rb") as f:
        resp = requests.post(
            f"{API_BASE}/simple/productions.json",
            headers={"Authorization": f"bearer {api_key}"},
            files={"input_file": (file_path.name, f)},
            data={
                "preset": preset_uuid,
                "title": title,
                "action": "start",
            },
            timeout=300,
        )

    if resp.status_code != 200:
        print(f"Error: Auphonic API returned {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(1)

    body = resp.json()
    if body.get("error_code"):
        print(f"Error: {body.get('error_message', 'Unknown error')}", file=sys.stderr)
        sys.exit(1)

    return body["data"]


def poll_status(api_key: str, production_uuid: str) -> dict:
    """Poll production status until done or error."""
    print(f"Processing (production: {production_uuid})...", file=sys.stderr)
    waited = 0

    while waited < MAX_POLL_TIME:
        time.sleep(POLL_INTERVAL)
        waited += POLL_INTERVAL

        resp = requests.get(
            f"{API_BASE}/production/{production_uuid}.json",
            headers={"Authorization": f"bearer {api_key}"},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"Warning: Status check returned {resp.status_code}, retrying...", file=sys.stderr)
            continue

        data = resp.json().get("data", {})
        status = data.get("status")
        status_str = data.get("status_string", "Unknown")

        print(f"  Status: {status_str} ({waited}s elapsed)", file=sys.stderr)

        if status == STATUS_DONE:
            return data
        if status in (STATUS_ERROR, STATUS_INCOMPLETE):
            error_msg = data.get("error_message", "Unknown error")
            print(f"Error: Production failed — {error_msg}", file=sys.stderr)
            sys.exit(1)

    print(f"Error: Production timed out after {MAX_POLL_TIME}s", file=sys.stderr)
    sys.exit(1)


def download_results(api_key: str, production_data: dict, output_path: Path) -> list[dict]:
    """Download all output files from a completed production."""
    output_path.mkdir(parents=True, exist_ok=True)
    downloaded = []

    output_files = production_data.get("output_files", [])
    for of in output_files:
        url = of.get("download_url")
        filename = of.get("filename")
        if not url or not filename:
            continue

        fmt = of.get("format", "")
        if fmt in ("descr", "stats", "chaps", "psc", "cut-list", "waveform", "image"):
            continue

        print(f"  Downloading {filename}...", file=sys.stderr)
        resp = requests.get(
            url,
            headers={"Authorization": f"bearer {api_key}"},
            timeout=120,
            stream=True,
        )
        if resp.status_code != 200:
            print(f"  Warning: Failed to download {filename} (HTTP {resp.status_code})", file=sys.stderr)
            continue

        dest = output_path / filename
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        downloaded.append({
            "filename": filename,
            "format": fmt,
            "size": of.get("size_string", ""),
            "path": str(dest.relative_to(REPO_ROOT)),
        })

    return downloaded


def update_index(project_path: Path, output_dir: str, downloaded: list[dict], production_uuid: str):
    """Update file_index.json with entries for each downloaded file."""
    index_path = project_path / "file_index.json"
    if index_path.exists():
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {}

    for dl in downloaded:
        key = f"{output_dir}/{dl['filename']}"
        entry = index.get(key, {})
        entry["added"] = entry.get("added", datetime.now().strftime("%Y-%m-%d"))
        entry["type"] = "audio"
        entry.setdefault("description", "")
        entry.setdefault("notes", "")
        entry["origin"] = {
            "skill": "auphonic-optimize",
            "auphonic_production": production_uuid,
            "format": dl["format"],
        }
        index[key] = entry

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
        f.write("\n")


def extract_stats(production_data: dict) -> dict | None:
    """Pull before/after loudness stats from the production response."""
    stats = production_data.get("statistics", {})
    levels = stats.get("levels")
    if not levels:
        return None

    result = {}
    inp = levels.get("input", {})
    out = levels.get("output", {})

    if inp.get("loudness"):
        result["input_loudness"] = f"{inp['loudness'][0]} {inp['loudness'][1]}"
    if inp.get("snr"):
        result["input_snr"] = f"{inp['snr'][0]} {inp['snr'][1]}"
    if out.get("loudness"):
        result["output_loudness"] = f"{out['loudness'][0]} {out['loudness'][1]}"
    if out.get("peak"):
        result["output_peak"] = f"{out['peak'][0]} {out['peak'][1]}"

    cuts = stats.get("cuts")
    if cuts:
        for c in cuts:
            result[f"cuts_{c['name']}"] = f"{c['count']} cuts ({c['percent']}%)"

    return result if result else None


def main():
    args = parse_args()
    load_dotenv()

    api_key = get_api_key()
    preset_uuid = resolve_preset(args.preset)

    project_path = REPO_ROOT / args.project_dir
    file_path = project_path / args.file

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    ext = file_path.suffix.lower()
    if ext not in AUDIO_EXTENSIONS:
        print(f"Error: Not a supported audio file ({ext}). Supported: {', '.join(sorted(AUDIO_EXTENSIONS))}", file=sys.stderr)
        sys.exit(1)

    title = args.title or file_path.stem

    production_data = upload_and_start(api_key, file_path, preset_uuid, title)
    production_uuid = production_data["uuid"]

    production_data = poll_status(api_key, production_uuid)

    output_path = project_path / args.output_dir
    downloaded = download_results(api_key, production_data, output_path)

    if not downloaded:
        print("Warning: No audio output files were downloaded.", file=sys.stderr)

    update_index(project_path, args.output_dir, downloaded, production_uuid)

    audio_stats = extract_stats(production_data)

    summary = {
        "status": "ok",
        "production_uuid": production_uuid,
        "preset": preset_uuid,
        "input_file": args.file,
        "output_files": downloaded,
        "duration": production_data.get("length_timestring", ""),
        "warnings": production_data.get("warning_message", "") or None,
    }
    if audio_stats:
        summary["audio_stats"] = audio_stats

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
