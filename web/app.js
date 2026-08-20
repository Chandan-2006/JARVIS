// ==========================================================
// JARVIS VOICE SYSTEM
// CLICK MIC ONCE -> LISTEN -> THINK -> SPEAK -> LISTEN AGAIN
// ==========================================================

const voiceState = document.getElementById("voiceState");
const statusText = document.getElementById("statusText");
const messages = document.getElementById("messages");
const commandInput = document.getElementById("commandInput");
const sendButton = document.getElementById("sendButton");
const micButton = document.getElementById("micButton");
const voiceSystem = document.getElementById("voiceSystem");


// ==========================================================
// VARIABLES
// ==========================================================

let recognition = null;

let voiceEnabled = false;
let listening = false;
let speaking = false;
let processing = false;
let starting = false;

let restartTimer = null;


// ==========================================================
// CORE MODE
// ==========================================================

function setCoreMode(mode) {

    document.body.classList.remove(
        "jarvis-listening",
        "jarvis-thinking",
        "jarvis-speaking",
        "jarvis-idle"
    );

    document.body.classList.add(
        "jarvis-" + mode
    );

    if (voiceState) {

        if (mode === "listening") {
            voiceState.textContent = "LISTENING";
        }

        else if (mode === "thinking") {
            voiceState.textContent = "THINKING";
        }

        else if (mode === "speaking") {
            voiceState.textContent = "SPEAKING";
        }

        else {
            voiceState.textContent = "READY";
        }
    }

    if (voiceSystem) {
        voiceSystem.textContent = mode.toUpperCase();
    }
}


// ==========================================================
// STATUS
// ==========================================================

function setStatus(mainText, subText) {

    if (voiceState) {
        voiceState.textContent = mainText;
    }

    if (statusText) {
        statusText.textContent = subText;
    }
}


// ==========================================================
// CHECK BROWSER SUPPORT
// ==========================================================

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


if (!SpeechRecognition) {

    console.error(
        "Speech Recognition is not supported."
    );

    setStatus(
        "VOICE NOT SUPPORTED",
        "Please use Google Chrome or Microsoft Edge."
    );

    setCoreMode("idle");

}


// ==========================================================
// CREATE RECOGNITION
// ==========================================================

else {

    recognition = new SpeechRecognition();

    // IMPORTANT
    // false is more reliable with Chrome.
    recognition.continuous = false;

    recognition.interimResults = true;

    recognition.lang = "en-IN";

    recognition.maxAlternatives = 1;


    // ======================================================
    // MICROPHONE STARTED
    // ======================================================

    recognition.onstart = function () {

        starting = false;

        listening = true;

        setStatus(
            "LISTENING",
            "I'm listening, Sir..."
        );

        setCoreMode("listening");

        updateMicButton(true);

        console.log(
            "JARVIS MICROPHONE: LISTENING"
        );
    };


    // ======================================================
    // SPEECH RESULT
    // ======================================================

    recognition.onresult = async function (event) {

        if (speaking) {
            return;
        }

        if (processing) {
            return;
        }


        let finalText = "";

        let interimText = "";


        for (
            let i = event.resultIndex;
            i < event.results.length;
            i++
        ) {

            const result =
                event.results[i];

            const transcript =
                result[0]
                    .transcript
                    .trim();


            if (!transcript) {
                continue;
            }


            if (result.isFinal) {

                finalText +=
                    transcript + " ";

            }

            else {

                interimText +=
                    transcript + " ";
            }
        }


        // --------------------------------------------------
        // SHOW LIVE SPEECH
        // --------------------------------------------------

        if (
            interimText &&
            statusText
        ) {

            statusText.textContent =
                interimText;
        }


        // --------------------------------------------------
        // FINAL SPEECH
        // --------------------------------------------------

        const text =
            finalText
                .replace(/\s+/g, " ")
                .trim();


        if (!text) {
            return;
        }


        console.log(
            "YOU:",
            text
        );


        // Stop listening while processing.
        stopRecognition();


        processing = true;


        addMessage(
            "YOU",
            text,
            "user-message"
        );


        setStatus(
            "THINKING",
            "JARVIS is processing your request, Sir..."
        );

        setCoreMode("thinking");


        await sendCommand(text);
    };


    // ======================================================
    // ERROR
    // ======================================================

    recognition.onerror = function (event) {

        starting = false;

        listening = false;

        updateMicButton(false);


        console.log(
            "VOICE ERROR:",
            event.error
        );


        // --------------------------------------------------
        // NO SPEECH
        // --------------------------------------------------

        if (
            event.error === "no-speech"
        ) {

            if (voiceEnabled && !speaking && !processing) {

                setStatus(
                    "READY",
                    "I didn't hear anything. Listening again..."
                );

                setCoreMode("idle");

                scheduleListen(500);
            }

            return;
        }


        // --------------------------------------------------
        // ABORTED
        // --------------------------------------------------

        if (
            event.error === "aborted"
        ) {

            if (
                voiceEnabled &&
                !speaking &&
                !processing
            ) {

                scheduleListen(500);
            }

            return;
        }


        // --------------------------------------------------
        // MICROPHONE ERROR
        // --------------------------------------------------

        if (
            event.error === "audio-capture"
        ) {

            setStatus(
                "MICROPHONE ERROR",
                "Check that your microphone is connected."
            );

            setCoreMode("idle");

            return;
        }


        // --------------------------------------------------
        // PERMISSION BLOCKED
        // --------------------------------------------------

        if (
            event.error === "not-allowed"
        ) {

            setStatus(
                "MICROPHONE BLOCKED",
                "Click the microphone icon in Chrome's address bar and allow access."
            );

            setCoreMode("idle");

            voiceEnabled = false;

            return;
        }


        // --------------------------------------------------
        // OTHER ERROR
        // --------------------------------------------------

        setStatus(
            "VOICE ERROR",
            event.error || "Voice recognition error."
        );

        setCoreMode("idle");


        if (
            voiceEnabled &&
            !speaking &&
            !processing
        ) {

            scheduleListen(1500);
        }
    };


    // ======================================================
    // RECOGNITION ENDED
    // ======================================================

    recognition.onend = function () {

        listening = false;

        starting = false;

        updateMicButton(false);


        console.log(
            "JARVIS MICROPHONE: ENDED"
        );


        if (!voiceEnabled) {
            return;
        }


        if (speaking) {
            return;
        }


        if (processing) {
            return;
        }


        // Automatically listen again.
        scheduleListen(500);
    };
}


// ==========================================================
// STOP RECOGNITION
// ==========================================================

function stopRecognition() {

    if (!recognition) {
        return;
    }


    listening = false;


    try {

        recognition.stop();

    }

    catch (error) {

        console.log(
            "STOP ERROR:",
            error
        );
    }


    updateMicButton(false);
}


// ==========================================================
// START LISTENING
// ==========================================================

function startListening() {

    if (!recognition) {
        return;
    }


    if (!voiceEnabled) {
        return;
    }


    if (speaking) {
        return;
    }


    if (processing) {
        return;
    }


    if (listening) {
        return;
    }


    if (starting) {
        return;
    }


    starting = true;


    try {

        recognition.start();

    }

    catch (error) {

        starting = false;

        console.log(
            "START ERROR:",
            error
        );


        scheduleListen(1000);
    }
}


// ==========================================================
// SCHEDULE LISTEN
// ==========================================================

function scheduleListen(delay = 500) {

    if (!recognition) {
        return;
    }


    if (!voiceEnabled) {
        return;
    }


    if (speaking) {
        return;
    }


    if (processing) {
        return;
    }


    if (listening) {
        return;
    }


    if (starting) {
        return;
    }


    if (restartTimer) {

        clearTimeout(
            restartTimer
        );
    }


    restartTimer =
        setTimeout(
            function () {

                restartTimer = null;

                startListening();

            },
            delay
        );
}


// ==========================================================
// SEND COMMAND TO SERVER
// ==========================================================

async function sendCommand(text) {

    try {

        console.log(
            "COMMAND:",
            text
        );


        const response =
            await fetch(
                "/command",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify({
                            text: text
                        })
                }
            );


        if (!response.ok) {

            throw new Error(
                "Server returned HTTP " +
                response.status
            );
        }


        const data =
            await response.json();


        const answer =
            data.response ||
            data.message ||
            "I'm listening, Sir.";


        console.log(
            "JARVIS:",
            answer
        );


        addMessage(
            "JARVIS",
            answer,
            "jarvis-message"
        );


        processing = false;


        speak(answer);

    }


    catch (error) {

        console.error(
            "COMMAND ERROR:",
            error
        );


        processing = false;


        const answer =
            "I could not connect to my local system, Sir.";


        addMessage(
            "JARVIS",
            answer,
            "jarvis-message"
        );


        speak(answer);
    }
}


// ==========================================================
// ADD MESSAGE
// ==========================================================

function addMessage(
    speaker,
    text,
    className
) {

    if (!messages) {
        return;
    }


    const message =
        document.createElement("div");


    message.className =
        "message " + className;


    const name =
        document.createElement("span");


    name.className =
        "message-name";


    name.textContent =
        speaker;


    const content =
        document.createElement("p");


    content.textContent =
        text;


    message.appendChild(name);

    message.appendChild(content);

    messages.appendChild(message);


    messages.scrollTop =
        messages.scrollHeight;
}


// ==========================================================
// JARVIS SPEAK
// ==========================================================

function speak(text) {

    if (!window.speechSynthesis) {

        speaking = false;

        processing = false;


        setStatus(
            "READY",
            "Listening for your command, Sir..."
        );

        setCoreMode("idle");


        if (voiceEnabled) {
            scheduleListen(500);
        }

        return;
    }


    speaking = true;


    // Stop microphone while JARVIS speaks.
    stopRecognition();


    setStatus(
        "SPEAKING",
        "JARVIS is replying, Sir..."
    );

    setCoreMode("speaking");


    window.speechSynthesis.cancel();


    const utterance =
        new SpeechSynthesisUtterance(text);


    utterance.lang = "en-IN";

    utterance.rate = 1.05;

    utterance.pitch = 0.9;

    utterance.volume = 1.0;


    // ======================================================
    // SELECT BEST VOICE
    // ======================================================

    const voices =
        window.speechSynthesis.getVoices();


    const preferredNames = [

        "Microsoft Ravi",
        "Microsoft Arjun",
        "Google UK English Male",
        "Google US English",
        "Google English",
        "Microsoft David",
        "David"

    ];


    let selectedVoice = null;


    for (
        const preferred
        of preferredNames
    ) {

        selectedVoice =
            voices.find(
                voice =>
                    voice.name
                        .toLowerCase()
                        .includes(
                            preferred.toLowerCase()
                        )
            );


        if (selectedVoice) {
            break;
        }
    }


    // Fallback to English voice.
    if (!selectedVoice) {

        selectedVoice =
            voices.find(
                voice =>
                    voice.lang
                        .toLowerCase()
                        .startsWith("en")
            );
    }


    if (selectedVoice) {

        utterance.voice =
            selectedVoice;


        console.log(
            "JARVIS VOICE:",
            selectedVoice.name
        );
    }


    // ======================================================
    // SPEECH FINISHED
    // ======================================================

    utterance.onend =
        function () {

            console.log(
                "JARVIS SPEECH FINISHED"
            );


            speaking = false;

            processing = false;


            setStatus(
                "READY",
                "Listening for your command, Sir..."
            );

            setCoreMode("idle");


            if (voiceEnabled) {

                scheduleListen(600);
            }
        };


    // ======================================================
    // SPEECH ERROR
    // ======================================================

    utterance.onerror =
        function (event) {

            console.log(
                "SPEECH ERROR:",
                event.error
            );


            speaking = false;

            processing = false;


            setStatus(
                "READY",
                "Listening for your command, Sir..."
            );

            setCoreMode("idle");


            if (voiceEnabled) {

                scheduleListen(700);
            }
        };


    window.speechSynthesis.speak(
        utterance
    );
}


// ==========================================================
// TEXT COMMAND
// ==========================================================

async function sendTextCommand() {

    if (!commandInput) {
        return;
    }


    const text =
        commandInput.value
            .trim();


    if (!text) {
        return;
    }


    commandInput.value = "";


    stopRecognition();


    processing = true;


    addMessage(
        "YOU",
        text,
        "user-message"
    );


    setStatus(
        "THINKING",
        "Processing your request, Sir..."
    );

    setCoreMode("thinking");


    await sendCommand(text);
}


// ==========================================================
// SEND BUTTON
// ==========================================================

if (sendButton) {

    sendButton.addEventListener(
        "click",
        sendTextCommand
    );
}


// ==========================================================
// ENTER KEY
// ==========================================================

if (commandInput) {

    commandInput.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Enter") {

                event.preventDefault();

                sendTextCommand();
            }
        }
    );
}


// ==========================================================
// MICROPHONE BUTTON
// ==========================================================

if (micButton) {

    micButton.addEventListener(
        "click",
        function () {

            console.log(
                "MIC BUTTON CLICKED"
            );


            // ------------------------------------------------
            // STOP VOICE
            // ------------------------------------------------

            if (voiceEnabled) {

                voiceEnabled = false;

                clearTimeout(
                    restartTimer
                );

                restartTimer = null;


                stopRecognition();


                setStatus(
                    "READY",
                    "Voice control stopped. Press 🎤 to start."
                );

                setCoreMode("idle");


                updateMicButton(false);


                return;
            }


            // ------------------------------------------------
            // START VOICE
            // ------------------------------------------------

            voiceEnabled = true;


            setStatus(
                "STARTING",
                "Starting microphone..."
            );


            setCoreMode("idle");


            updateMicButton(true);


            startListening();
        }
    );
}


// ==========================================================
// MICROPHONE BUTTON UI
// ==========================================================

function updateMicButton(active) {

    if (!micButton) {
        return;
    }


    if (active) {

        micButton.classList.add(
            "mic-active"
        );

        micButton.title =
            "Stop voice control";

    }

    else {

        micButton.classList.remove(
            "mic-active"
        );

        micButton.title =
            "Start voice control";
    }
}


// ==========================================================
// LOAD AVAILABLE VOICES
// ==========================================================

if (window.speechSynthesis) {

    window.speechSynthesis.onvoiceschanged =
        function () {

            const voices =
                window.speechSynthesis
                    .getVoices();


            console.log(
                "AVAILABLE VOICES:",
                voices.map(
                    voice => voice.name
                )
            );
        };
}


// ==========================================================
// PAGE LOAD
// ==========================================================

window.addEventListener(
    "load",
    function () {

        console.log(
            "================================"
        );

        console.log(
            "JARVIS VOICE SYSTEM"
        );

        console.log(
            "CLICK MICROPHONE TO START"
        );

        console.log(
            "================================"
        );


        voiceEnabled = false;

        listening = false;

        speaking = false;

        processing = false;

        starting = false;


        setStatus(
            "READY",
            "Press 🎤 to start voice control."
        );

        setCoreMode("idle");


        updateMicButton(false);
    }
);