const status = document.getElementById("status");
const subStatus = document.getElementById("sub-status");
const conversation = document.getElementById("conversation");
const voiceStatus = document.getElementById("voiceStatus");

const SpeechRecognition =
    window.SpeechRecognition ||
    window.webkitSpeechRecognition;

const speech = window.speechSynthesis;

let listening = false;
let speaking = false;
let processing = false;


// ==============================
// JARVIS SPEAK
// ==============================

function speak(text) {

    speaking = true;

    speech.cancel();

    const message =
        new SpeechSynthesisUtterance(text);

    message.lang = "en-US";
    message.rate = 0.95;
    message.pitch = 1;
    message.volume = 1;

    message.onstart = () => {

        status.textContent =
            "JARVIS SPEAKING";

        subStatus.textContent =
            "Please wait";

        voiceStatus.textContent =
            "SPEAKING";
    };


    message.onend = () => {

        speaking = false;

        status.textContent =
            "JARVIS READY";

        subStatus.textContent =
            "Listening for your next command";

        voiceStatus.textContent =
            "READY";

        setTimeout(
            startListening,
            500
        );
    };


    speech.speak(message);
}


// ==============================
// ADD MESSAGE
// ==============================

function addMessage(sender, text) {

    const message =
        document.createElement("div");

    message.className = "message";


    const name =
        document.createElement("strong");

    name.textContent = sender;


    const content =
        document.createElement("span");

    content.textContent = text;


    message.appendChild(name);

    message.appendChild(content);

    conversation.appendChild(message);


    conversation.scrollTop =
        conversation.scrollHeight;
}


// ==============================
// VOICE SYSTEM
// ==============================

if (!SpeechRecognition) {

    status.textContent =
        "VOICE NOT SUPPORTED";

    subStatus.textContent =
        "Use Chrome or Edge";

    voiceStatus.textContent =
        "UNAVAILABLE";

} else {

    const recognition =
        new SpeechRecognition();


    recognition.lang = "en-US";

    recognition.continuous = false;

    recognition.interimResults = false;

    recognition.maxAlternatives = 3;


    // ==============================
    // START LISTENING
    // ==============================

    function startListening() {

        if (
            listening ||
            speaking ||
            processing
        ) {
            return;
        }


        try {

            recognition.start();

        } catch (error) {

            console.log(
                "Recognition start:",
                error
            );
        }
    }


    // ==============================
    // LISTENING STARTED
    // ==============================

    recognition.onstart = () => {

        listening = true;


        status.textContent =
            "LISTENING...";


        subStatus.textContent =
            "Speak naturally";


        voiceStatus.textContent =
            "LISTENING";
    };


    // ==============================
    // SPEECH RESULT
    // ==============================

    recognition.onresult =
        async (event) => {

            listening = false;

            processing = true;


            let text =
                event.results[0][0]
                    .transcript
                    .trim();


            if (!text) {

                processing = false;

                startListening();

                return;
            }


            console.log(
                "Recognized:",
                text
            );


            // Remove wake word if present

            const lower =
                text.toLowerCase();


            if (
                lower.startsWith("jarvis ")
            ) {

                text =
                    text.substring(7)
                        .trim();

            }


            if (!text) {

                processing = false;

                status.textContent =
                    "LISTENING...";

                subStatus.textContent =
                    "Yes?";

                voiceStatus.textContent =
                    "LISTENING";


                setTimeout(
                    startListening,
                    500
                );

                return;
            }


            // Ignore accidental instruction

            if (
                lower.includes(
                    "followed by your command"
                )
            ) {

                processing = false;

                startListening();

                return;
            }


            addMessage(
                "YOU",
                text
            );


            status.textContent =
                "THINKING...";


            subStatus.textContent =
                "Processing your command";


            voiceStatus.textContent =
                "PROCESSING";


            try {

                const result =
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


                if (!result.ok) {

                    throw new Error(
                        "Server error " +
                        result.status
                    );
                }


                const data =
                    await result.json();


                const response =
                    data.response ||
                    "I don't have a response yet.";


                addMessage(
                    "JARVIS",
                    response
                );


                processing = false;


                speak(response);


            } catch (error) {

                console.error(error);


                processing = false;


                status.textContent =
                    "CONNECTION ERROR";


                subStatus.textContent =
                    "Trying again";


                voiceStatus.textContent =
                    "ERROR";


                setTimeout(
                    startListening,
                    1500
                );
            }
        };


    // ==============================
    // RECOGNITION END
    // ==============================

    recognition.onend = () => {

        listening = false;


        if (
            !speaking &&
            !processing
        ) {

            setTimeout(
                startListening,
                500
            );
        }
    };


    // ==============================
    // RECOGNITION ERROR
    // ==============================

    recognition.onerror =
        (event) => {

            listening = false;


            console.log(
                "Recognition error:",
                event.error
            );


            if (
                event.error ===
                "not-allowed"
            ) {

                status.textContent =
                    "MICROPHONE BLOCKED";


                subStatus.textContent =
                    "Allow microphone access";


                voiceStatus.textContent =
                    "BLOCKED";


                return;
            }


            if (
                event.error ===
                "no-speech"
            ) {

                status.textContent =
                    "LISTENING...";


                subStatus.textContent =
                    "I am listening";


                voiceStatus.textContent =
                    "LISTENING";


                setTimeout(
                    startListening,
                    500
                );


                return;
            }


            status.textContent =
                "VOICE ERROR";


            subStatus.textContent =
                "Trying again";


            voiceStatus.textContent =
                "ERROR";


            setTimeout(
                startListening,
                1000
            );
        };


    // ==============================
    // START WHEN PAGE OPENS
    // ==============================

    window.addEventListener(
        "load",
        () => {

            setTimeout(
                startListening,
                1000
            );

        }
    );
}