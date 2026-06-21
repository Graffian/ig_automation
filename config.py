import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    if not os.path.exists(CONFIG_FILE):
        print(f"Config file not found. Creating template at {CONFIG_FILE}")
        save_config({"username": "", "password": "", "track_interval_minutes": 30, "target_accounts": []})
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def validate_config(config):
    missing = []
    if not config.get("username"):
        missing.append("username")
    if not config.get("password"):
        missing.append("password")
    if not config.get("target_accounts"):
        missing.append("target_accounts (list of accounts to track)")
    if missing:
        print(f"Missing config fields: {', '.join(missing)}")
        print("Edit config.json and fill in the required fields.")
        return False
    return True
