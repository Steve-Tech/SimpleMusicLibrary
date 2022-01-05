"use strict";
function live_search() {
    const inputBox = document.getElementById('search');
    const input = inputBox.value.toLowerCase();  // Make input lowercase to ignore case when searching
    const cards = document.getElementById("cards")?.getElementsByClassName('card');
    // const counter = document.getElementById("searchCount");

    if (cards != null) {

        let searchNum = 0;

        for (let i = 0; i < cards.length; i++) {  // For each card find input in 2 attributes and display none if no match
            if ((cards[i].getAttribute("data-name")?.toLowerCase().indexOf(input) > -1) ||
                (cards[i].getAttribute("data-alt")?.toLowerCase().indexOf(input) > -1)) {
                cards[i].classList.remove("d-none");  // Shows card if hidden previously
                searchNum += 1;  // Counts search results
            } else {
                cards[i].classList.add("d-none");
            }
        }
        if (searchNum === 0) {  // Adds the bootstrap form invalid class to the search box when there are no results
            inputBox.classList.add("is-invalid");
        } else {
            inputBox.classList.remove("is-invalid");
        }

        // counter.innerText = searchNum + " Shown";  // Update search count
    }

}


document.getElementById("search_form").addEventListener("submit", (e) => {
    page("/search?q=" + encodeURIComponent(e.target[0].value));
    e.preventDefault();
})
