#!/usr/bin/python3
import json
from hashlib import blake2b
from os.path import dirname, join, split, exists, splitext
from os import walk, makedirs
from sys import argv

import requests
from sqlalchemy import inspect, text
from tinytag import TinyTag, TinyTagException
from tqdm import tqdm
from mmh3 import hash as hash32

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


def update():
    result = [None]*4
    with db.engine.connect() as connection:
        # Create temp table
        result[0] = connection.execute(text("""create table music_dg_tmp
(
    id           INTEGER not null
        primary key,
    file         VARCHAR not null
        unique,
    title        VARCHAR,
    album        VARCHAR,
    albumartist  VARCHAR,
    artist       VARCHAR,
    audio_offset INTEGER,
    bitrate      FLOAT,
    channels     INTEGER,
    comment      VARCHAR,
    composer     VARCHAR,
    disc         VARCHAR,
    disc_total   VARCHAR,
    duration     FLOAT,
    extra        VARCHAR,
    filesize     INTEGER,
    genre        VARCHAR,
    samplerate   INTEGER,
    track        VARCHAR,
    track_total  INTEGER,
    year         INTEGER,
    image        INTEGER
        constraint music_cover_images_hash_fk
            references cover_images,
    json         VARCHAR
);"""))

        # Move into temp table
        result[1] = connection.execute(text("""
insert into music_dg_tmp(id, file, title, album, albumartist, artist, genre, year, duration, json, image, disc, track)
select id, file, title, album, album_artist, artist, genre, year, duration, json, image, disc, track
from music;"""))
        # Replace old table with temp table
        result[2] = connection.execute(text("drop table music;"))
        result[3] = connection.execute(text("alter table music_dg_tmp rename to music;"))
        if result[0] and result[1] and result[2] and result[3]:
            for m in tqdm(Music.query.all(), desc="Updating Data"):
                # json column doesn't exist as far as sqlalchemy is concerned
                data = json.loads(list(connection.execute(text(f"select json from music where id={m.id}")))[0][0])
                m.filesize = data["filesize"]
                m.album = data["album"]
                m.albumartist = data["albumartist"]
                m.artist = data["artist"]
                m.audio_offset = data["audio_offset"]
                m.bitrate = data["bitrate"]
                m.channels = data["channels"]
                m.comment = data["comment"]
                m.composer = data["composer"]
                m.disc = data["disc"]
                m.disc_total = data["disc_total"]
                m.duration = data["duration"]
                m.extra = json.dumps(data["extra"])
                m.genre = data["genre"]
                m.samplerate = data["samplerate"]
                m.title = data["title"]
                m.track = data["track"]
                m.track_total = data["track_total"]
                m.year = data["year"]
            db.session.commit()
            # Remove json column
            connection.execute(text("""create table music_dg_tmp
(
    id           INTEGER not null
        primary key,
    file         VARCHAR not null
        unique,
    title        VARCHAR,
    album        VARCHAR,
    albumartist  VARCHAR,
    artist       VARCHAR,
    audio_offset INTEGER,
    bitrate      FLOAT,
    channels     INTEGER,
    comment      VARCHAR,
    composer     VARCHAR,
    disc         VARCHAR,
    disc_total   VARCHAR,
    duration     FLOAT,
    extra        VARCHAR,
    filesize     INTEGER,
    genre        VARCHAR,
    samplerate   INTEGER,
    track        VARCHAR,
    track_total  INTEGER,
    year         INTEGER,
    image        INTEGER
        constraint music_cover_images_hash_fk
            references cover_images
);"""))
            connection.execute(text("""
insert into music_dg_tmp(id, file, title, album, albumartist, artist, audio_offset, bitrate, channels, comment,
                         composer, disc, disc_total, duration, extra, filesize, genre, samplerate, track, track_total,
                         year, image)
select id, file, title, album, albumartist, artist, audio_offset, bitrate, channels, comment, composer,
    disc, disc_total, duration, extra, filesize, genre, samplerate, track, track_total, year, image
from music;"""))
            connection.execute(text("drop table music;"))
            connection.execute(text("alter table music_dg_tmp rename to music;"))

    for image in tqdm(CoverImages.query.all(), desc="Updating Image Hashes"):
        new_hash = hash32(image.image)
        old_hash = image.hash
        image.hash = new_hash
        db.session.query(Music).filter_by(image=old_hash).update({Music.image: new_hash})
    db.session.commit()

    Meta.__table__.create(db.engine)
    if not (db_version := Meta.query.get("db_version")):
        db.session.add(Meta(key="db_version", value="0.2"))
    else:
        db_version.value = "0.2"
    db.session.commit()


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
    deleted = 0
    for id, file in (progress := tqdm(db.session.query(Music.id, Music.file).all(), desc="Finding deleted files")):
        if not exists(file):
            # print("Deleting: ", file)
            progress.set_postfix_str("Deleting: " + file)
            Music.query.filter_by(id=id).delete()
            db.session.flush()
            deleted += 1
    db.session.commit()

    created = 0
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
                    new_meta['title'] = meta.title or splitext(filename)[0]
                    new_meta['album'] = meta.album or split(dirname(path))[1]
                    new_meta['albumartist'] = meta.albumartist or split(dirname(dirname(path)))[1]
                    new_meta['artist'] = meta.artist or split(dirname(dirname(path)))[1]
                    new_meta['genre'] = meta.genre or split(dirname(dirname(dirname(path))))[1]
                    new_meta['extra'] = json.dumps(meta.extra)

                    if "audio_offest" in new_meta:
                        new_meta['audio_offset'] = new_meta['audio_offest']
                        del new_meta['audio_offest']

                    img_hash = None
                    if image := meta.get_image():
                        img_hash = hash32(image)
                        if not db.session.query(CoverImages.query.filter_by(hash=img_hash).exists()).scalar():
                            db.session.add(CoverImages(hash=img_hash, image=image))

                    db.session.add(
                        Music(file=path,
                              **new_meta,
                              image=img_hash))
                    db.session.flush()
                    created += 1

                except TinyTagException as e:
                    pass
                    # print("Error: ", e)
            else:
                progress.set_postfix_str("Skipped: " + path)
    db.session.commit()
    print("Deleted Songs:", deleted)
    print("New Songs:", created)


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
            if input("Update Database? (SQLite Recommended) [y/N]: ") == 'y':
                update()
            elif input("Drop All Tables? [y/N]: ") == 'y':
                drop()
            elif input("Drop All Music Tables? [y/N]: ") == 'y':
                drop_music()
        db.create_all()
        if not db.session.query(Meta.query.filter_by(key="db_version").exists()).scalar():
            db.session.add(Meta(key="db_version", value="0.2"))
        db.session.commit()
        if input("Create Users? [y/N]: ") == 'y':
            users()
        if input("Search Library for Songs? [y/N]: ") == 'y':
            scan()


if __name__ == '__main__':
    main()
