import subprocess

def speak(text):
    print("JARVIS:", text)

    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        f"Add-Type -AssemblyName System.Speech; "
        f"$s=New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.Speak('{text}'); "
        f"$s.Dispose()"
    ]

    subprocess.run(command)


speak("Hello. I am JARVIS.")
speak("The voice system is working.")
speak("I can now speak more than one sentence.")