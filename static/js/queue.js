"use strict";
let queue_button = elem_id("queue");

class Queue {
    current = null;
    played = [];

    constructor(queue = []) {
        this.queue = queue;
    }

    get next() {
        return this.queue[0];
    }

    get previous() {
        return this.played[0];
    }

    get array() {
        return this.queue;
    }

    get length() {
        return this.queue.length;
    }

    get full_queue() {
        return this.current ? [this.current, ...this.queue] : this.queue;
    }


    play(song = this.queue.shift()) {
        this.current = song;
        this.played.unshift(song);
        this.update();
        return this.current;
    }

    play_prev() {
        let song = this.played.shift();
        if (this.current && this.current !== song) {
            this.queue.unshift(this.current);
        }
        this.current = song;
        this.update();
        return this.current;
    }

    add_all(song_id) {
        let before = this.queue.length;
        let adding = false;
        for (let element of document.querySelectorAll("table.table > tbody > tr[data-id]")) {
            let e_id = element.getAttribute("data-id");
            if (e_id == song_id || adding) {
                this.queue.push(parseInt(e_id));
                adding = true;
            }
        }
        this.update();
        let amount = this.queue.length - before;
        if (amount > 0)
            show_toast(`Added ${amount} items to queue.`);
        if (this.current == null) player.start(song_id);
    }

    add(song_id) {
        let before = this.queue.length;
        let isArray = Array.isArray(song_id);
        if (isArray)
            this.queue.push(...song_id);
        else
            this.queue.push(song_id);
        this.update();
        let amount = this.queue.length - before;
        if (amount > 0)
            show_toast(`Added ${amount} ${amount !== 1 ? 'items' : 'item'} to queue.`);
        if (this.current == null) {
            if (isArray)
                player.start(song_id[0]);
            else
                player.start(song_id);
        }
    }

    // Knuth Shuffle
    shuffle() {
        let currentIndex = this.queue.length, randomIndex;
        while (currentIndex !== 0) {
            randomIndex = Math.floor(Math.random() * currentIndex);
            currentIndex--;
            [this.queue[currentIndex], this.queue[randomIndex]] = [
                this.queue[randomIndex], this.queue[currentIndex]];
        }
        this.update();
    }

    clear() {
        this.queue = [];
        this.update();
    }

    move(item, inc) {
        this.queue.splice(item + inc, 0, this.queue.splice(item, 1)[0]);
        this.update();
    }

    push(item) {
        let val = this.queue.push(item);
        this.update();
        return val;
    }

    unshift(item) {
        let val = this.queue.unshift(item);
        this.update();
        return val;
    }

    shift() {
        let val = this.queue.shift();
        this.update();
        return val;
    }

    pop() {
        let val = this.queue.pop();
        this.update();
        return val;
    }

    splice(start, count) {
        let val = this.queue.splice(start, count);
        this.update();
        return val;
    }

    // Update queue on server and displayed in queue screen
    update() {
        update_big_player()
        let xhr = new XMLHttpRequest();
        xhr.open("POST", '/queue', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = () => {
            if (xhr.status !== 200) show_toast(`An Error Occurred: ${xhr.status} ${xhr.statusText}`)
        }
        xhr.send(JSON.stringify(this.full_queue));
    }
}