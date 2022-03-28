let page_cache = {};

function open_big_player(push = true) {
    let container = elem_id("container");

    if (push) {
        page_cache['url'] = window.location.pathname;
        page_cache['title'] = document.title;
        page_cache['container'] = container.cloneNode(true);
        page_cache['navbar'] = elem_id("navbar").cloneNode(true);
        window.history.pushState({
            "page": window.location.pathname,
            "cache": true
        }, "Loading - SimpleMusicLibrary", window.location.pathname + "#queue");
    }

    for (let e of document.querySelectorAll("#navbarLinks .active")) {
        e.classList.remove("active");
    }

    document.title = "Your Queue - SimpleMusicLibrary";

    let elements = {};
    let new_children = [];
    let song = songs[queue.current || queue.next];

    if (song) {
        elements.h2 = document.createElement("h2");
        elements.h2.innerText = song.title;

        elements.h3a = document.createElement("a");
        elements.h3a.innerText = song.artist;
        elements.h3a.title = "Go to Artist";
        elements.h3a.classList.add("text-decoration-none");
        elements.h3a.setAttribute("role", "button");
        elements.h3a.addEventListener('click', () => page('/artists/' + song.id));
        elements.h3 = document.createElement("h3");
        elements.h3.appendChild(elements.h3a)

        elements.div1 = document.createElement("div");
        elements.div1.classList.add("d-flex", "flex-column", "justify-content-center");
        elements.div1.append(elements.h2, elements.h3)

        elements.img = document.createElement("img");
        elements.img.classList.add("col-4", "col-md-3", "col-lg-2", "px-0", "me-1", "bg-img");
        elements.img.src = `/image/${song.image}`;
        elements.img.title = "Go to Album";
        elements.img.setAttribute("role", "button");
        elements.img.addEventListener('click', () => page('/albums/' + song.id));

        elements.div0 = document.createElement("div");
        elements.div0.classList.add("d-flex", "flex-row");
        elements.div0.append(elements.img, elements.div1)
        elements.div0.addEventListener('contextmenu', (e) => menus.open(e, 'playing', queue.current || queue.next));

        elements.h5a = document.createElement("h5");
        elements.h5a.innerText = "Currently Playing:";

        elements.hr = document.createElement("hr");
        new_children = [elements.h5a, elements.div0, elements.hr];
    }

    elements.h5b = document.createElement("h5");
    elements.h5b.innerText = "Up next:";

    let new_items = [];

    for (let [index, song_id] of queue.array.entries()) {
        let song = songs[song_id];
        let tr = document.createElement("tr");
        for (let metaKey of ["track", "title", "album", "artist"]) {
            let td = document.createElement("td");
            td.innerText = song[metaKey];
            tr.appendChild(td);
        }
        { // year
            let td = document.createElement("td");
            td.innerText = song['year'];
            td.classList.add("d-none", "d-sm-table-cell")
            tr.appendChild(td);
        }
        { // duration
            let td = document.createElement("td");
            td.innerText = format_time(song['duration']);
            td.classList.add("d-none", "d-sm-table-cell")
            tr.appendChild(td);
        }

        tr.setAttribute("draggable", "true");
        tr.addEventListener('click', () => player.play(song_id));
        tr.addEventListener('contextmenu', (e) => menus.open(e, "queue", index));
        tr.addEventListener('dragstart', (e) => drag.start(e));
        tr.addEventListener('dragover', (e) => drag.over(e));
        tr.addEventListener('dragend', (e) => drag.update_queue(e));
        tr.setAttribute('role', 'button');
        new_items.push(tr);
    }

    elements.thead_tr = document.createElement("tr");
    for (let i of ["#", "Title", "Album", "Artist"]) {
        let th = document.createElement("th");
        th.setAttribute("scope", "col");
        th.innerText = i;
        elements.thead_tr.appendChild(th);
    }
    for (let i of ["Date", "Duration"]) {
        let th = document.createElement("th");
        th.setAttribute("scope", "col");
        th.innerText = i;
        th.classList.add("d-none", "d-sm-table-cell");
        elements.thead_tr.appendChild(th);
    }

    elements.thead = document.createElement("thead");
    elements.thead.appendChild(elements.thead_tr);

    elements.tbody = document.createElement("tbody");
    elements.tbody.append(...new_items);

    elements.table = document.createElement("table");
    elements.table.classList.add("table");
    elements.table.append(elements.thead, elements.tbody);
    updateTables(elements.table);

    container.replaceChildren(...new_children, elements.h5b, elements.table);
    queue_button.classList.add("text-info");
}

function update_big_player() {
    if (window.location.hash === "#queue") open_big_player(false);
}
