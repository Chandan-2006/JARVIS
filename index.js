const readline = require("readline-sync");

console.log("=================================");
console.log("        JARVIS is starting...");
console.log("=================================");
console.log("Hello! I am JARVIS.");
console.log("System initialized successfully.");
console.log("Type 'exit' to shut me down.\n");

while (true) {
    const command = readline.question("You: ").toLowerCase().trim();

    if (command === "exit") {
        console.log("JARVIS: Goodbye.");
        break;
    }

    if (command.includes("hello") || command.includes("hi")) {
        console.log("JARVIS: Hello! How can I help you?");
    }
    else if (command.includes("your name")) {
        console.log("JARVIS: I am JARVIS.");
    }
    else if (command.includes("turn on") && command.includes("fan")) {
        console.log("JARVIS: Fan command received.");
    }
    else if (command.includes("turn off") && command.includes("fan")) {
        console.log("JARVIS: Fan OFF command received.");
    }
    else if (command.includes("turn on") && command.includes("light")) {
        console.log("JARVIS: Light command received.");
    }
    else if (command.includes("turn off") && command.includes("light")) {
        console.log("JARVIS: Light OFF command received.");
    }
    else {
        console.log("JARVIS: I don't understand that command yet.");
    }
}