import requests

def ask_ai(message, user_profile):

    prompt = f"""
You are a helpful scholarship assistant.

User profile:
Education: {user_profile['education']}
Category: {user_profile['category']}
Income: {user_profile['income']}
State: {user_profile['state']}

User question:
{message}

Suggest suitable scholarships and guidance.
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3",
                "prompt": prompt,
                "stream": False
            }
        )

        return response.json()["response"]

    except Exception as e:
        print("AI ERROR:", e)
        return "Local AI not running."