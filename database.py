from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Meta(db.Model):
    key = db.Column(db.String, primary_key=True)
    value = db.Column(db.String)


class Users(UserMixin, db.Model):
    username = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, nullable=False)
    name = db.Column(db.String)
    theme = db.Column(db.String)

    def get_id(self):  # Required for flask-login to get the id of a user
        return self.username


class Music(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String)
    album = db.Column(db.String)
    albumartist = db.Column(db.String)
    artist = db.Column(db.String)
    audio_offset = db.Column(db.Integer)
    bitrate = db.Column(db.Float)
    channels = db.Column(db.Integer)
    comment = db.Column(db.String)
    composer = db.Column(db.String)
    disc = db.Column(db.String)
    disc_total = db.Column(db.String)
    duration = db.Column(db.Float)
    extra = db.Column(db.String)
    filesize = db.Column(db.Integer)
    genre = db.Column(db.String)
    samplerate = db.Column(db.Integer)
    track = db.Column(db.String)
    track_total = db.Column(db.String)
    year = db.Column(db.String)
    image = db.Column(db.Integer, db.ForeignKey("cover_images.hash"))


class CoverImages(db.Model):
    hash = db.Column(db.Integer, primary_key=True)
    image = db.Column(db.LargeBinary)


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user = db.Column(db.String, db.ForeignKey("users.username", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    song = db.Column(db.Integer, db.ForeignKey("music.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.DateTime)


class Queue(db.Model):
    index = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String, db.ForeignKey("users.username", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    song = db.Column(db.Integer, db.ForeignKey("music.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)


class Playlists(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user = db.Column(db.String, db.ForeignKey("users.username", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String)


class PlaylistSongs(db.Model):
    playlist = db.Column(db.Integer, db.ForeignKey("playlists.id", onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    index = db.Column(db.Integer, primary_key=True)
    song = db.Column(db.Integer, db.ForeignKey("music.id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
