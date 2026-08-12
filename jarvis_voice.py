import speech_recognition as sr
import pyttsx3

recognizer = sr.Recognizer()

engine = pyttsx3.init()
engine.setProperty("rate", 170)
engine.setProperty("volume", 1.0)


def speak(text):
    print("JARVIS:", text)
    engine.say(text)
    engine.runAndWait()


speak("Hello. I am JARVIS. Voice system initialized.")
speak("Say exit when you want me to stop.")


while True:
    try:
        with sr.Microphone() as source:
            print("\nListening...")
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
            speak("Goodbye.")
            break

        elif "hello" in command or "hi jarvis" in command:
            speak("Hello! How can I help you?")

        elif "your name" in command:
            speak("I am JARVIS.")

        elif "turn on" in command and "fan" in command:
            speak("Fan command received.")

        elif "turn off" in command and "fan" in command:
            speak("Fan off command received.")

        elif "turn on" in command and "light" in command:
            speak("Light command received.")

        elif "turn off" in command and "light" in command:
            speak("Light off command received.")

        else:
            speak("I don't understand that command yet.")

    except sr.UnknownValueError:
        speak("I couldn't understand that.")

    except sr.WaitTimeoutError:
        speak("I didn't hear anything.")

    except sr.RequestError:
        speak("The speech recognition service is unavailable.")

    except Exception as error:
        print("Error:", error)
        speak("Something went wrong.")