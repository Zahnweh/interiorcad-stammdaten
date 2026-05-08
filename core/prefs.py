import os, json, platform

_APP_NAME = "interiorcad Stammdaten"


def _get_custom_file():
    if platform.system() == "Windows":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    else:
        base = os.path.expanduser("~/Library/Application Support")
    folder = os.path.join(base, _APP_NAME)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "custom_values.json")


CUSTOM_FILE = _get_custom_file()


def load_custom():
    try:
        with open(CUSTOM_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"thicknesses": [], "edges": []}


def save_custom(data):
    try:
        with open(CUSTOM_FILE, "w") as f:
            json.dump(data, f)
    except Exception:
        pass
