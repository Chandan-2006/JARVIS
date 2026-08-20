from flask import Flask, send_from_directory, request, jsonify
import json
import os
import re
import urllib.request
import urllib.error

app = Flask(__name__, static_folder="web")

MEMORY_FILE = "memory.json"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:4b"


# ==========================================
# MEMORY
# ==========================================

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


# ==========================================
# TEXT NORMALIZATION
# ==========================================

def normalize_text(text):

    if not isinstance(text, str):
        return ""

    text = text.lower().strip()

    replacements = {
        "what's": "what is",
        "whats": "what is",
        "who's": "who is",
        "i'm": "i am",
        "my name's": "my name is",
        "how's": "how is"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"[^\w\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ==========================================
# CLEAN QWEN RESPONSE
# ==========================================

def clean_ai_response(text):

    if not text:
        return "I don't have a response yet."

    text = str(text).strip()


    # --------------------------------------
    # CASE 1:
    # <think>reasoning</think>answer
    # --------------------------------------

    if "</think>" in text.lower():

        parts = re.split(
            r"</think>",
            text,
            maxsplit=1,
            flags=re.IGNORECASE
        )

        if len(parts) == 2:
            text = parts[1].strip()


    # --------------------------------------
    # CASE 2:
    # <think>reasoning</think>
    # --------------------------------------

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )


    # --------------------------------------
    # Other Qwen thinking markers
    # --------------------------------------

    text = re.sub(
        r"<\|think\|>.*?<\|endofthink\|>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )


    # --------------------------------------
    # Remove accidental marker text
    # --------------------------------------

    text = text.replace(
        "<|assistant|>",
        ""
    )

    text = text.replace(
        "<|end|>",
        ""
    )

    text = text.strip()


    # --------------------------------------
    # If reasoning somehow remains without
    # tags, try to locate the final answer.
    # --------------------------------------

    answer_markers = [
        "Final answer:",
        "Final response:",
        "Answer:",
        "Response:"
    ]

    for marker in answer_markers:

        match = re.search(
            re.escape(marker),
            text,
            flags=re.IGNORECASE
        )

        if match:

            text = text[
                match.end():
            ].strip()

            break


    # --------------------------------------
    # Remove common reasoning lines
    # --------------------------------------

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]


    filtered_lines = []


    reasoning_starts = (
        "okay, the user",
        "the user said",
        "the user wants",
        "i need to",
        "i should",
        "i need",
        "let me",
        "first, i",
        "hmm,",
        "wait,",
        "thinking",
        "brainstorming",
        "double-checking",
        "mental note"
    )


    for line in lines:

        lower = line.lower()

        if lower.startswith(
            reasoning_starts
        ):
            continue

        filtered_lines.append(line)


    if filtered_lines:

        text = " ".join(
            filtered_lines
        ).strip()


    # --------------------------------------
    # Remove obvious "reasoning" fragments
    # --------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()


    if not text:

        return "I'm ready to help."


    return text


# ==========================================
# ASK QWEN
# ==========================================

def ask_qwen(user_text):

    saved_name = memory.get(
        "name",
        "the user"
    )


    system_prompt = f"""
You are JARVIS, a friendly desktop AI assistant.

The user's name is {saved_name}.

Understand natural human language, including:
- imperfect grammar
- different sentence structures
- casual speech
- incomplete grammar
- polite requests
- spelling mistakes

Speak naturally.

IMPORTANT OUTPUT RULES:
- Give ONLY the final answer.
- Do NOT show reasoning.
- Do NOT explain how you generated the answer.
- Do NOT use <think> tags.
- Do NOT say "the user said..."
- Do NOT say "I need to..."
- Do NOT brainstorm.
- Do NOT describe your internal process.
- Keep normal spoken answers short.
- Normally answer in one or two sentences.

If the request is unclear, ask one short clarification.
"""


    payload = {
        "model": OLLAMA_MODEL,

        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_text
            }
        ],

        "stream": False,

        "think": False,

        "keep_alive": "10m",

        "options": {
            "temperature": 0.2,
            "num_predict": 80
        }
    }


    body = json.dumps(
        payload
    ).encode("utf-8")


    req = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={
            "Content-Type":
                "application/json"
        },
        method="POST"
    )


    try:

        with urllib.request.urlopen(
            req,
            timeout=120
        ) as response:

            result = json.loads(
                response
                .read()
                .decode("utf-8")
            )


        # Newer Ollama responses may separate
        # thinking from the final answer.
        message = result.get(
            "message",
            {}
        )


        answer = message.get(
            "content",
            ""
        )


        # If Ollama provides a separate
        # thinking field, never use it.
        if message.get("thinking"):
            print(
                "QWEN THINKING RECEIVED "
                "(hidden)"
            )


        answer = clean_ai_response(
            answer
        )


        print(
            "QWEN FINAL:",
            answer
        )


        return answer


    except urllib.error.URLError as error:

        print(
            "OLLAMA CONNECTION ERROR:",
            error
        )

        return (
            "My local AI brain is not available "
            "right now."
        )


    except TimeoutError:

        print(
            "OLLAMA ERROR: timed out"
        )

        return (
            "My AI response took too long. "
            "Please try again."
        )


    except Exception as error:

        print(
            "OLLAMA ERROR:",
            error
        )

        return (
            "I had trouble processing that."
        )


# ==========================================
# WEBPAGE
# ==========================================

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


# ==========================================
# COMMAND
# ==========================================

@app.route(
    "/command",
    methods=["POST"]
)
def command():

    data = request.get_json(
        silent=True
    )


    if not data:

        return jsonify({
            "response":
                "I did not receive a command."
        })


    original_text = str(
        data.get(
            "text",
            ""
        )
    ).strip()


    text = normalize_text(
        original_text
    )


    print(
        "WEB:",
        original_text
    )


    print(
        "NORMALIZED:",
        text
    )


    # ======================================
    # EXIT
    # ======================================

    if (
        text == "exit"
        or
        "shut down jarvis" in text
        or
        "shutdown jarvis" in text
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

            name = text.split(
                "my name is ",
                1
            )[1].strip()

        else:

            name = text.split(
                "i am ",
                1
            )[1].strip()


        name = name.strip(
            " .,!?;"
        )


        if name:

            memory["name"] = name

            save_memory(
                memory
            )


            response = (
                f"Nice to meet you, {name}. "
                "I will remember your name."
            )

        else:

            response = (
                "I didn't catch your name."
            )


    # ======================================
    # REMEMBER NAME
    # ======================================

    elif (
        "do you know my name" in text
        or
        "do you remember my name" in text
        or
        "what is my name" in text
        or
        "tell me my name" in text
        or
        "who am i" in text
        or
        "do you remember who i am" in text
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
        "hello jarvis" in text
        or
        "hi jarvis" in text
        or
        "hey jarvis" in text
    ):

        response = (
            "Hello! How can I help you?"
        )


    # ======================================
    # JARVIS NAME
    # ======================================

    elif (
        "what is your name" in text
        or
        "who are you" in text
        or
        "tell me your name" in text
        or
        "what are you called" in text
    ):

        response = "I am JARVIS."


    # ======================================
    # FAN ON
    # ======================================

    elif (
        "fan" in text
        and
        (
            "turn on" in text
            or
            "switch on" in text
            or
            "start fan" in text
            or
            "start the fan" in text
            or
            "fan on" in text
            or
            "get the fan going" in text
            or
            "put the fan on" in text
        )
    ):

        response = (
            "I understand. "
            "You want the fan turned on."
        )


    # ======================================
    # FAN OFF
    # ======================================

    elif (
        "fan" in text
        and
        (
            "turn off" in text
            or
            "switch off" in text
            or
            "stop fan" in text
            or
            "stop the fan" in text
            or
            "fan off" in text
            or
            "put the fan off" in text
        )
    ):

        response = (
            "I understand. "
            "You want the fan turned off."
        )


    # ======================================
    # LIGHT ON
    # ======================================

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
            "put the light on" in text
        )
    ):

        response = (
            "I understand. "
            "You want the light turned on."
        )


    # ======================================
    # LIGHT OFF
    # ======================================

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
            "put the light off" in text
        )
    ):

        response = (
            "I understand. "
            "You want the light turned off."
        )


    # ======================================
    # EVERYTHING ELSE -> QWEN
    # ======================================

    else:

        response = ask_qwen(
            original_text
        )


    print(
        "JARVIS:",
        response
    )


    return jsonify({
        "response": response
    })


# ==========================================
# START SERVER
# ==========================================

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