import imghdr
import json
from datetime import datetime
from hashlib import blake2b
from os import environ
from os.path import split, dirname

from flask import Flask, render_template, request, Response, send_file, flash, redirect, url_for, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import func, desc, or_, and_
from tinytag import TinyTag, TinyTagException
from mmh3 import hash as hash32

from database import *
from forms import *

settings = json.load(open("settings.json"))

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = settings['database']
app.config["SECRET_KEY"] = settings['secret_key']

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)

if "gunicorn" in environ.get("SERVER_SOFTWARE", ""):
    import logging

    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

if settings['watchdog']:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers.polling import PollingObserver


    class WatchdogHandler(FileSystemEventHandler):
        @staticmethod
        def create(new_path):
            if not any(split(new_path)[1].startswith(item) for item in settings["ignore_prefix"]):
                with app.app_context():
                    if not db.session.query(Music.query.filter_by(file=new_path).exists()).scalar():
                        try:
                            meta = TinyTag.get(new_path, image=True)
                            app.logger.debug(meta)
                            if meta.filesize:
                                new_meta = meta.as_dict()
                                new_meta['title'] = meta.title or split(new_path)[1]
                                new_meta['album'] = meta.album or split(dirname(new_path))[1]
                                new_meta['albumartist'] = meta.albumartist or split(dirname(dirname(new_path)))[1]
                                new_meta['artist'] = meta.artist or split(dirname(dirname(new_path)))[1]
                                new_meta['genre'] = meta.genre or split(dirname(dirname(dirname(new_path))))[1]
                                new_meta['extra'] = json.dumps(meta.extra)

                                img_hash = None
                                if image := meta.get_image():
                                    img_hash = hash32(image)
                                    if not db.session.query(
                                            CoverImages.query.filter_by(hash=img_hash).exists()).scalar():
                                        db.session.add(CoverImages(hash=img_hash, image=image))

                                db.session.add(
                                    Music(file=new_path,
                                          **new_meta,
                                          image=img_hash))
                                db.session.commit()

                        except TinyTagException as e:
                            app.logger.warning(e)

                        except FileNotFoundError as e:
                            app.logger.warning(e)

        def on_created(self, event):
            if not event.is_directory:
                app.logger.info("File Created - '%s'", event.src_path)
                self.create(event.src_path)

        def on_deleted(self, event):
            if settings["delete_allowed"]:
                if not event.is_directory:
                    app.logger.info("File Deleted - '%s'", event.src_path)
                    with app.app_context():
                        Music.query.filter_by(file=event.src_path).delete()
                        db.session.commit()
                else:
                    if event.src_path == settings["library"]:
                        settings["delete_allowed"] = False
                        app.logger.error("Library was removed, deletion disabled, restart to re-enable")
                        app.logger.warning("To remove all songs, drop tables in setup.py")

        def on_moved(self, event):
            if not event.is_directory:
                app.logger.info("File Moved - '%s' to '%s'", event.src_path, event.dest_path)
                with app.app_context():
                    item = Music.query.filter_by(file=event.src_path).scalar()
                    if item is not None:
                        item.file = event.dest_path
                        db.session.commit()
                    else:
                        self.create(event.dest_path)


    event_handler = WatchdogHandler()
    observer = PollingObserver()
    observer.schedule(event_handler, path=settings['library'], recursive=True)
    app.logger.info("Starting Watchdog")
    observer.start()


def dict_row(raw_row):
    row = raw_row.__dict__
    del row['_sa_instance_state']
    return row


def json_row(row):
    return json.dumps(dict_row(row))


def get_user_queue():
    return {k: dict_row(v) for k, v in db.session.query(Music.id, Music)
        .join(Queue, and_(Music.id == Queue.song, Queue.user == current_user.username))
        .order_by(Queue.index).all()}


def get_user_playlists():
    return db.session.query(Playlists.id, Playlists.name).filter_by(user=current_user.username).all()


@app.context_processor
def inject_vars():
    if current_user.is_authenticated:
        return dict(
            theme=request.args.get("theme") or current_user.theme,
            form=UserData(name=current_user.name, theme=current_user.theme),
            playlists=get_user_playlists(),
            # queue=list(user_queue().keys())
        )
    return []


@app.template_filter()
def format_time(time):
    if time is None:
        return time
    mins, secs = divmod(time, 60)
    if time > 3600:
        hours, mins = divmod(mins, 60)
        return f"{hours:.0f}:{mins:02.0f}:{secs:02.0f}"
    else:
        return f"{mins:.0f}:{secs:02.0f}"


@login_manager.user_loader
def load_user(user_id: int):
    return Users.query.get(user_id)


@login_manager.unauthorized_handler
def unauthorized_callback(message=None):  # Redirect if not logged in
    if message:
        flash(message, "warning")
    return redirect('/login?next=' + request.full_path)


@app.route('/login', methods=['GET', 'POST'])
def route_login():
    if current_user.is_authenticated:
        return redirect(url_for('route_home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.get(form.username.data)
        if user is None or user.password != blake2b(bytes(form.password.data, "utf-8")).hexdigest():
            flash("Invalid username or password", "warning")
            app.logger.info("%s - username '%s' failed to log in", request.remote_addr, form.username.data)
            return redirect(url_for('route_login'))
        else:
            login_user(user, remember=form.remember_me.data)
            app.logger.info("%s - username '%s' logged in successfully", request.remote_addr, form.username.data)
            return redirect(request.args.get("next") or url_for('route_home'))
    return render_template('login.html', title="Login", form=form)


@app.route('/user', methods=['POST'])
@login_required
def route_user():
    form = UserData(name=current_user.name, theme=current_user.theme)
    if form.validate_on_submit():
        user = Users.query.get(current_user.username)
        if form.name.data:
            user.name = form.name.data
        if form.password.data:
            user.password = blake2b(bytes(form.password.data, "utf-8")).hexdigest()
        if form.theme.data:
            user.theme = form.theme.data
        db.session.commit()
    return redirect(request.args.get("next") or url_for('route_home'))


@app.route('/queue', methods=['POST'])
@login_required
def route_queue():
    data = request.json
    app.logger.debug("Queue - '%s' = '%s'", current_user.username, data)
    db.session.execute(Queue.__table__.delete().where(Queue.user == current_user.username))
    for index, song_id in enumerate(data):
        db.session.add(Queue(index=index, user=current_user.username, song=song_id))
    db.session.commit()
    return '200 OK'


@app.route('/playlist', methods=['POST'])
@login_required
def route_playlist():
    data = request.json
    action = request.args.get("action")
    app.logger.debug("Playlist - '%s' = '%s' with '%s'", current_user.username, action, data)
    if ((list_id := data.get("playlist")) and db.session.query(
            Playlists.query.filter_by(id=data["playlist"], user=current_user.username).exists()).scalar()) \
            or action == "new":
        if action == "get":
            return Response(json.dumps(PlaylistSongs.query.filter_by(playlist=list_id).all()),
                            mimetype="application/json")
        elif action == "delete":
            PlaylistSongs.query.filter_by(playlist=list_id).delete()
            Playlists.query.filter_by(id=list_id, user=current_user.username).delete()
            db.session.commit()
            return '200'
        elif item := data.get("item"):
            if action == "add":
                index = (db.session.query(func.max(PlaylistSongs.index)).filter_by(playlist=list_id).scalar() or 0) + 1
                new = PlaylistSongs(index=index, playlist=list_id, song=item)
                db.session.add(new)
                db.session.commit()
                return Response(str(new.index), mimetype="application/json")
            elif action == "remove":
                num_rows = PlaylistSongs.query.filter_by(index=item, playlist=list_id).delete()
                db.session.flush()
                songs = PlaylistSongs.query.filter_by(playlist=list_id).all()
                for i, song in enumerate(songs, start=1):
                    song.index = i
                db.session.commit()
                return '200' if num_rows else abort(400)
            elif action == "move":
                for i in range(item[0], item[0] + item[1], inc := (1 if item[1] > 0 else -1)):
                    old = PlaylistSongs.query.filter_by(index=i, playlist=list_id).scalar()
                    new = PlaylistSongs.query.filter_by(index=i + inc, playlist=list_id).scalar()
                    old.song, new.song = new.song, old.song
                    db.session.flush()
                db.session.commit()
                return '200'
            elif action == "new":
                new = Playlists(user=current_user.username, name=item)
                db.session.add(new)
                db.session.commit()
                return Response(str(new.id), mimetype="application/json")
            elif action == "rename":
                playlist = Playlists.query.filter_by(id=list_id, user=current_user.username).scalar()
                playlist.name = item
                db.session.commit()
                return '200'
        elif items := data.get("items"):
            return_var = []
            for item in items:
                if action == "add":
                    index = (db.session.query(func.max(PlaylistSongs.index)).filter_by(
                        playlist=list_id).scalar() or 0) + 1
                    new = PlaylistSongs(index=index, playlist=list_id, song=item)
                    db.session.add(new)
                    db.session.flush()
                    return_var.append(new.index)
                elif action == "remove":
                    PlaylistSongs.query.filter_by(index=item, playlist=list_id).delete()
                    db.session.flush()
                    return_var.append('200')
                elif action == "new":
                    new = Playlists(user=current_user.username, name=item)
                    db.session.add(new)
                    db.session.flush()
                    return_var.append(new.id)
            db.session.commit()
            return Response(json.dumps(return_var), mimetype="application/json")
    else:
        return abort(403)

    return abort(400)


@app.route('/search')
@login_required
def route_search():
    s_query = request.args.get("q")
    app.logger.debug("Search - '%s' = '%s'", current_user.username, s_query)
    songs = {k: dict_row(v) for k, v in db.session.query(Music.id, Music).filter(
        or_(Music.title.ilike(f"%{s_query}%"), Music.artist.ilike(f"%{s_query}%"),
            Music.albumartist.ilike(f"%{s_query}%"), Music.composer.ilike(f"%{s_query}%"),
            Music.comment.ilike(f"%{s_query}%"), Music.genre.ilike(f"%{s_query}%"),
            Music.file.ilike(f"%{s_query}%"))).all()
             } if s_query else {}

    user_queue = get_user_queue()

    return render_template("search.html", title="Search",
                           query=s_query, results=songs, songs=songs | user_queue, queue=list(user_queue.keys()))


@app.route("/logout")
@login_required
def route_logout():
    app.logger.info("%s = '%s' logged out", request.remote_addr, current_user.username)
    logout_user()
    return redirect(url_for('route_login'))


@app.route('/')
@login_required
def route_home():
    top = {k: dict_row(v) for k, v in db.session.query(Music.id, Music)
        .join(History, and_(Music.id == History.song, History.user == current_user.username))
        .group_by(History.song).order_by(desc(func.count(History.song))).limit(10).all()}

    last = {k: dict_row(v) for k, v in db.session.query(Music.id, Music).distinct(History.song)
        .join(History, and_(Music.id == History.song, History.user == current_user.username))
        .order_by(desc(History.date)).limit(10).all()}

    user_queue = get_user_queue()

    playlists = db.session.query(Playlists.id, Playlists.name, func.count(PlaylistSongs.song), func.sum(Music.duration)) \
        .filter_by(user=current_user.username) \
        .join(PlaylistSongs, Playlists.id == PlaylistSongs.playlist, isouter=True) \
        .join(Music, PlaylistSongs.song == Music.id, isouter=True).group_by(Playlists.id).all()

    return render_template("home.html", title="Home",
                           top_songs=top, last_songs=last, songs=top | last | user_queue,
                           queue=list(user_queue.keys()), playlists=playlists)


@app.route('/playlists/<int:playlist_id>')
@login_required
def route_playlists(playlist_id: int):
    user_queue = get_user_queue()

    if playlist := Playlists.query.filter_by(id=playlist_id, user=current_user.username).scalar():
        playlist_songs = {k: dict_row(v) for k, v in db.session.query(Music.id, Music)
            .join(PlaylistSongs, and_(PlaylistSongs.playlist == playlist_id, Music.id == PlaylistSongs.song))
            .order_by(PlaylistSongs.index).all()}

        playlist_list = db.session.query(PlaylistSongs.song).filter_by(playlist=playlist_id).order_by(
            PlaylistSongs.index).all()

        return render_template("playlist.html", title=playlist.name, playlist=playlist,
                               playlist_songs=playlist_songs, playlist_list=playlist_list,
                               songs=playlist_songs | user_queue, queue=list(user_queue.keys()))
    return abort(403)


@app.route('/albums')
@login_required
def route_albums():
    user_queue = get_user_queue()

    return render_template("albums.html", title="Albums", theme=request.args.get("theme") or current_user.theme,
                           albums={k: dict_row(v) for k, v in
                                   db.session.query(Music.id, Music).group_by(Music.album).order_by(Music.album)},
                           songs=user_queue, queue=list(user_queue.keys()))


@app.route('/albums/<int:song_id>')
@login_required
def route_album(song_id: int):
    user_queue = get_user_queue()

    album_songs = {k: dict_row(v) for k, v in db.session.query(Music.id, Music)
        .filter(
        Music.album == (db.session.query(Music.album).filter_by(id=song_id).scalar_subquery()))
        .order_by(Music.disc, func.length(Music.track), Music.track)}

    return render_template("album.html", title=list(album_songs.values())[0]['album'],
                           album_songs=album_songs, songs=album_songs | user_queue, queue=list(user_queue.keys()))


@app.route('/artists')
@login_required
def route_artists():
    user_queue = get_user_queue()

    return render_template("artists.html", title="Artists", theme=request.args.get("theme") or current_user.theme,
                           artists={k: dict_row(v) for k, v in
                                    db.session.query(Music.id, Music).group_by(Music.artist)
                           .order_by(Music.artist)},
                           songs=user_queue, queue=list(user_queue.keys()))


@app.route('/artists/<int:song_id>')
@login_required
def route_artist(song_id: int):
    user_queue = get_user_queue()

    query = db.session.query(Music.id, Music) \
        .filter(Music.artist == (db.session.query(Music.artist).filter_by(id=song_id).scalar_subquery()))

    artist_songs = {k: dict_row(v) for k, v in
                    query.order_by(Music.album, Music.disc, func.length(Music.track),
                                   Music.track)}

    return render_template("artist.html", title=list(artist_songs.values())[0]['artist'],
                           albums={k: dict_row(v) for k, v in query.group_by(Music.album).order_by(Music.album)},
                           songs=artist_songs | user_queue, artist=artist_songs, queue=list(user_queue.keys()))


@app.route('/song/<int:song_id>')
@app.route('/song/<int:song_id>/<string:action>')
@login_required
def route_song(song_id: int, action=None):
    if action == "meta":
        return Response(json_row(Music.query.get(song_id)), mimetype="application/json")
    elif action == "image":
        if image := db.session.query(CoverImages.image).join(Music, Music.image == CoverImages.hash).filter_by(
                id=song_id).scalar():
            # mime = imghdr.what(image, h=image[:32])
            mime = imghdr.what(None, h=image[:32])
            return Response(image, mimetype="image/" + (mime or "unknown"))
        return send_file("static/img/blank.svg")
    elif action == "listen":
        listen = History(user=current_user.username, song=song_id, date=datetime.now())
        db.session.add(listen)
        db.session.commit()
        return Response(str(listen.id), mimetype="application/json")
    else:
        return send_file(db.session.query(Music.file).filter_by(id=song_id).scalar())


@app.route('/image/<image_hash>')
@login_required
def route_image(image_hash):
    if image := db.session.query(CoverImages.image).filter_by(hash=image_hash).scalar():
        # mime = imghdr.what(image, h=image[:32])
        mime = imghdr.what(None, h=image[:32])
        return Response(image, mimetype="image/" + (mime or "unknown"))
    return send_file("static/img/blank.svg")


if __name__ == '__main__':
    app.run()
