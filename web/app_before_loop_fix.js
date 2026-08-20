// ==========================================================
// JARVIS AUTOMATIC VOICE INTERFACE
// ==========================================================

const micButton = document.getElementById("micButton");
const status = document.getElementById("status");
const subStatus = document.getElementById("sub-status");
const conversation = document.getElementById("conversation");
const voiceStatus = document.getElementById("voiceStatus");

let recognition = null;
let listening = false;
let speaking = false;
let restarting = false;


// ==========================================================
// SPEECH RECOGNITION
// ==========================================================

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;


if (SpeechRecognition) {

    recognition = new SpeechRecognition();

    recognition.continuous = false;

    recognition.interimResults = false;

    recognition.lang = "en-IN";

    recognition.maxAlternatives = 1;


    // ------------------------------------------------------
    // START LISTENING
    // ------------------------------------------------------

    recognition.onstart = function () {

        listening = true;

        setStatus(
            "LISTENING...",
            "Speak naturally"
        );

        if (voiceStatus) {
            voiceStatus.textContent = "LISTENING";
        }

        console.log("VOICE: listening");
    };


    // ------------------------------------------------------
    // SPEECH RESULT
    // ------------------------------------------------------

    recognition.onresult = async function (event) {

        const text =
            event.results[0][0].transcript.trim();


        if (!text) {
            return;
        }


        console.log(
            "YOU:",
            text
        );


        addMessage(
            "YOU",
            text,
            "user-message"
        );


        setStatus(
            "THINKING...",
            "JARVIS is preparing a reply"
        );


        if (voiceStatus) {
            voiceStatus.textContent = "THINKING";
        }


        await sendCommand(text);
    };


    // ------------------------------------------------------
    // VOICE ERROR
    // ------------------------------------------------------

    recognition.onerror = function (event) {

        console.log(
            "VOICE ERROR:",
            event.error
        );


        listening = false;


        // Ignore normal browser interruptions.

        if (
            event.error === "no-speech" ||
            event.error === "aborted"
        ) {

            return;
        }


        setStatus(
            "VOICE ERROR",
            "Please check microphone permission"
        );


        if (voiceStatus) {
            voiceStatus.textContent = "ERROR";
        }
    };


    // ------------------------------------------------------
    // VOICE END
    // ------------------------------------------------------

    recognition.onend = function () {

        listening = false;


        console.log(
            "VOICE: ended"
        );


        // Don't restart while JARVIS is speaking.

        if (speaking) {
            return;
        }


        setStatus(
            "JARVIS READY",
            'Say "JARVIS" followed by your command'
        );


        if (voiceStatus) {
            voiceStatus.textContent = "READY";
        }


        // Automatic listening again.

        autoListen();
    };

}


// ==========================================================
// STATUS
// ==========================================================

function setStatus(mainText, subText) {

    if (status) {
        status.textContent = mainText;
    }


    if (subStatus) {
        subStatus.textContent = subText;
    }
}


// ==========================================================
// AUTOMATIC LISTENING
// ==========================================================

function autoListen() {

    if (!recognition) {
        return;
    }


    if (listening) {
        return;
    }


    if (speaking) {
        return;
    }


    if (restarting) {
        return;
    }


    restarting = true;


    setTimeout(function () {

        restarting = false;


        try {

            recognition.start();

        } catch (error) {

            console.log(
                "AUTO LISTEN ERROR:",
                error
            );

        }

    }, 250);
}


// ==========================================================
// SEND COMMAND TO PYTHON
// ==========================================================

async function sendCommand(text) {

    try {

        const response =
            await fetch(
                "/command",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        text: text
                    })
                }
            );


        const data =
            await response.json();


        const answer =
            data.response ||
            "I'm listening.";


        console.log(
            "JARVIS:",
            answer
        );


        addMessage(
            "JARVIS",
            answer,
            "jarvis-message"
        );


        speak(answer);


    } catch (error) {

        console.error(
            "COMMAND ERROR:",
            error
        );


        const answer =
            "I could not connect to my local system.";


        addMessage(
            "JARVIS",
            answer,
            "jarvis-message"
        );


        speak(answer);
    }
}


// ==========================================================
// CONVERSATION DISPLAY
// ==========================================================

function addMessage(
    speaker,
    text,
    className
) {

    if (!conversation) {
        return;
    }


    const message =
        document.createElement("div");


    message.className =
        "message " + className;


    const name =
        document.createElement("strong");


    name.textContent =
        speaker;


    const content =
        document.createElement("span");


    content.textContent =
        text;


    message.appendChild(
        name
    );


    message.appendChild(
        content
    );


    conversation.appendChild(
        message
    );


    // Always show newest message.

    conversation.scrollTop =
        conversation.scrollHeight;
}


// ==========================================================
// JARVIS VOICE
// ==========================================================

function speak(text) {

    if (!window.speechSynthesis) {

        autoListen();

        return;
    }


    speaking = true;


    if (recognition && listening) {

        try {
            recognition.stop();
        } catch (error) {
            console.log(error);
        }
    }


    setStatus(
        "SPEAKING...",
        "JARVIS is replying"
    );


    if (voiceStatus) {
        voiceStatus.textContent = "SPEAKING";
    }


    // Stop previous speech.

    window.speechSynthesis.cancel();


    const utterance =
        new SpeechSynthesisUtterance(text);


    utterance.lang =
        "en-IN";


    // FAST VOICE

    utterance.rate =
        1.45;


    // Slightly deeper assistant voice.

    utterance.pitch =
        0.9;


    utterance.volume =
        1.0;


    // ------------------------------------------------------
    // SELECT VOICE
    // ------------------------------------------------------

    const voices =
        window.speechSynthesis.getVoices();


    let selectedVoice =
        null;


    const preferredNames = [

        "Microsoft Ravi",

        "Microsoft Arjun",

        "Google UK English Male",

        "Google English",

        "Microsoft David",

        "David"

    ];


    for (
        const preferred of preferredNames
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


    // ------------------------------------------------------
    // SPEECH FINISHED
    // ------------------------------------------------------

    utterance.onend =
        function () {

            speaking = false;


            setStatus(
                "JARVIS READY",
                'Speak naturally'
            );


            if (voiceStatus) {
                voiceStatus.textContent =
                    "LISTENING";
            }


            // Immediately listen again.

            autoListen();
        };


    // ------------------------------------------------------
    // SPEECH ERROR
    // ------------------------------------------------------

    utterance.onerror =
        function (event) {

            console.log(
                "SPEECH ERROR:",
                event.error
            );


            speaking = false;


            setStatus(
                "JARVIS READY",
                "Speak naturally"
            );


            if (voiceStatus) {
                voiceStatus.textContent =
                    "READY";
            }


            autoListen();
        };


    window.speechSynthesis.speak(
        utterance
    );
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
                    voice =>
                        voice.name
                )
            );
        };
}


// ==========================================================
// START AUTOMATIC MODE
// ==========================================================

window.addEventListener(
    "load",
    function () {

        console.log(
            "JARVIS AUTOMATIC VOICE MODE"
        );


        setStatus(
            "JARVIS READY",
            "Starting microphone..."
        );


        setTimeout(
            autoListen,
            800
        );
    }
);