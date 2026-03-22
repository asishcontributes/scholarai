// ===============================
// LOAD SCHOLARSHIPS ON PAGE LOAD
// ===============================

document.addEventListener("DOMContentLoaded", function () {
    loadScholarships();
});


// ===============================
// FETCH FROM BACKEND
// ===============================

function loadScholarships() {

    fetch("/get_scholarships")
        .then(response => response.json())
        .then(data => displayScholarships(data))
        .catch(error => console.error("Error:", error));
}


// ===============================
// DISPLAY ON PAGE
// ===============================

function displayScholarships(list) {

    let container = document.getElementById("scholarship-list");

    if (!container) {
        console.error("No container found");
        return;
    }

    container.innerHTML = "";

    if (list.length === 0) {
        container.innerHTML = "<p>No scholarships found.</p>";
        return;
    }

    list.forEach(s => {

        let card = `
            <div style="
                border:1px solid #ddd;
                padding:15px;
                margin:10px 0;
                border-radius:8px;
                background:white;
                box-shadow:0 2px 5px rgba(0,0,0,0.1);
            ">
                <h3>${s.scholarship_name}</h3>
                <p><b>Provider:</b> ${s.provider}</p>
                <p><b>Deadline:</b> ${s.deadline}</p>
                <p><b>Match:</b> ${s.eligibility_match_percent}%</p>
                <a href="${s.application_link}" target="_blank">
                    Apply Now
                </a>
            </div>
        `;

        container.innerHTML += card;
    });
}