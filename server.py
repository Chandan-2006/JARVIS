from flask import Flask, send_from_directory, request, jsonify
import json
import os
import re

app = Flask(__name__, static_folder="web")

MEMORY_FILE = "memory.json"


# ==========================================
# MEMORY
# ==========================================

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}

    return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=4)


memory = load_memory()


# ==========================================
# TEXT NORMALIZATION
# ==========================================

def normalize_text(text):
    if not isinstance(text, str):
        return ""

    text = text.lower().strip()

    # Common speech-recognition variations
    replacements = {
        "what's": "what is",
        "whats": "what is",
        "who's": "who is",
        "who's": "who is",
        "i'm": "i am",
        "my name's": "my name is",
        "can you please": "please",
        "could you please": "please",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)

    # Remove repeated spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def contains_any(text, phrases):
    return any(phrase in text for phrase in phrases)


def has_words(text, words):
    return all(word in text for word in words)


# ==========================================
# WEBPAGE
# ==========================================

@app.route("/")
def home():
    return send_from_directory("web", "index.html")


@app.route("/<path:filename>")
def files(filename):
    return send_from_directory("web", filename)


# ==========================================
# JARVIS COMMAND
# ==========================================

@app.route("/command", methods=["POST"])
def command():

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "response": "I did not receive a command."
        })

    original_text = str(data.get("text", "")).strip()

    text = normalize_text(original_text)

    print("WEB:", original_text)
    print("NORMALIZED:", text)


    # ======================================
    # EXIT
    # ======================================

    if (
        text == "exit"
        or
        contains_any(text, [
            "shut down jarvis",
            "shutdown jarvis",
            "stop listening",
            "go to sleep"
        ])
    ):
        response = "Goodbye."


    # ======================================
    # SAVE NAME
    # ======================================

    elif (
        "my name is " in text
        or
        text.startswith("i am ")
    ):

        if "my name is " in text:
            name = text.split("my name is ", 1)[1].strip()
        else:
            name = text.split("i am ", 1)[1].strip()

        name = name.strip(" .,!?")

        if name:
            memory["name"] = name
            save_memory(memory)

            response = (
                f"Nice to meet you, {name}. "
                "I will remember your name."
            )
        else:
            response = "I didn't catch your name."


    # ======================================
    # REMEMBERED NAME
    # ======================================

    elif contains_any(text, [
        "do you know my name",
        "do you remember my name",
        "what is my name",
        "tell me my name",
        "who am i",
        "do you remember who i am"
    ]):

        if "name" in memory:
            response = (
                f"Yes. Your name is {memory['name']}."
            )
        else:
            response = "I don't know your name yet."


    # ======================================
    # GREETINGS
    # ======================================

    elif (
        text in [
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening"
        ]
        or
        contains_any(text, [
            "hello jarvis",
            "hi jarvis",
            "hey jarvis"
        ])
    ):

        if "good morning" in text:
            response = "Good morning. How can I help you?"
        elif "good afternoon" in text:
            response = "Good afternoon. How can I help you?"
        elif "good evening" in text:
            response = "Good evening. How can I help you?"
        else:
            response = "Hello! How can I help you?"


    # ======================================
    # JARVIS IDENTITY
    # ======================================

    elif contains_any(text, [
        "what is your name",
        "who are you",
        "tell me your name",
        "what should i call you",
        "what are you called"
    ]):

        response = "I am JARVIS."


    # ======================================
    # HELP / CAPABILITIES
    # ======================================

    elif contains_any(text, [
        "what can you do",
        "how can you help me",
        "what can you help me with",
        "tell me what you can do",
        "what are your capabilities"
    ]):

        response = (
            "I can listen to you, remember information "
            "you tell me, answer questions, and control "
            "supported home devices."
        )


    # ======================================
    # HOW ARE YOU
    # ======================================

    elif contains_any(text, [
        "how are you",
        "how are you doing",
        "are you okay",
        "are you working"
    ]):

        response = (
            "I am functioning normally and ready to help."
        )


    # ======================================
    # FAN ON
    # ======================================

    elif (
        "fan" in text
        and
        contains_any(text, [
            "turn on",
            "switch on",
            "start",
            "activate",
            "put on",
            "fan on",
            "make the fan run"
        ])
    ):

        response = (
            "Sure. I understand that you want the fan turned on."
        )


    # ======================================
    # FAN OFF
    # ======================================

    elif (
        "fan" in text
        and
        contains_any(text, [
            "turn off",
            "switch off",
            "stop",
            "deactivate",
            "put off",
            "fan off"
        ])
    ):

        response = (
            "Sure. I understand that you want the fan turned off."
        )


    # ======================================
    # HOT / WARM -> FAN
    # ======================================

    elif (
        "fan" in text
        and
        contains_any(text, [
            "hot",
            "warm",
            "heat"
        ])
    ):

        response = (
            "It sounds like you want the fan on."
        )


    # ======================================
    # LIGHT ON
    # ======================================

    elif (
        "light" in text
        and
        contains_any(text, [
            "turn on",
            "switch on",
            "start",
            "activate",
            "put on",
            "light on"
        ])
    ):

        response = (
            "Sure. I understand that you want the light turned on."
        )


    # ======================================
    # LIGHT OFF
    # ======================================

    elif (
        "light" in text
        and
        contains_any(text, [
            "turn off",
            "switch off",
            "stop",
            "deactivate",
            "put off",
            "light off"
        ])
    ):

        response = (
            "Sure. I understand that you want the light turned off."
        )


    # ======================================
    # THANK YOU
    # ======================================

    elif contains_any(text, [
        "thank you",
        "thanks",
        "thank you jarvis",
        "thanks jarvis"
    ]):

        response = "You're welcome."


    # ======================================
    # UNKNOWN
    # ======================================

    else:

        response = (
            "I heard you, but I don't know how to handle "
            "that request yet."
        )


    print("JARVIS:", response)

    return jsonify({
        "response": response
    })


# ==========================================
# START SERVER
# ==========================================

if __name__ == "__main__":

    print("=================================")
    print("       JARVIS WEB SERVER")
    print("=================================")
    print("Open your browser and visit:")
    print("http://127.0.0.1:5000")
    print("")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )