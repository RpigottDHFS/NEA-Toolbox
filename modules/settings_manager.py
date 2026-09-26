from __future__ import annotations

import json
from pathlib import Path

APP_DIR = Path.home() / ".nea_toolbox"
SETTINGS_FILE = APP_DIR / "settings.json"
DEFAULTS = {
    "centre_number": "23162",
    "last_roster": "",
    "last_output_folder": "",
}


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            saved = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULTS, **saved}
        except (OSError, json.JSONDecodeError):
            pass
    return dict(DEFAULTS)


def save_settings(settings):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps({**DEFAULTS, **settings}, indent=2), encoding="utf-8")
