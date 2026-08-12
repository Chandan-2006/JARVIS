import speech_recognition as sr
import subprocess
import json
import os

recognizer = sr.Recognizer()

MEMORY_FILE = "memory.json"


# =========================
# MEMORY
# =========================

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
        except:
            return {}

    return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=4)


memory = load_memory()


# =========================
# JARVIS VOICE
# =========================

def speak(text):
    print("JARVIS:", text)

    safe_text = text.replace("'", "''")

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"Add-Type -AssemblyName System.Speech; "
        f"$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Speak('{safe_text}'); "
        f"$s.Dispose()"
    ]

    subprocess.run(
        command,
        stdout=subprocess.DEVNULL
    )


# =========================
# LISTEN
# =========================

def listen():
    with sr.Microphone() as source:

        print("\nListening...")

        recognizer.adjust_for_ambient_noise(
            source,
            duration=0.5
        )

        audio = recognizer.listen(
            source,
            timeout=10,
            phrase_time_limit=6
        )

    print("Processing...")

    return recognizer.recognize_google(
        audio
    ).lower().strip()


# =========================
# START JARVIS
# =========================

speak("Hello. I am JARVIS.")
speak("Memory system initialized.")
speak("Voice system initialized.")
speak("Say exit when you want me to stop.")


# =========================
# MAIN LOOP
# =========================

while True:

    try:

        command = listen()

        print("You:", command)


        # EXIT
        if (
            command == "exit"
            or "shut down jarvis" in command
        ):

            speak("Goodbye.")
            break


        # HELLO
        elif (
            "hello" in command
            or "hi jarvis" in command
        ):

            speak(
                "Hello! How can I help you?"
            )


        # SAVE NAME
        elif "my name is" in command:

            name = command.split(
                "my name is",
                1
            )[1].strip()

            if name:

                memory["name"] = name

                save_memory(memory)

                speak(
                    f"Nice to meet you, {name}. "
                    "I will remember your name."
                )


        # ASK MY NAME
        elif (
            "do you know my name" in command
            or "did you know my name" in command
            or "what is my name" in command
            or "what's my name" in command
            or "who am i" in command
        ):

            if "name" in memory:

                speak(
                    f"Yes. Your name is "
                    f"{memory['name']}."
                )

            else:

                speak(
                    "I don't know your name yet."
                )


        # JARVIS NAME
        elif (
            "what is your name" in command
            or "what's your name" in command
            or "who are you" in command
        ):

            speak(
                "I am JARVIS."
            )


        # WHAT CAN YOU DO
        elif (
            "what can you do" in command
            or "how can you help me" in command
        ):

            speak(
                "I can listen to your voice, "
                "remember information you tell me, "
                "and control supported devices."
            )


        # HOW ARE YOU
        elif (
            "how are you" in command
            or "how are you doing" in command
        ):

            speak(
                "I am functioning normally. "
                "Thank you for asking."
            )


        # GREETINGS
        elif (
            "good morning" in command
            or "good evening" in command
            or "good afternoon" in command
        ):

            speak(
                "Hello. I hope you are having a good day."
            )


        # FAN ON
        elif (
            "turn on" in command
            and "fan" in command
        ):

            speak(
                "Fan command received."
            )


        # FAN OFF
        elif (
            "turn off" in command
            and "fan" in command
        ):

            speak(
                "Fan off command received."
            )


        # LIGHT ON
        elif (
            "turn on" in command
            and "light" in command
        ):

            speak(
                "Light command received."
            )


        # LIGHT OFF
        elif (
            "turn off" in command
            and "light" in command
        ):

            speak(
                "Light off command received."
            )


        # UNKNOWN COMMAND
        else:

            speak(
                "I don't understand that command yet."
            )


    # =========================
    # ERROR HANDLING
    # =========================

    except sr.UnknownValueError:

        speak(
            "I couldn't understand that."
        )


    except sr.WaitTimeoutError:

        speak(
            "I didn't hear anything."
        )


    except sr.RequestError:

        speak(
            "The speech recognition service "
            "is unavailable."
        )


    except Exception as error:

        print("Error:", error)

        speak(
            "Something went wrong."
        )