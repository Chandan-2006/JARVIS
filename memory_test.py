import json
import os

MEMORY_FILE = "memory.json"


def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            return json.load(file)

    return {}


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=4)


memory = load_memory()

print("=================================")
print("       JARVIS MEMORY TEST")
print("=================================")

while True:
    command = input("\nYou: ").strip()

    if command.lower() == "exit":
        print("JARVIS: Goodbye.")
        break

    if command.lower().startswith("my name is "):
        name = command[11:].strip()

        if name:
            memory["name"] = name
            save_memory(memory)
            print(f"JARVIS: Nice to meet you, {name}. I will remember your name.")

    elif command.lower() == "do you know my name":
        if "name" in memory:
            print(f"JARVIS: Yes. Your name is {memory['name']}.")
        else:
            print("JARVIS: I don't know your name yet.")

    else:
        print("JARVIS: I don't know that command yet.")