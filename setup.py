import json
from hashlib import blake2b
from os.path import dirname, join, split, exists
from os import walk, makedirs

from sqlalchemy import inspect
from tinytag import TinyTag, TinyTagException

from database import *

themes_dir = "static/css/themes"
makedirs(themes_dir, exist_ok=True)

from app import app, settings


def main():
    if input("Download Bootswatch Themes? [y/N]: "):
        import bootswatch
        print("Downloading Bootswatch Themes")
        bootswatch.main(themes_dir)

    with app.app_context():
        if inspect(db.engine).get_table_names():
            if input("Drop All Tables? [y/N]: ") == 'y':
                db.drop_all()
                db.session.commit()
            elif input("Drop All Music Tables? [y/N]: ") == 'y':
                Music.__table__.drop(db.engine)
                History.__table__.drop(db.engine)
                Playlists.__table__.drop(db.engine)
                PlaylistSongs.__table__.drop(db.engine)
                Queue.__table__.drop(db.engine)
                db.session.commit()

        db.create_all()
        db.session.commit()

        for user in settings["users"]:
            if not db.session.query(Users.query.filter_by(username=user).exists()).scalar():
                print("Creating user:", user)
                print("Password:", password := user.capitalize() + "!")
                db.session.add(Users(username=user, password=blake2b(bytes(password, "utf-8")).hexdigest()))

        db.session.commit()

        print("Deleting deleted files")
        for id, file in db.session.query(Music.id, Music.file).all():
            if not exists(file):
                print(file)
                Music.query.get(id).delete()

        for root, dirs, files in walk(settings['library']):
            for i, filename in enumerate(sorted(files)):
                path = join(root, filename)
                print(path)
                if not db.session.query(Music.query.filter_by(file=path).exists()).scalar():
                    try:
                        meta = TinyTag.get(path, image=True)
                        print(meta)
                        new_meta = meta.as_dict()
                        new_meta['title'] = meta.title or filename
                        new_meta['album'] = meta.album or split(dirname(path))[1]
                        new_meta['albumartist'] = meta.albumartist or split(dirname(dirname(path)))[1]
                        new_meta['artist'] = meta.artist or split(dirname(dirname(path)))[1]
                        new_meta['disc'] = meta.disc or 1
                        new_meta['genre'] = meta.genre or split(dirname(dirname(dirname(path))))[1]
                        new_meta['track'] = meta.track or i + 1
                        db.session.add(
                            Music(file=path,
                                  title=new_meta['title'],
                                  album=new_meta['album'],
                                  album_artist=new_meta['albumartist'],
                                  artist=new_meta['artist'],
                                  disc=new_meta['disc'],
                                  genre=new_meta['genre'],
                                  track=new_meta['track'],
                                  year=meta.year,
                                  duration=meta.duration,
                                  json=json.dumps(new_meta),
                                  image=meta.get_image()))
                        db.session.flush()

                    except TinyTagException as e:
                        print(e)

        db.session.commit()


if __name__ == '__main__':
    main()
