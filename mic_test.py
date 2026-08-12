import speech_recognition as sr

recognizer = sr.Recognizer()

print("=================================")
print("        JARVIS VOICE MODE")
print("=================================")
print("Say 'exit' to stop JARVIS.\n")

while True:
    try:
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(
                source,
                timeout=10,
                phrase_time_limit=5
            )

        print("Processing...")

        command = recognizer.recognize_google(audio)
        command = command.lower().strip()

        print("You:", command)

        if command == "exit" or "shut down jarvis" in command:
            print("JARVIS: Goodbye.")
            break

        elif "hello" in command or "hi jarvis" in command:
            print("JARVIS: Hello! How can I help you?")

        elif "your name" in command:
            print("JARVIS: I am JARVIS.")

        elif "turn on" in command and "fan" in command:
            print("JARVIS: Fan command received.")

        elif "turn off" in command and "fan" in command:
            print("JARVIS: Fan OFF command received.")

        elif "turn on" in command and "light" in command:
            print("JARVIS: Light command received.")

        elif "turn off" in command and "light" in command:
            print("JARVIS: Light OFF command received.")

        else:
            print("JARVIS: I don't understand that command yet.")

    except sr.UnknownValueError:
        print("JARVIS: I couldn't understand that.")

    except sr.WaitTimeoutError:
        print("JARVIS: I didn't hear anything.")

    except sr.RequestError as error:
        print("JARVIS: Speech service error:", error)

    except Exception as error:
        print("JARVIS: Error:", error)