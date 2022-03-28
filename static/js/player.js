"use strict";
let songs = JSON.parse(document.getElementById('songs').innerText);
let queue = new Queue(JSON.parse(document.getElementById('user_queue').innerText));
let playlists = new Playlists();

class Player {
    constructor(audio = new Audio()) {
        this.audio = audio;

        this.audio.addEventListener("loadedmetadata", () => {
            slider.max = this.audio.duration;
            max_time.innerText = format_time(this.audio.duration);
            // this.display(id, false);
        });

        this.audio.addEventListener("play", () => {
            button.classList.remove("bi-play-fill");
            button.classList.add("bi-pause-fill");
            slider.value = this.audio.currentTime;
            current_time.innerText = format_time(this.audio.currentTime);
            this.audio.muted = volume.disabled;
            if (!this.fading)
                this.audio.volume = this.volume;
            if ("mediaSession" in navigator) {
                navigator.mediaSession.playbackState = "playing";
                if (this.audio && (this.audio.duration || this.audio.duration === 0) && this.audio.playbackRate && this.audio.currentTime) {
                    navigator.mediaSession.setPositionState({
                        duration: this.audio.duration,
                        playbackRate: this.audio.playbackRate,
                        position: this.audio.currentTime
                    });
                }
            }

            let last_time = Math.floor(this.audio.currentTime);

            this.interval = setInterval(() => {
                let duration = this.audio.duration;
                let playbackRate = this.audio.playbackRate;
                let currentTime = this.audio.currentTime;
                slider.value = currentTime;
                if ((duration || duration === 0) && playbackRate && currentTime) {
                    navigator.mediaSession.setPositionState({
                        duration: duration,
                        playbackRate: playbackRate,
                        position: currentTime
                    });
                }
                if (last_time !== Math.floor(currentTime)) {
                    last_time = Math.floor(currentTime);
                    current_time.innerText = format_time(currentTime);
                }

                // slider.style.setProperty("--buffered", `${(this.audio.buffered.end(player.audio.buffered.length-1) / duration)*100}%`)

            }, 50);
        });

        this.audio.addEventListener("pause", () => {
            button.classList.remove("bi-pause-fill");
            button.classList.add("bi-play-fill");
            if ("mediaSession" in navigator)
                navigator.mediaSession.playbackState = "paused";
            clearInterval(this.interval);
        });

        this.audio.addEventListener("ended", (e) => {
            if ("mediaSession" in navigator)
                navigator.mediaSession.playbackState = "none";
            clearInterval(this.interval);
            if (this.looping === 1)
                queue.push(queue.current);
            queue.current = null;
            if (queue.length) {
                this.start(queue.next);
            } else {
                e.target.pause();
            }
        });
    }

    interval;
    volume = 1;
    looping = 0;
    fading = false;

    get paused() {
        return this.audio.paused;
    };

    get time() {
        return this.audio.currentTime;
    };

    set time(t) {
        this.audio.currentTime = t;
    };

    get muted() {
        return this.audio.muted;
    };

    set muted(m) {
        this.audio.muted = m;
    };

    get duration() {
        return this.audio.duration;
    };

    set set_volume(vol) {
        this.volume = vol;
        this.audio.volume = vol;
    }

    // Play a song setting up the queue
    start(id = queue.next, push = true) {
        if (!this.audio.paused)
            this.audio.pause();
        this.audio.src = `/song/${id}`;

        this.play(false, id, () => {
            if (queue.next === id)
                queue.shift();
            if (push)
                queue.play(id);
            this.display(id);

            let xhr = new XMLHttpRequest();
            xhr.open("GET", `/song/${id}/listen`, true);
            xhr.send();
        });
    }

    play(fast = false, id = queue.current, run = Function()) {
        this.audio.play().then(() => {
            run();

            if ("mediaSession" in navigator) {
                navigator.mediaSession.playbackState = 'playing';

                let song = songs[id];

                navigator.mediaSession.metadata = new MediaMetadata({
                    title: song.title,
                    artist: song.artist,
                    album: song.album,
                    artwork: [
                        {src: `/image/${song.image}`}
                    ]
                });

                navigator.mediaSession.setPositionState({
                    duration: this.audio.duration,
                    playbackRate: this.audio.playbackRate,
                    position: this.audio.currentTime
                });
            }

        }).catch((error) => {
            console.error(error);
            show_toast(`An Error Occurred: ${error.message}`);
            button.classList.remove("bi-pause-fill");
            button.classList.add("bi-play-fill");
            if ("mediaSession" in navigator)
                navigator.mediaSession.playbackState = "none";
            clearInterval(this.interval);
        });

        if (!fast) {
            this.fading = true;
            this.audio.volume = 0;
            let vol_interval = setInterval(() => {
                if (this.audio.volume + 0.05 < this.volume) {
                    this.audio.volume += 0.05;
                } else {
                    this.audio.volume = this.volume;
                    this.fading = false;
                    clearInterval(vol_interval);
                }
            }, 10);
        } else {
            this.audio.volume = this.volume;
        }

    }

    pause(fast = false) {
        if (fast) {
            this.audio.pause();
        } else {
            this.fading = true;
            let vol_interval = setInterval(() => {
                if (this.audio.volume - 0.05 > 0) {
                    this.audio.volume -= 0.05;
                } else {
                    this.audio.pause();
                    this.fading = false;
                    clearInterval(vol_interval);
                }
            }, 10);
        }
    }

    // Toggle play & pause
    toggle() {
        if (queue.current == null) this.start();
        else this.audio.paused ? this.play() : this.pause();
    }


    loop() {
        this.looping++;
        switch (this.looping) {
            case 1: // On
                show_toast("Looping Queue");
                loop_button.classList.remove('off', 'one');
                this.audio.loop = false;
                break;
            case 2: // 1 song
                show_toast("Looping Song");
                loop_button.classList.remove('off');
                loop_button.classList.add('one');
                this.audio.loop = true;
                break;
            default:
                show_toast("Looping Off");
                this.looping = 0;
                loop_button.classList.remove('one');
                loop_button.classList.add('off');
                this.audio.loop = false;
                break;
        }
    }

    // Update the currently playing display
    display(id = queue.current, time = true) {
        const song_info = elem_id("info");
        const song_image = elem_id("image");
        const song_title = elem_id("title");
        const song_artist = elem_id("artist");

        if (id != null) {
            let song = songs[id];
            song_image.src = `/image/${song.image}`;
            song_title.innerText = song.title;
            song_artist.innerText = song.artist;
            song_info.title = `${song.file.split('.').pop().toUpperCase()}, ${(song.filesize / 1048576).toFixed(1)}MB, ${song.samplerate / 1000}KHz, ${song.bitrate.toFixed(1)}kbps`;
            song_info.classList.remove("invisible");
            if (time) {
                slider.max = song.duration;
                max_time.innerText = format_time(song.duration);
            }
        }
        update_big_player();
    }
}

let player = new Player();

// TODO: Make this not a mess

let button = elem_id("play");
let loop_button = elem_id("loop");
let shuffle_button = elem_id("shuffle");
let back_button = elem_id("back");
let forward_button = elem_id("forward");

let slider = elem_id("slider");
let volume = elem_id("volume");
let mute = elem_id("mute");
let current_time = elem_id("current_time");
let max_time = elem_id("max_time");


slider.addEventListener("mousedown", (e) => {
    if (queue.current && e.button === 0 && !player.paused)
        player.pause(true);
});
slider.addEventListener("touchstart", () => {
    if (queue.current && !player.paused)
        player.pause(true);
});
slider.addEventListener("mouseup", (e) => {
    if (queue.current && e.button === 0 && player.paused)
        player.play(true);
});
slider.addEventListener("touchend", () => {
    if (queue.current && player.paused)
        player.play(true);
});

slider.addEventListener("input", (e) => {
    player.time = e.target.value;
    current_time.innerText = format_time(e.target.value);
    if ("mediaSession" in navigator && this.audio && (this.audio.duration || this.audio.duration === 0) && this.audio.playbackRate && this.audio.currentTime)
        navigator.mediaSession.setPositionState({
            duration: this.audio.duration,
            playbackRate: this.audio.playbackRate,
            position: this.audio.currentTime
        });
});

queue_button.addEventListener("click", () => {
    if (window.location.hash !== "#queue")
        open_big_player();
    else
        window.history.back();
});

volume.addEventListener("change", (e) => {
    player.set_volume = e.target.value;
    e.target.title = Math.round(e.target.value * 100) + '%';
    localStorage.setItem('volume', e.target.value);
});
volume.addEventListener("input", (e) => {
    player.set_volume = e.target.value;
    e.target.title = Math.round(e.target.value * 100) + '%';
});
mute.addEventListener("click", (e) => {
    player.muted = !player.muted;
    volume.disabled = player.muted;
    if (player.muted) {
        e.target.classList.remove("bi-volume-up-fill");
        e.target.classList.add("bi-volume-mute-fill");
    } else {
        e.target.classList.remove("bi-volume-mute-fill");
        e.target.classList.add("bi-volume-up-fill");
    }
});


if ("mediaSession" in navigator) {
    navigator.mediaSession.setActionHandler('play', () => {
        if (queue.current == null) player.start();
        else player.play();
    });
    navigator.mediaSession.setActionHandler('pause', () => player.pause());
    navigator.mediaSession.setActionHandler('stop', () => player.pause());
    navigator.mediaSession.setActionHandler('seekbackward', (e) => player.time = Math.max(player.time - (e.seekOffset || 10), 0));
    navigator.mediaSession.setActionHandler('seekforward', (e) => player.time = Math.min(player.time + (e.seekOffset || 10), player.duration));
    navigator.mediaSession.setActionHandler('seekto', (e) => {
        player.time = e.seekTime;
    });
    navigator.mediaSession.setActionHandler('previoustrack', () => player.start(queue.play_prev(), false));
    navigator.mediaSession.setActionHandler('nexttrack', () => {
        if (queue.length) player.start(queue.shift());
        else player.time = player.duration;
    });
}

button.addEventListener("click", () => player.toggle());
loop_button.addEventListener("click", () => player.loop());
shuffle_button.addEventListener("click", () => {
    queue.shuffle();
    show_toast("Shuffled Queue");
});
forward_button.addEventListener("click", () => {
    if (queue.length) player.start(queue.shift());
    else player.time = player.duration;
});
back_button.addEventListener("click", () => player.start(queue.play_prev(), false));

window.addEventListener('popstate', (e) => {
    if (window.location.hash === "#queue") open_big_player(false);
    else if ("page" in e.state) page(e.state.page, false);
});


let drag = new Drag();

function load() {
    let new_volume = localStorage.getItem('volume') || 1;
    player.set_volume = new_volume;
    volume.value = new_volume;
    volume.title = Math.round(new_volume * 100) + '%';
    if (window.location.hash === "#queue"){
        window.history.replaceState(window.history.state, null, window.location.pathname);
        open_big_player();
    }
    player.display(queue.next);
}

load();
