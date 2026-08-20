from flask import Flask, request, jsonify, send_from_directory
import requests
import re
import time
import os


# ==========================================================
# JARVIS
# FAST LOCAL AI VERSION
# ==========================================================

app = Flask(
    __name__,
    static_folder="web",
    static_url_path=""
)


# ==========================================================
# SETTINGS
# ==========================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

MODEL = "Jadio/Qwen3_4b_instruct_q4km:latest"

OLLAMA_TIMEOUT = 45


# ==========================================================
# MEMORY
# ==========================================================

MEMORY = {
    "name": "Chandan"
}


# ==========================================================
# CONVERSATION
# ==========================================================

conversation_history = []


MAX_HISTORY = 8


# ==========================================================
# SYSTEM PROMPT
# ==========================================================

SYSTEM_PROMPT = """
You are JARVIS, a local personal AI assistant.

You are talking directly with Chandan.

Speak naturally like a normal conversation.

IMPORTANT:

- Give SHORT answers.
- Usually answer in 1 or 2 sentences.
- Do NOT explain your reasoning.
- Do NOT show your thinking.
- Do NOT mention "the user".
- Do NOT say "I need to figure out".
- Do NOT repeat the question.
- Do NOT write long essays unless Chandan asks for details.
- Understand imperfect English.
- Correctly understand conversational sentences.
- If Chandan says he learned something, respond naturally.
- If Chandan asks a question, answer it directly.
- Remember that Chandan's name is Chandan.
- Be friendly but concise.

Example:

Chandan: Yesterday I learned Python.

JARVIS: Nice! What did you learn?

Chandan: My name is Chandan.

JARVIS: Nice to meet you, Chandan.

Chandan: What can you do?

JARVIS: I can chat, remember things, answer questions, and control supported devices.

Never output hidden reasoning or analysis.
"""


# ==========================================================
# NORMALIZE TEXT
# ==========================================================

def normalize_text(text):

    if not text:
        return ""

    text = text.strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


# ==========================================================
# REMOVE QWEN THINKING
# ==========================================================

def clean_ai_response(text):

    if not text:
        return ""

    text = text.strip()


    # Remove <think>...</think>

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )


    # Remove ``` blocks

    text = re.sub(
        r"```.*?```",
        "",
        text,
        flags=re.DOTALL
    )


    # Remove common reasoning prefixes

    bad_starts = [

        "Okay, the user said",
        "The user said",
        "The user wants",
        "I need to",
        "First, I need to",
        "Let's think",
        "Thinking...",
        "I should respond",
        "I need to respond",
        "The user is asking",
        "Hmm, the user",
    ]


    for start in bad_starts:

        if text.lower().startswith(
            start.lower()
        ):

            # Try to find the actual final answer.

            lines = text.splitlines()

            useful = []

            for line in lines:

                line = line.strip()

                if not line:
                    continue

                if line.lower().startswith(
                    start.lower()
                ):
                    continue

                useful.append(line)


            if useful:

                text = " ".join(
                    useful
                )

                break


    # Remove obvious analysis markers

    text = re.sub(
        r"^\s*(analysis|reasoning|thoughts?)\s*:\s*",
        "",
        text,
        flags=re.IGNORECASE
    )


    # Remove excessive whitespace

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()


    # Remove surrounding quotes

    if (
        len(text) >= 2
        and text[0] == '"'
        and text[-1] == '"'
    ):

        text = text[1:-1].strip()


    return text


# ==========================================================
# FAST LOCAL COMMANDS
# ==========================================================

def local_response(text):

    lower = text.lower().strip()


    # ------------------------------------------
    # NAME
    # ------------------------------------------

    if re.search(
        r"\b(what is|whats|what's)\s+my\s+name\b",
        lower
    ):

        return (
            f"Your name is {MEMORY['name']}."
        )


    if re.search(
        r"\bmy name is\b",
        lower
    ):

        match = re.search(
            r"\bmy name is\s+(.+)",
            text,
            re.IGNORECASE
        )


        if match:

            name = match.group(1).strip()

            name = re.sub(
                r"[.!?]+$",
                "",
                name
            )


            if name:

                MEMORY["name"] = name.title()

                return (
                    f"Nice to meet you, {MEMORY['name']}."
                )


    # ------------------------------------------
    # JARVIS NAME
    # ------------------------------------------

    if re.search(
        r"\bwhat is your name\b",
        lower
    ):

        return "I am JARVIS."


    # ------------------------------------------
    # GREETING
    # ------------------------------------------

    if re.fullmatch(
        r"(hi|hello|hey)( jarvis)?[.!]?",
        lower
    ):

        return (
            f"Hello {MEMORY['name']}, how can I help?"
        )


    # ------------------------------------------
    # SIMPLE JARVIS
    # ------------------------------------------

    if lower in [
        "jarvis",
        "hey jarvis",
        "hi jarvis",
        "hello jarvis"
    ]:

        return (
            f"Yes, {MEMORY['name']}?"
        )


    return None


# ==========================================================
# OLLAMA
# ==========================================================

def ask_ollama(user_text):

    global conversation_history


    messages = [

        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }

    ]


    # Add recent conversation

    messages.extend(
        conversation_history[
            -MAX_HISTORY:
        ]
    )


    messages.append(
        {
            "role": "user",
            "content": user_text
        }
    )


    payload = {

        "model": MODEL,

        "messages": messages,

        "stream": False,

        "think": False,

        "options": {

            # Keep responses short.

            "num_predict": 60,

            # More deterministic.

            "temperature": 0.4,

            # Smaller context for speed.

            "num_ctx": 2048,

            # Keep CPU generation focused.

            "top_p": 0.8

        }

    }


    start_time = time.time()


    try:

        response = requests.post(

            OLLAMA_URL,

            json=payload,

            timeout=OLLAMA_TIMEOUT
        )


        elapsed = time.time() - start_time


        print(
            f"OLLAMA TIME: {elapsed:.2f}s"
        )


        response.raise_for_status()


        data = response.json()


        message = data.get(
            "message",
            {}
        )


        answer = message.get(
            "content",
            ""
        )


        answer = clean_ai_response(
            answer
        )


        if not answer:

            return (
                "I'm here. What would you like to know?"
            )


        # Save conversation

        conversation_history.append(
            {
                "role": "user",
                "content": user_text
            }
        )


        conversation_history.append(
            {
                "role": "assistant",
                "content": answer
            }
        )


        # Keep history small.

        if len(conversation_history) > 16:

            conversation_history = (
                conversation_history[-16:]
            )


        return answer


    except requests.exceptions.Timeout:

        print(
            "OLLAMA ERROR: timeout"
        )


        return (
            "I'm taking too long to think. Try asking that more simply."
        )


    except requests.exceptions.ConnectionError:

        print(
            "OLLAMA ERROR: connection failed"
        )


        return (
            "I can't connect to my local AI right now."
        )


    except Exception as error:

        print(
            "OLLAMA ERROR:",
            error
        )


        return (
            "I had trouble processing that."
        )


# ==========================================================
# COMMAND
# ==========================================================

@app.route(
    "/command",
    methods=["POST"]
)
def command():

    try:

        data = request.get_json(
            silent=True
        ) or {}


        text = data.get(
            "text",
            ""
        )


        text = normalize_text(
            text
        )


        if not text:

            return jsonify(
                {
                    "response":
                    "I'm listening."
                }
            )


        print()
        print(
            "WEB:",
            text
        )


        print(
            "NORMALIZED:",
            text.lower()
        )


        # --------------------------------------
        # FAST LOCAL RESPONSE
        # --------------------------------------

        fast_answer = local_response(
            text
        )


        if fast_answer:

            print(
                "JARVIS:",
                fast_answer
            )


            return jsonify(
                {
                    "response":
                    fast_answer
                }
            )


        # --------------------------------------
        # LOCAL AI
        # --------------------------------------

        answer = ask_ollama(
            text
        )


        print(
            "JARVIS:",
            answer
        )


        return jsonify(
            {
                "response":
                answer
            }
        )


    except Exception as error:

        print(
            "COMMAND ERROR:",
            error
        )


        return jsonify(
            {
                "response":
                "Something went wrong."
            }
        ), 500


# ==========================================================
# HOME PAGE
# ==========================================================

@app.route("/")
def home():

    return send_from_directory(
        "web",
        "index.html"
    )


# ==========================================================
# STATIC FILES
# ==========================================================

@app.route("/<path:path>")
def static_files(path):

    file_path = os.path.join(
        "web",
        path
    )


    if os.path.isfile(file_path):

        return send_from_directory(
            "web",
            path
        )


    return (
        "Not found",
        404
    )


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )

    print(
        "              J A R V I S"
    )

    print(
        "=========================================="
    )

    print()

    print(
        "LOCAL AI:",
        MODEL
    )

    print()

    print(
        "Open your browser:"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print()


    app.run(

        host="127.0.0.1",

        port=5000,

        debug=False,

        threaded=True
    )