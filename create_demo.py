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
    for d in ["demo/songs", "demo/images", "demo/albums", "demo/artists"]:
        makedirs(d, exist_ok=True)
    chdir("demo")

    app.settings['users'] = ["guest"]
    app.settings['library'] = "demo/songs"
    db.create_all()
    setup.download()
    setup.users()
    setup.scan()

    with app.app.test_client() as client:
        open("login.html", 'wb').write(client.get('/login').data)
        assert client.get('/auto_login').status_code == 204, "Failed to login"
        open("index.html", 'wb').write(client.get('/').data)
        open("albums/index.html", 'wb').write(client.get('/albums').data)
        for i, in db.session.query(Music.id).group_by(Music.album).order_by(Music.album):
            open(f"albums/{i}.html", 'wb').write(client.get(f'/albums/{i}').data)
        open("artists/index.html", 'wb').write(client.get('/artists').data)
        for i, in db.session.query(Music.id).group_by(Music.artist).order_by(Music.artist):
            open(f"artists/{i}.html", 'wb').write(client.get(f'/artists/{i}').data)

    shutil.copytree("../static", "static", dirs_exist_ok=True)


if __name__ == '__main__':
    main()
