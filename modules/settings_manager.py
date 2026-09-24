import json
import os

SETTINGS_FILE = "config/settings.json"


def load_settings():

    if os.path.exists(SETTINGS_FILE):

        with open(
            SETTINGS_FILE,
            "r"
        ) as file:

            return json.load(file)

    return {
        "teams_folder": ""
    }


def save_settings(settings):

    with open(
        SETTINGS_FILE,
        "w"
    ) as file:

        json.dump(
            settings,
            file,
            indent=4
        )
