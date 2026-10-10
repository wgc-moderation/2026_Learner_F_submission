"""Create the private settings for the staff login."""
# import the needed modules
import json
import secrets
from getpass import getpass
from pathlib import Path
from werkzeug.security import generate_password_hash

# Create the instance folder and settings file
folder = Path(__file__).resolve().parent / "instance"
folder.mkdir(exist_ok=True)
settings_file = folder / "login.json"

# Check if the settings file already exists
if settings_file.exists():
    raise SystemExit("Login already exists. No settings were changed.")

# Prompt the user for a username and password
username = input("Choose a staff username: ").strip()
password = getpass("Choose a password (at least 12 characters): ")
confirmation = getpass("Type the password again: ")

# Validate the input and create the settings file
if not username or len(password) < 12 or password != confirmation:
    raise SystemExit("Details did not match or were too short. Run again.")

# Create the settings dictionary and write it to the settings file
settings = {
    "username": username,
    "password_hash": generate_password_hash(password),
    "secret_key": secrets.token_hex(32)
}

# Write the settings to the file and set permissions
settings_file.write_text(json.dumps(settings), encoding="utf-8")
settings_file.chmod(0o600)
print("Staff account created.")
