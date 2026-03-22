document.getElementById("scholarshipForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const data = {
        education: document.getElementById("education").value,
        income: document.getElementById("income").value,
        category: document.getElementById("category").value,
        state: document.getElementById("state").value
    };

    fetch("http://127.0.0.1:5000/match", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        localStorage.setItem("scholarshipResults", JSON.stringify(result));
       window.location.href = "dashboard.html";
    })
    .catch(error => {
        alert("Backend not running!");
        console.error(error);
    });
});


async function loginUser(email, password) {

  const response = await fetch("http://127.0.0.1:5000/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      email: email,
      password: password
    })
  });

  const data = await response.json();

  if (response.ok) {
    alert("Login Successful ✅");
    localStorage.setItem("user_name", email);
    window.location.href = "dashboard.html";
  } else {
    alert(data.error);
  }
}

function handleLogin() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  loginUser(email, password);
}