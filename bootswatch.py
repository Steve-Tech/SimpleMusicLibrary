import requests


def main(themes_dir="static/css/themes"):
    bootswatch = requests.get("https://bootswatch.com/api/5.json").json()

    print("Bootswatch Version: ", bootswatch["version"])

    for theme in bootswatch["themes"]:
        print(theme["name"])
        r = requests.get(theme["cssMin"])
        with open(themes_dir + '/' + theme["name"].title() + ".css", 'wb') as f:
            f.write(r.content)


if __name__ == '__main__':
    main()
