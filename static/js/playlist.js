"use strict";

class Playlists {

    constructor(funcs = null) {
        this.funcs = funcs
    }

    add(playlist, song, load = this.funcs?.add) {
        this.send("add", {"playlist": playlist, "item": song}, load);
    }

    remove(playlist, item, load = this.funcs?.remove) {
        this.send("add", {"playlist": playlist, "item": item}, load);
    }

    swap(playlist, items, load = this.funcs?.swap) {
        this.send("add", {"playlist": playlist, "item": items}, load);
    }

    new(name = "New Playlist", load = this.funcs?.new) {
        this.send("new", {"item": name}, load);
    }

    rename(playlist, name = "New Playlist", load = this.funcs?.rename) {
        this.send("rename", {"playlist": playlist, "item": name}, load);
    }

    delete(playlist, load = this.funcs?.delete) {
        this.send("delete", {"playlist": playlist}, load);
    }

    send(action, data, load = null) {
        console.log(action, data)
        fetch(`/playlist?action=${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        }).then((response) => {
            return response.json();
        }).then(load);
    }
}