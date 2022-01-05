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
        return hours + ':' + (mins < 10 ? '0' + mins : mins) + ':' + (secs < 10 ? '0' + secs : secs);
    } else {
        let mins = Math.floor(time / 60);
        return mins + ':' + (secs < 10 ? '0' + secs : secs);
    }
}

function page(url, push = true) {
    if (push) window.history.pushState({"page": url}, "Loading - SimpleMusicLibrary", url);
    document.title = "Loading - SimpleMusicLibrary";
    let xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = 'document';
    xhr.onload = () => {
        if (xhr.status !== 200) show_toast("An Error Occurred: " + xhr.status + ' ' + xhr.statusText)
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

window.history.replaceState({"page": window.location.pathname}, document.title)
setupPage()
