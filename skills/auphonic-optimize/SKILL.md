---
name: auphonic-optimize
description: Use when the user wants to optimize, clean up, or post-process an audio file using Auphonic. Handles leveling, noise reduction, loudness normalization, and more via the Auphonic cloud API.
---

# Auphonic Audio Optimization

Optimize audio files using the Auphonic API. Uploads a file, processes it with a user-selected preset (leveling, noise reduction, loudness normalization, etc.), and downloads the optimized result.

---

## Process

### Step 1: Determine Working Directory

Ask the user which directory contains the audio file they want to optimize. This will be used as the `--project-dir` argument. If the user's request already includes a path or enough context to infer it, confirm rather than re-asking.

### Step 2: Select Preset

Check if a default preset is already saved:

```bash
python3 .claude/skills/auphonic-optimize/scripts/list_presets.py --show-saved
```

- **If a default exists:** The script prints `{"status": "ok", "uuid": "...", "name": "..."}`. Confirm with the user: "Using preset **{name}**. Want to use a different one?" If they confirm or don't object, proceed to Step 3.
- **If no default:** The script prints `{"status": "no_default"}`. Continue below to fetch and select.

Fetch available presets from Auphonic:

```bash
python3 .claude/skills/auphonic-optimize/scripts/list_presets.py
```

The script returns a JSON array of presets:

```json
[
  {"uuid": "ceigtvDv8jH6NaK52Z5eXH", "name": "My Podcast Preset", "created": "2026-01-15", "is_multitrack": false},
  {"uuid": "9KN6czHvcrVeYWex5aQz59", "name": "Video Audio Cleanup", "created": "2026-02-01", "is_multitrack": false}
]
```

Present the presets in a numbered list and ask the user to pick one. Then save their choice as the default:

```bash
python3 .claude/skills/auphonic-optimize/scripts/list_presets.py --save "{selected_uuid}"
```

This stores the preset in `config.json` so it's remembered for next time.

### Step 3: Select Audio File

Ask the user which audio file to optimize. If they've already specified a file, confirm it. Otherwise, you can list audio files in the working directory to help them choose:

```bash
find {project_dir} -maxdepth 2 -type f \( -name "*.mp3" -o -name "*.wav" -o -name "*.m4a" -o -name "*.aac" -o -name "*.flac" -o -name "*.ogg" -o -name "*.opus" \) 2>/dev/null
```

Present any found files to the user and ask which one to optimize. If only one audio file exists, confirm it with the user.

### Step 4: Optimize

Run the optimization script. The `--file` argument is a path relative to `--project-dir`:

```bash
python3 .claude/skills/auphonic-optimize/scripts/optimize_audio.py \
  --file "{relative_path_to_file}" \
  --project-dir "{project_dir}"
```

To use a specific preset (overriding the saved default):

```bash
python3 .claude/skills/auphonic-optimize/scripts/optimize_audio.py \
  --file "{relative_path_to_file}" \
  --project-dir "{project_dir}" \
  --preset "{preset_uuid}"
```

To set a custom production title:

```bash
python3 .claude/skills/auphonic-optimize/scripts/optimize_audio.py \
  --file "{relative_path_to_file}" \
  --project-dir "{project_dir}" \
  --title "My Custom Title"
```

To change the output directory (default is `audio/optimized`):

```bash
python3 .claude/skills/auphonic-optimize/scripts/optimize_audio.py \
  --file "{relative_path_to_file}" \
  --project-dir "{project_dir}" \
  --output-dir "audio/final"
```

The script will:
1. Upload the file to Auphonic and start processing
2. Poll for completion every 10 seconds (up to 10 minutes)
3. Download the optimized output file(s)
4. Update `file_index.json` with origin metadata
5. Print a JSON summary

Keep the user informed of progress — the script prints status updates to stderr during upload, processing, and download.

### Step 5: Report Results

The script outputs a JSON summary:

```json
{
  "status": "ok",
  "production_uuid": "X2bUTQ8z888YaKukkU6vfJ",
  "preset": "ceigtvDv8jH6NaK52Z5eXH",
  "input_file": "raw/recording.mp3",
  "output_files": [
    {"filename": "recording.mp3", "format": "mp3", "size": "12.4 MB", "path": "my-project/audio/optimized/recording.mp3"}
  ],
  "duration": "00:15:32.100",
  "warnings": null,
  "audio_stats": {
    "input_loudness": "-22.5 LUFS",
    "input_snr": "28.3 dB",
    "output_loudness": "-16.0 LUFS",
    "output_peak": "-1.0 dBTP",
    "cuts_filler": "12 cuts (2.1%)",
    "cuts_silence": "8 cuts (1.5%)"
  }
}
```

Summarize to the user:

- Where the optimized file was saved
- Before/after loudness levels (if available in `audio_stats`)
- Any cuts applied (filler words, silence)
- Any warnings from Auphonic
- The Auphonic production UUID for reference

---

## Switching Presets

If the user wants to switch to a different preset mid-session, re-run the preset listing and save:

```bash
python3 .claude/skills/auphonic-optimize/scripts/list_presets.py
python3 .claude/skills/auphonic-optimize/scripts/list_presets.py --save "{new_uuid}"
```

---

## Examples

**Basic optimization with saved preset:**

```bash
python3 .claude/skills/auphonic-optimize/scripts/optimize_audio.py \
  --file "raw/voiceover-take-3.wav" \
  --project-dir "my-project"
```

**With explicit preset and title:**

```bash
python3 .claude/skills/auphonic-optimize/scripts/optimize_audio.py \
  --file "raw/interview-raw.mp3" \
  --project-dir "my-project" \
  --preset "9KN6czHvcrVeYWex5aQz59" \
  --title "Interview with Guest"
```

**Output to a custom directory:**

```bash
python3 .claude/skills/auphonic-optimize/scripts/optimize_audio.py \
  --file "raw/podcast-episode.mp3" \
  --project-dir "my-project" \
  --output-dir "audio/final"
```

---

## Supported Audio Formats

| Extension | Format |
|-----------|--------|
| `.mp3` | MP3 |
| `.wav` | WAV |
| `.m4a` | AAC / ALAC |
| `.aac` | AAC |
| `.flac` | FLAC |
| `.ogg` | Ogg Vorbis |
| `.opus` | Opus |
| `.wma` | WMA |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "AUPHONIC_API_KEY not set" | Add `AUPHONIC_API_KEY=your_key` to `.env` at the repo root. Get your key from [Auphonic Account Settings](https://auphonic.com/accounts/settings/#api-key). |
| "No default preset saved" | Run `list_presets.py` to see available presets, then `list_presets.py --save UUID` to set one. |
| "Preset UUID not found" | The UUID doesn't match any preset in your Auphonic account. Run `list_presets.py` to see valid UUIDs. |
| "Production timed out" | Large files (>1 hour) may take longer. The script polls for up to 10 minutes. For very long files, check the [Auphonic status page](https://auphonic.com/engine/status/) directly. |
| "Production failed" | Check the error message. Common causes: unsupported format, corrupted file, or account credit limit reached. |
| Wrong output format | Output format is determined by the Auphonic preset. Edit your preset at [auphonic.com/engine/presets](https://auphonic.com/engine/presets/) to change output formats. |
