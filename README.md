# SimpleMusicLibrary
A Simple Bootstrap Music Library

## Installation
### Requirements
- Python 3.9+
  - This could be fairly easy to port to an older version
- A WSGI Server
  - eg. Gunicorn or uWSGI

### Music
- The folder structure should be `$genre$/$artist$/$album$/`
- This is only used if TinyTag could not read the metadata for each song

### Settings
- Create settings.json and edit with your preferred settings:
  - `database`: An SQLAlchemy database URI
  - `secret_key`: Something secure, long and random for flask sessions
  - `library`: Your library location
    - `\\` for Windows, `/` for everything else
  - `users`: An array of users to create
    - Default password is username with capital first letter + exclamation mark
      - eg. `admin` -> `Admin!`
  - `watchdog`: Watch and scan new files in library
  - `delete_allowed`: Is watchdog allowed to remove deleted files from database
  - `ignore_prefix`: Ignore new files starting with anything in array
```json
{
  "database": "sqlite:///database.db",
  "secret_key": "replace with something random",
  "library": "M:\\Music",
  "users": ["admin", "family", "guest"],
  "watchdog": true,
  "delete_allowed": true,
  "ignore_prefix": ["0tmp", "1tmp"]
}
```

### Setup
- `pip install -r requirements.txt`
- `python3 setup.py`
  - `Download Bootswatch Themes? [y/N]: ` - Download themes from bootswatch
  - `Drop All Tables? [y/N]: ` - Reset all data, only needed for reinstall
  - `Drop All Music Tables? [y/N]: ` - Reset all data except userdata, only needed for reinstall
  - `Create Users? [y/N]: ` - Create users from settings, does no harm if users exist
  - `Search Library for Songs? [y/N]: ` - Delete deleted songs and add new songs to the database
- Run `app.py` with your WSGI server