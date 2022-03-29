import requests
import shutil
from os import makedirs

themes_dir = "static/css/themes"
makedirs(themes_dir, exist_ok=True)

print("------ Downloading Bootswatch Themes ------")
bootswatch = requests.get("https://bootswatch.com/api/5.json").json()

print("Bootswatch Version: ", bootswatch["version"])

for theme in bootswatch["themes"]:
    r = requests.get(theme["cssMin"])
    with open(f"{themes_dir}/{theme['name'].title()}.css", 'wb') as f:
        f.write(r.content)

print("------ Copying Static to Demo ------")
shutil.copytree("static", "demo/static")
