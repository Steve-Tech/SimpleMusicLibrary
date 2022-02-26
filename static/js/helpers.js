"use strict";
const elem_id = (elem) => document.getElementById(elem)
// const elems_class = (elem) => document.getElementsByClassName(elem)
// const elem_query = (elem) => document.querySelector(elem)
// const elems_query = (elem) => document.querySelectorAll(elem)

const toast = elem_id("toast");
let bs_toast = bootstrap.Toast.getOrCreateInstance(toast);

function show_toast(message) {
    toast.getElementsByClassName('toast-body')[0].innerText = message;
    bs_toast.show()
}

function format_time(time) {
    let secs = Math.floor(time % 60);
    if (time > 3600) {
        let mins = Math.floor((time % 3600) / 60);
        let hours = Math.floor(time / 3600);
        return `${hours}:${mins < 10 ? '0' + mins : mins}`
    } else {
        let mins = Math.floor(time / 60);
        return `${mins}:${secs < 10 ? '0' + secs : secs}`
    }
}

function page(url, push = true) {
    if (push) window.history.pushState({"page": url}, "Loading - SimpleMusicLibrary", url);
    document.title = "Loading - SimpleMusicLibrary";
    elem_id("loading").classList.remove("opacity-0")
    let xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = 'document';
    xhr.onload = () => {
        if (xhr.status !== 200) show_toast(`An Error Occurred: ${xhr.status} ${xhr.statusText}`)
        elem_id("loading").classList.add("opacity-0")
        const new_doc = xhr.responseXML;
        document.title = new_doc.title;
        document.getElementById("navbar").innerHTML = new_doc.getElementById("navbar").innerHTML;
        document.getElementById("container").innerHTML = new_doc.getElementById("container").innerHTML;
        let e_songs = new_doc.getElementById('songs');
        if (e_songs) Object.assign(songs, JSON.parse(e_songs.innerText));
        setupPage();
    }
    xhr.send()
}

function setupPage() {
    document.querySelectorAll("[data-page]").forEach((element) => {
        const data_page = () => page(element.getAttribute("data-page"))
        element.removeEventListener("click", data_page);
        element.addEventListener("click", data_page);
    })
    updateTables(document.body)
    load_search()
}

function updateTables(base_element = document.body) {
    base_element.querySelectorAll("table.table > tbody > tr").forEach((element) => {
        let text = element.children[0].innerText;
        element.addEventListener("mouseenter", (e) => {
            element.children[0].innerText = '▶';
        })
        element.addEventListener("mouseleave", (e) => {
            element.children[0].innerText = text;
        })
    })
}

function get_all() {
    let ids = []
    document.querySelectorAll("table.table > tbody > tr[data-id]").forEach((element) => {
        ids.push(element.getAttribute("data-id"))
    })
    return ids
}

class Drag {
    row;
    original_index;
    ready = true;

    start(e) {
        this.row = e.target;
        this.original_index = Array.from(e.target.parentNode.children).indexOf(e.target)
    }

    over(e) {
        e.preventDefault();
        if (this.ready) {
            let children = Array.from(this.row.closest("tbody").children);
            if (children.indexOf(e.target.parentNode) > children.indexOf(this.row)) {
                e.target.closest("tr").after(this.row);
            } else {
                e.target.closest("tr").before(this.row);
            }
            setTimeout(() => {this.ready = true}, 50)
            this.ready = false;
        }
    }

    update_queue(e) {
        queue.move(this.original_index, Array.from(e.target.parentNode.children).indexOf(this.row) - this.original_index)
    }

    update_playlist(e, playlist_id) {
        playlists.move(playlist_id, this.original_index + 1, Array.from(e.target.parentNode.children).indexOf(this.row) - this.original_index)
    }
}

class Menus {
    menus = {};
    selected;
    index;
    elem;

    constructor() {
        document.body.addEventListener('click', (e) => {
            if (!document.querySelector(".dropend > .dropdown-item.dropdown-toggle")?.contains(e.target)) {
                this.close_all()
            }
        })
    }


    build(name, items) {
        let ul = document.createElement("ul");
        ul.id = `${name}_menu`;
        ul.classList.add("dropdown-menu", "context-menu");
        for (const item in items) {
            if (item.startsWith("html")) {
                let li = document.createElement("li");
                li.innerHTML = items[item];
                ul.appendChild(li);
            } else if (item.startsWith("elem")) {
                ul.appendChild(items[item]);
            } else {
                let a = document.createElement("a");
                a.innerText = item;
                a.classList.add("dropdown-item");
                a.setAttribute("role", "button");
                a.addEventListener("click", items[item]);
                ul.appendChild(document.createElement("li").appendChild(a));
            }
        }
        document.body.appendChild(ul);
        this.menus[name] = ul;
    }

    open(e, name, id) {
        if (!(e.altKey || e.ctrlKey || e.metaKey || e.shiftKey))
            e.preventDefault()
        this.selected = id;
        this.elem = e.target;
        menu = this.menus[name];
        menu.style.top = e.pageY + "px";
        menu.style.left = e.pageX + "px";
        menu.classList.add("show")
    }

    close(name) {
        this.menus[name].classList.remove("show");
    }

    close_all() {
        Object.values(this.menus).forEach(e => e.classList.remove("show"));
    }
}

let menus = new Menus()
menus.build("song",
    {
        "Play": () => player.start(menus.selected),
        "Play Next": () => queue.unshift(menus.selected),
        "Play All": () => queue.add_all(menus.selected),
        "Add to Queue": () => queue.add(menus.selected),
        "elem: Add to Playlist": elem_id("playlist_dropend"),
        "Go to Album": () => page('/albums/' + menus.selected),
        "Go to Artists": () => page('/artists/' + menus.selected)
    }
)
menus.build("playlist",
    {
        "Play": () => player.start(menus.selected),
        "Play Next": () => queue.unshift(menus.selected),
        "Play All": () => queue.add_all(menus.selected),
        "Add to Queue": () => queue.add(menus.selected),
        "Remove from Playlist": () => {
            playlists.remove(elem_id("playlist").getAttribute("data-id"), Array.from(menus.elem.closest("tbody").children).indexOf(menus.elem.closest("tr")) + 1);
            menus.elem.closest("tr").remove();
        },
        "Go to Album": () => page('/albums/' + menus.selected),
        "Go to Artists": () => page('/artists/' + menus.selected)
    }
)
menus.build("queue",
    {
        "Play Now": () => player.start(queue.array[menus.selected]),
        "Play Next": () => queue.unshift(queue.array[menus.selected]),
        "Remove from Queue": () => queue.splice(menus.selected, 1),
        "Go to Album": () => page('/albums/' + menus.selected),
        "Go to Artists": () => page('/artists/' + menus.selected)
    }
)

window.history.replaceState({"page": window.location.pathname}, document.title)
setupPage()
