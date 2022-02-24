"use strict";

class Playlists {
    constructor(funcs = null) {
        this.funcs = funcs
    }

    add(playlist, song, load = this.funcs?.add) {
        this.send("add", {"playlist": playlist, "item": song}, load);
    }

    remove(playlist, item, load = this.funcs?.remove) {
        this.send("remove", {"playlist": playlist, "item": item}, load);
    }

    swap(playlist, items, load = this.funcs?.swap) {
        this.send("swap", {"playlist": playlist, "item": items}, load);
    }

    new(name = "New Playlist", load = this.funcs?.new) {
        this.send("new", {"item": name}, (id) => {
            document.querySelectorAll(`.playlists`).forEach((e) => {
                let item = document.createElement("a");
                item.classList.add("dropdown-item");
                item.setAttribute("role", "button");
                item.setAttribute("data-id", id);
                item.onclick = () => {
                    playlists.add(id, selected);
                };
                item.innerText = "New Playlist";
                e.appendChild(document.createElement("li").appendChild(item))
            });
        });
    }

    rename(playlist, name = "New Playlist", load = this.funcs?.rename) {
        this.send("rename", {"playlist": playlist, "item": name}, () => {
            document.querySelectorAll(`.playlists [data-id=${playlist}]`).forEach((e) => e.innerText = name);
        });
    }

    delete(playlist, load = this.funcs?.delete) {
        this.send("delete", {"playlist": playlist}, () => {
            document.querySelectorAll(`.playlists [data-id="${playlist}"]`).forEach((e) => e.remove());
        });
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