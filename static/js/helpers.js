"use strict";

// Shorthand document.getElementById()
const elem_id = (elem) => document.getElementById(elem);
// const elems_class = (elem) => document.getElementsByClassName(elem);
// const elem_query = (elem) => document.querySelector(elem);
// const elems_query = (elem) => document.querySelectorAll(elem);

const toast = elem_id("toast");
let bs_toast = bootstrap.Toast.getOrCreateInstance(toast);

function show_toast(message) {
    toast.getElementsByClassName('toast-body')[0].innerText = message;
    bs_toast.show();
}

// Formats time from seconds into h:mm:ss
function format_time(time) {
    let secs = Math.floor(time % 60);
    if (time > 3600) {
        let mins = Math.floor((time % 3600) / 60);
        let hours = Math.floor(time / 3600);
        return `${hours}:${mins < 10 ? '0' + mins : mins}`;
    } else {
        let mins = Math.floor(time / 60);
        return `${mins}:${secs < 10 ? '0' + secs : secs}`;
    }
}

// Go to a page without reloading and stopping the playing song
function page(url, push = true) {
    if (push) window.history.pushState({"page": url}, "Loading - SimpleMusicLibrary", url);
    queue_button.classList.remove("text-info")
    if (page_cache['url'] === url) {
        console.log(page_cache)
        document.title = page_cache['title'];
        elem_id("container").replaceWith(page_cache['container']);
        elem_id("navbar").replaceWith(page_cache['navbar']);
        page_cache = {}
        setupPage();
        return
    }
    document.title = "Loading - SimpleMusicLibrary";
    elem_id("loading").classList.remove("opacity-0");
    let xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = 'document';
    xhr.onload = () => {
        if (xhr.status !== 200) show_toast(`An Error Occurred: ${xhr.status} ${xhr.statusText}`);
        elem_id("loading").classList.add("opacity-0");
        const new_doc = xhr.responseXML;
        document.title = new_doc.title;
        document.getElementById("navbar").innerHTML = new_doc.getElementById("navbar").innerHTML;
        document.getElementById("container").innerHTML = new_doc.getElementById("container").innerHTML;
        let e_songs = new_doc.getElementById('songs');
        if (e_songs) Object.assign(songs, JSON.parse(e_songs.innerText));
        setupPage();
    }
    xhr.send();
}

function clickPage(e, url, push = true) {
    if (e.ctrlKey) {
        window.open(url, "_blank")
    } else {
        page(url, push)
    }
}

// Setup function for new page load
function setupPage() {
    document.querySelectorAll("[data-page]").forEach((element) => {
        const data_page = (e) => clickPage(e, element.getAttribute("data-page"));
        element.removeEventListener("click", data_page);
        element.addEventListener("click", data_page);
    });
    updateTables(document.body);
    load_search();
}

// Update event listeners for tables
function updateTables(base_element = document.body) {
    base_element.querySelectorAll("table.table > tbody > tr").forEach((element) => {
        let text = element.children[0].innerText;
        element.addEventListener("mouseenter", () => {
            element.children[0].innerText = '';
            element.children[0].classList.add("bi", "bi-play-circle-fill");
        });
        element.addEventListener("mouseleave", () => {
            element.children[0].innerText = text;
            element.children[0].classList.remove("bi", "bi-play-circle-fill");
        });
    });
}

// Get all songs on a page
function get_all() {
    let ids = [];
    document.querySelectorAll("table.table > tbody > tr[data-id]").forEach((element) => {
        ids.push(element.getAttribute("data-id"));
    });
    return ids;
}

// Handles dragging of songs in a table
class Drag {
    row;
    original_index;
    ready = true;

    start(e) {
        this.row = e.target;
        this.original_index = Array.from(e.target.parentNode.children).indexOf(e.target);
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
            setTimeout(() => {
                this.ready = true
            }, 50);
            this.ready = false;
        }
    }

    update_queue(e) {
        queue.move(this.original_index, Array.from(e.target.parentNode.children).indexOf(this.row) - this.original_index);
    }

    update_playlist(e, playlist_id) {
        playlists.move(playlist_id, this.original_index + 1, Array.from(e.target.parentNode.children).indexOf(this.row) - this.original_index);
    }
}

// Handles context menus
class Menus {
    menus = {};
    selected;
    index;
    elem;

    constructor() {
        document.body.addEventListener('click', (e) => {
            if (!document.querySelector(".dropend > .dropdown-item.dropdown-toggle")?.contains(e.target)) {
                this.close_all();
            }
        });
    }

    // Build a menu to be cached for showing
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

    // Open a built menu
    open(e, name, id) {
        // Let browser menu show if any modifier keys are pressed
        if (!(e.altKey || e.ctrlKey || e.metaKey || e.shiftKey))
            e.preventDefault();
        this.selected = id;
        this.elem = e.target;
        let menu = this.menus[name];
        menu.classList.add("show", "invisible"); // Show but invisible to get the height & width of the menu
        // Move menu if in lower quarter of the screen or right most eighth
        menu.style.top = (e.clientY > window.innerHeight / 1.5 ? e.pageY - menu.offsetHeight : e.pageY) + "px";
        menu.style.left = (e.clientX > window.innerWidth / 1.25 ? e.pageX - menu.offsetWidth : e.pageX) + "px";
        menu.classList.remove("invisible"); // Finally show
    }

    // Close a certain menu
    close(name) {
        this.menus[name].classList.remove("show");
    }

    // Close All Menus
    close_all() {
        Object.values(this.menus).forEach(e => e.classList.remove("show"));
    }
}

let menus = new Menus();
menus.build("song",
    {
        "Play": () => player.start(menus.selected),
        "Play Next": () => queue.unshift(menus.selected),
        "Add to Queue": () => queue.add(menus.selected),
        "Add Following to Queue": () => queue.add_all(menus.selected),
        "elem: Add to Playlist": elem_id("playlist_dropend"),
        "Go to Album": (e) => clickPage(e, '/albums/' + menus.selected),
        "Go to Artist": (e) => clickPage(e, '/artists/' + menus.selected)
    }
)
menus.build("playlist",
    {
        "Play": () => player.start(menus.selected),
        "Play Next": () => queue.unshift(menus.selected),
        "Add to Queue": () => queue.add(menus.selected),
        "Add Following to Queue": () => queue.add_all(menus.selected),
        "Remove from Playlist": () => {
            playlists.remove(elem_id("playlist").getAttribute("data-id"), Array.from(menus.elem.closest("tbody").children).indexOf(menus.elem.closest("tr")) + 1);
            menus.elem.closest("tr").remove();
        },
        "Go to Album": (e) => clickPage(e, '/albums/' + menus.selected),
        "Go to Artist": (e) => clickPage(e, '/artists/' + menus.selected)
    }
)
menus.build("queue",
    {
        "Play Now": () => player.start(queue.array[menus.selected]),
        "Play Next": () => queue.unshift(queue.array[menus.selected]),
        "Remove from Queue": () => queue.splice(menus.selected, 1),
        "Go to Album": (e) => clickPage(e, '/albums/' + queue.array[menus.selected]),
        "Go to Artist": (e) => clickPage(e, '/artists/' + queue.array[menus.selected])
    }
)
menus.build("album",
    {
        "Go to Album": (e) => clickPage(e, '/albums/' + menus.selected),
        "Go to Artist": (e) => clickPage(e, '/artists/' + menus.selected)
    }
)
menus.build("playing",
    {
        "Play Next": () => queue.unshift(menus.selected),
        "Re-add to Queue": () => queue.add(menus.selected),
        "Go to Album": (e) => clickPage(e, '/albums/' + menus.selected),
        "Go to Artist": (e) => clickPage(e, '/artists/' + menus.selected)
    }
)

elem_id("theme").addEventListener("change", (e) =>
    elem_id("bootstrap").setAttribute("href", "static/css/" +
            (e.target.value === "Default" ? "bootstrap.min.css" : `themes/${e.target.value}.css`)))

window.history.replaceState({"page": window.location.pathname}, document.title);
setupPage();
