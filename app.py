import imghdr
import json
from datetime import datetime
from hashlib import blake2b
from os import environ
from os.path import split, dirname

from flask import Flask, render_template, request, Response, send_file, flash, redirect, url_for
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import func, desc, or_
from tinytag import TinyTag, TinyTagException

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
                                new_meta['disc'] = meta.disc
                                new_meta['genre'] = meta.genre or split(dirname(dirname(dirname(new_path))))[1]
                                new_meta['track'] = meta.track
                                db.session.add(
                                    Music(file=new_path,
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
            if not event.is_directory:
                app.logger.info("File Deleted - '%s'", event.src_path)
                with app.app_context():
                    Music.query.filter_by(file=event.src_path).delete()
                    db.session.commit()

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
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = Users.query.get(form.username.data)
        if user is None or user.password != blake2b(bytes(form.password.data, "utf-8")).hexdigest():
            flash("Invalid username or password", "warning")
            app.logger.info("%s - username '%s' failed to log in", request.remote_addr, form.username.data)
            return redirect(url_for('login'))
        else:
            login_user(user, remember=form.remember_me.data)
            app.logger.info("%s - username '%s' logged in successfully", request.remote_addr, form.username.data)
            return redirect(request.args.get("next") or url_for('home'))
    return render_template('login.html', title="Login", form=form, disable=True)


@app.route('/user', methods=['POST'])
@login_required
def user_data():
    form = UserData(firstName=current_user.firstName, lastName=current_user.lastName, theme=current_user.theme)
    if form.validate_on_submit():
        user = Users.query.get(current_user.username)
        user.firstName = form.firstName.data
        user.lastName = form.lastName.data
        user.password = blake2b(bytes(form.password.data, "utf-8")).hexdigest()
        user.theme = form.theme.data
        db.session.commit()
    return redirect(request.args.get("next") or url_for('home'))


@app.route('/queue', methods=['POST'])
@login_required
def queue():
    data = request.json
    app.logger.debug("Queue - '%s' = '%s'", current_user.username, data)
    db.session.execute(Queue.__table__.delete().where(Queue.user == current_user.username))
    for index, song_id in enumerate(data):
        db.session.add(Queue(index=index, user=current_user.username, song=song_id))
    db.session.commit()
    return '200 OK'


@app.route('/search')
@login_required
def search():
    s_query = request.args.get("q")
    app.logger.debug("Search - '%s' = '%s'", current_user.username, s_query)
    songs = {k: json.loads(v) for k, v in db.session.query(Music.id, Music.json).filter(
        or_(Music.title.ilike(f"%{s_query}%"), Music.artist.ilike(f"%{s_query}%"))).all()} if s_query else {}

    user_queue = {k: json.loads(v) for k, v in db.session.query(Music.id, Music.json)
        .filter(Music.id == Queue.song).filter(Queue.user == current_user.username).order_by(Queue.index).all()}

    return render_template("search.html", title="Home", theme=request.args.get("theme") or current_user.theme,
                           query=s_query, results=songs, songs=songs | user_queue, queue=list(user_queue.keys()),
                           form=UserData(firstName=current_user.firstName, lastName=current_user.lastName,
                                         theme=current_user.theme))


@app.route("/logout")
@login_required
def logout():
    app.logger.info("%s = '%s' logged out", request.remote_addr, current_user.username)
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def home():
    top = {k: json.loads(v) for k, v in db.session.query(Music.id, Music.json)
        .filter(Music.id == History.song).filter(History.user == current_user.username)
        .group_by(History.song).order_by(desc(func.count(History.song))).limit(10).all()}

    last = {k: json.loads(v) for k, v in db.session.query(Music.id, Music.json).distinct(Music.id)
        .filter(Music.id == History.song).filter(History.user == current_user.username)
        .order_by(desc(History.date)).limit(10).all()}

    user_queue = {k: json.loads(v) for k, v in db.session.query(Music.id, Music.json)
        .filter(Music.id == Queue.song).filter(Queue.user == current_user.username).order_by(Queue.index).all()}

    return render_template("home.html", title="Home", theme=request.args.get("theme") or current_user.theme,
                           top_songs=top, last_songs=last, songs=top | last | user_queue,
                           queue=list(user_queue.keys()),
                           form=UserData(firstName=current_user.firstName, lastName=current_user.lastName,
                                         theme=current_user.theme))


@app.route('/albums')
@login_required
def albums():
    user_queue = {k: json.loads(v) for k, v in db.session.query(Queue.song, Music.json)
        .filter(Music.id == Queue.song).filter(Queue.user == current_user.username).order_by(Queue.index).all()}

    return render_template("albums.html", title="Albums", theme=request.args.get("theme") or current_user.theme,
                           albums={k: json.loads(v) for k, v in
                                   db.session.query(Music.id, Music.json).group_by(Music.album).order_by(Music.album)},
                           songs=user_queue, queue=list(user_queue.keys()),
                           form=UserData(firstName=current_user.firstName, lastName=current_user.lastName,
                                         theme=current_user.theme))


@app.route('/albums/<int:song_id>')
@login_required
def album(song_id):
    user_queue = {k: json.loads(v) for k, v in db.session.query(Queue.song, Music.json)
        .filter(Music.id == Queue.song).filter(Queue.user == current_user.username).order_by(Queue.index).all()}

    album_songs = {k: json.loads(v) for k, v in db.session.query(Music.id, Music.json)
        .filter(
        Music.album == (db.session.query(Music.album).filter_by(id=song_id).scalar_subquery()))
        .order_by(Music.disc, func.length(Music.track), Music.track)}

    return render_template("album.html", title=list(album_songs.values())[0]['album'],
                           theme=request.args.get("theme") or current_user.theme,
                           album_songs=album_songs, songs=album_songs | user_queue, queue=list(user_queue.keys()),
                           form=UserData(firstName=current_user.firstName, lastName=current_user.lastName,
                                         theme=current_user.theme))


@app.route('/artists')
@login_required
def artists():
    user_queue = {k: json.loads(v) for k, v in db.session.query(Queue.song, Music.json)
        .filter(Music.id == Queue.song).filter(Queue.user == current_user.username).order_by(Queue.index).all()}

    return render_template("artists.html", title="Artists", theme=request.args.get("theme") or current_user.theme,
                           artists={k: json.loads(v) for k, v in
                                    db.session.query(Music.id, Music.json).group_by(Music.artist)
                           .order_by(Music.artist)},
                           songs=user_queue, queue=list(user_queue.keys()),
                           form=UserData(firstName=current_user.firstName, lastName=current_user.lastName,
                                         theme=current_user.theme))


@app.route('/artists/<int:song_id>')
@login_required
def artist(song_id):
    user_queue = {k: json.loads(v) for k, v in db.session.query(Queue.song, Music.json)
        .filter(Music.id == Queue.song).filter(Queue.user == current_user.username).order_by(Queue.index).all()}

    query = db.session.query(Music.id, Music.json) \
        .filter(Music.artist == (db.session.query(Music.artist).filter_by(id=song_id).scalar_subquery()))

    artist_songs = {k: json.loads(v) for k, v in
                    query.order_by(Music.album, Music.disc, func.length(Music.track),
                                   Music.track)}

    return render_template("artist.html", title=list(artist_songs.values())[0]['artist'], theme=request.args.get("theme") or current_user.theme,
                           albums={k: json.loads(v) for k, v in query.group_by(Music.album).order_by(Music.album)},
                           songs=artist_songs | user_queue, artist=artist_songs, queue=list(user_queue.keys()),
                           form=UserData(firstName=current_user.firstName, lastName=current_user.lastName,
                                         theme=current_user.theme))


@app.route('/song/<int:song_id>')
@login_required
def song(song_id: int):
    if request.args.get("meta"):
        return Response(db.session.query(Music.json).filter_by(id=song_id).scalar(), mimetype="application/json")
    elif request.args.get("image"):
        if image := db.session.query(Music.image).filter_by(id=song_id).scalar():
            # mime = imghdr.what(image, h=image[:32])
            mime = imghdr.what(None, h=image[:32])
            return Response(image, mimetype="image/" + (mime or "unknown"))
        return send_file("static/img/blank.svg")
    elif request.args.get("listen"):
        listen = History(user=current_user.username, song=song_id, date=datetime.now())
        db.session.add(listen)
        db.session.commit()
        return Response(str(listen.id), mimetype="application/json")
    else:
        return send_file(db.session.query(Music.file).filter_by(id=song_id).scalar())


if __name__ == '__main__':
    app.run()
