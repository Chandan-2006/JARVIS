import pyttsx3

while True:
    text = input("Type what JARVIS should say: ").strip()

    if text.lower() == "exit":
        break

    print("JARVIS:", text)

    engine = pyttsx3.init()
    engine.setProperty("rate", 170)
    engine.setProperty("volume", 1.0)

    engine.say(text)
    engine.runAndWait()

    engine.stop()

print("Voice test complete.")