#!/usr/bin/python3
import json
from hashlib import blake2b
from os.path import dirname, join, split, exists
from os import walk, makedirs
from sys import argv

import requests
from sqlalchemy import inspect
from tinytag import TinyTag, TinyTagException
from tqdm import tqdm
from mmh3 import hash64

from database import *

themes_dir = "static/css/themes"
makedirs(themes_dir, exist_ok=True)

from app import app, settings


app.app_context().push()


def download():
    print("------ Downloading Bootswatch Themes ------")
    bootswatch = requests.get("https://bootswatch.com/api/5.json").json()

    print("Bootswatch Version: ", bootswatch["version"])

    for theme in (progress := tqdm(bootswatch["themes"], desc="Downloading Bootswatch Themes")):
        progress.set_postfix_str("Downloading: " + theme["name"])
        r = requests.get(theme["cssMin"])
        with open(f"{themes_dir}/{theme['name'].title()}.css", 'wb') as f:
            f.write(r.content)


def drop():
    print("------ Dropping all tables ------")
    db.drop_all()
    db.session.commit()


def drop_music():
    print("------ Dropping music tables ------")
    print("Dropping: Music")
    Music.__table__.drop(db.engine)
    print("Dropping: History")
    History.__table__.drop(db.engine)
    print("Dropping: Playlists")
    Playlists.__table__.drop(db.engine)
    print("Dropping: PlaylistSongs")
    PlaylistSongs.__table__.drop(db.engine)
    print("Dropping: Queue")
    Queue.__table__.drop(db.engine)
    db.session.commit()


def users():
    print("------ Creating Users ------")
    for user in settings["users"]:
        if not db.session.query(Users.query.filter_by(username=user).exists()).scalar():
            print("Username:", user)
            print("Password:", password := user.capitalize() + "!")
            db.session.add(Users(username=user, password=blake2b(bytes(password, "utf-8")).hexdigest()))
    db.session.commit()


def scan():
    print("------ Deleting deleted files ------")
    for id, file in (progress := tqdm(db.session.query(Music.id, Music.file).all(), desc="Finding deleted files")):
        if not exists(file):
            # print("Deleting: ", file)
            progress.set_postfix_str("Deleting: " + file)
            Music.query.filter_by(id=id).delete()
            db.session.flush()
    db.session.commit()

    print("------ Finding new files ------")
    for root, dirs, files in (progress := tqdm(walk(settings['library']), desc="Finding new files")):
        for i, filename in enumerate(sorted(files)):
            path = join(root, filename)
            # progress.set_postfix_str(path)
            # print("Found: ", path)
            if not db.session.query(Music.query.filter_by(file=path).exists()).scalar():
                progress.set_postfix_str("Reading: " + path)
                try:
                    meta = TinyTag.get(path, image=True)
                    # print("Adding: ", meta)
                    new_meta = meta.as_dict()
                    new_meta['title'] = meta.title or filename
                    new_meta['album'] = meta.album or split(dirname(path))[1]
                    new_meta['albumartist'] = meta.albumartist or split(dirname(dirname(path)))[1]
                    new_meta['artist'] = meta.artist or split(dirname(dirname(path)))[1]
                    new_meta['disc'] = meta.disc or 1
                    new_meta['genre'] = meta.genre or split(dirname(dirname(dirname(path))))[1]
                    new_meta['track'] = meta.track or i + 1
                    img_hash = None
                    if image := meta.get_image():
                        img_hash = hash64(image)[0]
                        if not db.session.query(CoverImages.query.filter_by(hash=img_hash).exists()).scalar():
                            db.session.add(CoverImages(hash=img_hash, image=image))
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
                              image=img_hash))
                    db.session.flush()

                except TinyTagException as e:
                    pass
                    # print("Error: ", e)
            else:
                progress.set_postfix_str("Skipped: " + path)
    db.session.commit()


def main():
    if len(argv) > 1:
        if "-download" in argv:
            download()
        if "-drop" in argv:
            if (a := argv.index("-drop") + 1) < len(argv):
                if argv[a] == "all":
                    drop()
                elif argv[a] == "music":
                    drop_music()
        if "-users" in argv:
            users()
        if "-scan" in argv:
            scan()
        if "-help" in argv:
            print("Usage: python3 setup.py [ -download | -drop <all|music> | -users | -scan | -help ]")
    else:
        if input("Download Bootswatch Themes? [y/N]: ") == 'y':
            download()
        if inspect(db.engine).get_table_names():
            if input("Drop All Tables? [y/N]: ") == 'y':
                drop()
            elif input("Drop All Music Tables? [y/N]: ") == 'y':
                drop_music()
        db.create_all()
        db.session.commit()
        if input("Create Users? [y/N]: ") == 'y':
            users()
        if input("Search Library for Songs? [y/N]: ") == 'y':
            scan()


if __name__ == '__main__':
    main()
