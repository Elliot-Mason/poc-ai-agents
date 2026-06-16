import requests
import sys

API_URL = "http://localhost:8000/chat"


def main():
    messages = []
    print("💳 CreditCardBot — type your message (Ctrl+C to quit)\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            resp = requests.post(API_URL, json={"messages": messages}, timeout=120)
            resp.raise_for_status()
            reply = resp.json()["reply"]
        except requests.ConnectionError:
            print("Bot: ⚠️  Can't reach the backend — is it running on :8000?\n")
            messages.pop()
            continue
        except Exception as e:
            print(f"Bot: ⚠️  Error: {e}\n")
            messages.pop()
            continue

        messages.append({"role": "assistant", "content": reply})
        print(f"Bot: {reply}\n")


if __name__ == "__main__":
    main()
