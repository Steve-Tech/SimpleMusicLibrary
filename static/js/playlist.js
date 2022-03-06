"use strict";

class Playlists {
    add(playlist, song) {
        this.send("add", {"playlist": playlist, [Array.isArray(song)?"items":"item"]: song});
    }

    remove(playlist, item) {
        this.send("remove", {"playlist": playlist, [Array.isArray(item)?"items":"item"]: item});
    }

    move(playlist, item, inc) {
        this.send("move", {"playlist": playlist, "item": [item, inc]});
    }

    new(name = "New Playlist") {
        this.send("new", {"item": name}, (id) => {
            document.querySelectorAll(".playlists").forEach((e) => {
                let item = document.createElement("a");
                item.classList.add("dropdown-item");
                item.setAttribute("role", "button");
                item.setAttribute("data-id", id);
                if (!item.classList.contains("playlist-all"))
                    item.onclick = () => playlists.add(id, menus.selected);
                else
                    item.onclick = () => playlists.add(id, get_all(), true);
                item.innerText = "New Playlist";
                e.appendChild(document.createElement("li").appendChild(item));
            });
        });
    }

    rename(playlist, name = "New Playlist") {
        this.send("rename", {"playlist": playlist, "item": name}, () => {
            document.querySelectorAll(`.playlists [data-id="${playlist}"]`).forEach((e) => e.innerText = name);
        });
    }

    delete(playlist) {
        this.send("delete", {"playlist": playlist}, () => {
            document.querySelectorAll(`.playlists [data-id="${playlist}"]`).forEach((e) => e.remove());
        });
    }

    send(action, data, load = null) {
        console.log(action, data);
        fetch(`/playlist?action=${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        }).then((response) => {
            if (response.ok)
                return response.json();
            else
                throw response;
        }).then(load).catch((err) => {
            show_toast(`An Error Occurred: ${err.status} ${err.statusText}`);
        });
    }
}