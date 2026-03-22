import requests

response = requests.post(
    "http://127.0.0.1:5000/send_welcome_email",
    json={"email": "asishmishra005@gmail.com", "name": "Asish"}
)
print(response.json())
