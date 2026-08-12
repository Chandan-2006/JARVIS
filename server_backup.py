from flask import Flask, send_from_directory, request, jsonify
import json
import os
import re

app = Flask(__name__, static_folder="web")

MEMORY_FILE = "memory.json"


# =========================
# MEMORY
# =========================

def load_memory():

    if os.path.exists(MEMORY_FILE):

        try:

            with open(
                MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                return json.load(file)

        except Exception:

            return {}

    return {}


def save_memory(memory):

    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            memory,
            file,
            indent=4
        )


memory = load_memory()


# =========================
# TEXT CLEANING
# =========================

def clean_text(text):

    text = text.lower().strip()

    text = re.sub(
        r"[^\w\s]",
        "",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# =========================
# WEBPAGE
# =========================

@app.route("/")
def home():

    return send_from_directory(
        "web",
        "index.html"
    )


@app.route("/<path:filename>")
def files(filename):

    return send_from_directory(
        "web",
        filename
    )


# =========================
# JARVIS COMMAND
# =========================

@app.route(
    "/command",
    methods=["POST"]
)
def command():

    data = request.get_json()

    if not data:

        return jsonify({
            "response":
                "I did not receive a command."
        })


    original_text = data.get(
        "text",
        ""
    )


    text = clean_text(
        original_text
    )


    print("WEB:", original_text)


    # =========================
    # EXIT
    # =========================

    if (
        text == "exit"
        or
        "shut down jarvis" in text
        or
        "shutdown jarvis" in text
    ):

        response = "Goodbye."


    # =========================
    # NAME MEMORY
    # =========================

    elif "my name is" in text:

        name = text.split(
            "my name is",
            1
        )[1].strip()


        if name:

            memory["name"] = name

            save_memory(memory)


            response = (
                f"Nice to meet you, {name}. "
                "I will remember your name."
            )

        else:

            response = (
                "I didn't catch your name."
            )


    # =========================
    # REMEMBER NAME
    # =========================

    elif (
        "do you know my name" in text
        or
        "do you remember my name" in text
        or
        "what is my name" in text
        or
        "whats my name" in text
    ):

        if "name" in memory:

            response = (
                f"Yes. Your name is "
                f"{memory['name']}."
            )

        else:

            response = (
                "I don't know your name yet."
            )


    # =========================
    # HELLO
    # =========================

    elif (
        "hello" in text
        or
        "hi jarvis" in text
        or
        text == "hi"
        or
        text == "hey jarvis"
    ):

        response = (
            "Hello! How can I help you?"
        )


    # =========================
    # JARVIS NAME
    # =========================

    elif (
        "what is your name" in text
        or
        "whats your name" in text
        or
        "who are you" in text
        or
        "tell me your name" in text
    ):

        response = "I am JARVIS."


    # =========================
    # FAN ON
    # =========================

    elif (
        "fan" in text
        and
        (
            "turn on" in text
            or
            "switch on" in text
            or
            "fan on" in text
            or
            "start fan" in text
            or
            "start the fan" in text
        )
    ):

        response = (
            "Fan command received. "
            "The fan should be turned on."
        )


    # =========================
    # FAN OFF
    # =========================

    elif (
        "fan" in text
        and
        (
            "turn off" in text
            or
            "switch off" in text
            or
            "fan off" in text
            or
            "stop fan" in text
            or
            "stop the fan" in text
        )
    ):

        response = (
            "Fan off command received. "
            "The fan should be turned off."
        )


    # =========================
    # LIGHT ON
    # =========================

    elif (
        "light" in text
        and
        (
            "turn on" in text
            or
            "switch on" in text
            or
            "light on" in text
            or
            "start light" in text
        )
    ):

        response = (
            "Light command received. "
            "The light should be turned on."
        )


    # =========================
    # LIGHT OFF
    # =========================

    elif (
        "light" in text
        and
        (
            "turn off" in text
            or
            "switch off" in text
            or
            "light off" in text
            or
            "stop light" in text
        )
    ):

        response = (
            "Light off command received. "
            "The light should be turned off."
        )


    # =========================
    # HELP
    # =========================

    elif (
        "how can you help me" in text
        or
        "what can you do" in text
        or
        "what can you help me with" in text
    ):

        response = (
            "I can remember information, "
            "answer basic questions, and "
            "control supported home devices."
        )


    # =========================
    # UNKNOWN
    # =========================

    else:

        response = (
            "I don't understand that "
            "command yet."
        )


    print(
        "JARVIS:",
        response
    )


    return jsonify({
        "response": response
    })


# =========================
# START SERVER
# =========================

if __name__ == "__main__":

    print(
        "================================="
    )

    print(
        "       JARVIS WEB SERVER"
    )

    print(
        "================================="
    )

    print(
        "Open your browser and visit:"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print("")


    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )