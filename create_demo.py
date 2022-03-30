from os import makedirs, chdir
import shutil

from database import *
import app
import setup


@app.app.route('/auto_login')
def auto_login():
    app.login_user(Users.query.get("guest"))
    return '', 204


def main():
    for d in ["demo/songs", "demo/image", "demo/albums", "demo/artists"]:
        makedirs(d, exist_ok=True)

    app.settings['users'] = ["guest"]
    app.settings['library'] = "demo/songs"
    db.create_all()
    setup.download()
    setup.users()
    setup.scan()

    chdir("demo")

    with app.app.test_client() as client:
        open("login.html", 'wb').write(client.get('/login').data)
        assert client.get('/auto_login').status_code == 204, "Failed to login"
        open("index.html", 'wb').write(client.get('/').data)
        open("albums/index.html", 'wb').write(client.get('/albums').data)
        for i, in db.session.query(Music.id).group_by(Music.album).order_by(Music.album):
            print(f"albums/{i}/index.html")
            makedirs(f"albums/{i}", exist_ok=True)
            open(f"albums/{i}/index.html", 'wb').write(client.get(f'/albums/{i}').data)
        open("artists/index.html", 'wb').write(client.get('/artists').data)
        for i, in db.session.query(Music.id).group_by(Music.artist).order_by(Music.artist):
            makedirs(f"artists/{i}", exist_ok=True)
            open(f"artists/{i}/index.html", 'wb').write(client.get(f'/artists/{i}').data)

    shutil.copytree("../static", "static", dirs_exist_ok=True)


if __name__ == '__main__':
    main()
