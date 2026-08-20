from flask import Flask, request, jsonify, send_from_directory
import requests
import re
import time
import os
import json
import threading
import queue
import urllib.parse

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# ==========================================================
# J A R V I S
# LOCAL AI + LIVE WEB + BROWSER CONTROL
# ==========================================================

app = Flask(
    __name__,
    static_folder="web",
    static_url_path=""
)


# ==========================================================
# SETTINGS
# ==========================================================

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"

MODEL = "Jadio/Qwen3_4b_instruct_q4km:latest"

OLLAMA_TIMEOUT = 20
WEB_TIMEOUT = 15
MAX_HISTORY = 6

TAVILY_API_KEY = os.environ.get(
    "TAVILY_API_KEY",
    ""
)

TAVILY_URL = "https://api.tavily.com/search"

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)
# ==========================================================
# TAVILY
# ==========================================================
MEMORY_FILE = os.path.join(
    BASE_DIR,
    "memory.json"
)


# ==========================================================
# MEMORY
# ==========================================================

memory_lock = threading.Lock()

MEMORY = {
    "name": "Chandan",
    "facts": []
}


def load_memory():

    global MEMORY

    try:

        if os.path.exists(MEMORY_FILE):

            with open(
                MEMORY_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                saved = json.load(file)

            if isinstance(saved, dict):

                if saved.get("name"):
                    MEMORY["name"] = str(
                        saved["name"]
                    )

                if isinstance(
                    saved.get("facts"),
                    list
                ):
                    MEMORY["facts"] = saved["facts"]

        print("MEMORY LOADED:", MEMORY)

    except Exception as error:

        print(
            "MEMORY LOAD ERROR:",
            repr(error)
        )


def save_memory():

    try:

        with memory_lock:

            with open(
                MEMORY_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    MEMORY,
                    file,
                    indent=2,
                    ensure_ascii=False
                )

    except Exception as error:

        print(
            "MEMORY SAVE ERROR:",
            repr(error)
        )


load_memory()


# ==========================================================
# CONVERSATION MEMORY
# ==========================================================

conversation_history = []

history_lock = threading.Lock()


def add_to_history(user_text, answer):

    global conversation_history

    with history_lock:

        conversation_history.append({
            "role": "user",
            "content": user_text
        })

        conversation_history.append({
            "role": "assistant",
            "content": answer
        })

        if len(conversation_history) > 12:

            conversation_history = (
                conversation_history[-12:]
            )


# ==========================================================
# BROWSER STATE
# ==========================================================

browser_state_lock = threading.Lock()

BROWSER_STATE = {

    "site": "",
    "url": "",
    "query": "",
    "video_title": "",
    "video_url": "",
    "video_active": False,
    "video_paused": True,
    "video_time": 0
}


def update_browser_state(**values):

    with browser_state_lock:

        BROWSER_STATE.update(values)

    print(
        "BROWSER STATE:",
        BROWSER_STATE
    )


def get_browser_state():

    with browser_state_lock:

        return dict(BROWSER_STATE)


# ==========================================================
# LAST ACTION
# ==========================================================

last_action_lock = threading.Lock()

LAST_ACTION = {

    "type": "",
    "url": "",
    "query": "",
    "description": "",
    "timestamp": 0
}


def remember_action(
    action_type,
    url="",
    query="",
    description=""
):

    global LAST_ACTION

    with last_action_lock:

        LAST_ACTION = {

            "type": action_type,
            "url": url,
            "query": query,
            "description": description,
            "timestamp": time.time()
        }

    print(
        "LAST ACTION:",
        LAST_ACTION
    )


def get_last_action():

    with last_action_lock:

        return dict(LAST_ACTION)


# ==========================================================
# PERSONALITY
# ==========================================================

SYSTEM_PROMPT = """
You are JARVIS, Chandan's personal AI assistant.

Always call Chandan "Sir".

Speak naturally and concisely.

Important rules:

- Browser actions are controlled by Python and Playwright.
- Never claim a browser action happened unless Python confirmed it.
- Never invent browser actions.
- Understand natural language and imperfect English.
- Use previous conversation context.
- Use current browser context when useful.
- If Python reports a browser action result, trust it.
- Normal movie, song, trailer and video requests are allowed.
- Always address Chandan as Sir.
"""


# ==========================================================
# TEXT HELPERS
# ==========================================================

def normalize_text(text):

    if not text:
        return ""

    text = str(text).strip()

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text


def clean_command_prefix(text):

    text = normalize_text(text)

    text = re.sub(
        r"^(jarvis|javis)\s*[,;:]?\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    return text.strip()


def clean_ai_response(text):

    if not text:
        return ""

    text = str(text).strip()

    text = re.sub(
        r"<think>.*?</think>",
        "",
        text,
        flags=re.DOTALL | re.IGNORECASE
    )

    text = re.sub(
        r"```.*?```",
        "",
        text,
        flags=re.DOTALL
    )

    for pattern in [
        r"^analysis:\s*",
        r"^reasoning:\s*",
        r"^thoughts:\s*",
        r"^answer:\s*",
        r"^jarvis:\s*",
        r"^assistant:\s*"
    ]:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


# ==========================================================
# PLAYWRIGHT BROWSER CONTROLLER
# ==========================================================

class BrowserController:

    def __init__(self):

        self.command_queue = queue.Queue()

        self.ready = threading.Event()

        self.thread = threading.Thread(
            target=self._browser_thread,
            daemon=True
        )

        self.thread.start()

        self.ready.wait(
            timeout=30
        )


    def _browser_thread(self):

        try:

            print()
            print(
                "PLAYWRIGHT: starting browser..."
            )

            with sync_playwright() as p:

                browser = p.chromium.launch(

                    headless=False,

                    args=[
                        "--start-maximized",
                        "--autoplay-policy=no-user-gesture-required"
                    ]
                )

                context = browser.new_context(
                    viewport=None
                )

                page = context.new_page()

                self.page = page

                self.ready.set()

                print(
                    "PLAYWRIGHT: browser ready"
                )

                while True:

                    item = self.command_queue.get()

                    if item is None:
                        break

                    function, args, result_holder = item

                    try:

                        result = function(
                            page,
                            *args
                        )

                        result_holder["result"] = result

                    except Exception as error:

                        print(
                            "BROWSER ACTION ERROR:",
                            repr(error)
                        )

                        result_holder["result"] = {
                            "success": False,
                            "error": str(error)
                        }

                    finally:

                        result_holder[
                            "event"
                        ].set()

                try:
                    context.close()
                except Exception:
                    pass

                try:
                    browser.close()
                except Exception:
                    pass

        except Exception as error:

            print(
                "PLAYWRIGHT START ERROR:",
                repr(error)
            )

            self.ready.set()


    def execute(
        self,
        function,
        *args,
        timeout=40
    ):

        if not self.ready.is_set():

            return {
                "success": False,
                "error": "Browser is not ready"
            }

        result_holder = {

            "event": threading.Event(),

            "result": {
                "success": False,
                "error": "Browser unavailable"
            }
        }

        self.command_queue.put(
            (
                function,
                args,
                result_holder
            )
        )

        finished = result_holder[
            "event"
        ].wait(
            timeout=timeout
        )

        if not finished:

            return {
                "success": False,
                "error": "Browser action timed out"
            }

        return result_holder[
            "result"
        ]


BROWSER = BrowserController()


# ==========================================================
# OPEN URL
# ==========================================================

def browser_open_url(page, url):

    print(
        "BROWSER NAVIGATE:",
        url
    )

    try:

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=20000
        )

        time.sleep(1)

        current_url = page.url

        update_browser_state(
            url=current_url
        )

        return {
            "success": True,
            "url": current_url
        }

    except PlaywrightTimeoutError:

        current_url = page.url

        if current_url and current_url != "about:blank":

            update_browser_state(
                url=current_url
            )

            return {
                "success": True,
                "url": current_url,
                "warning": "Navigation timeout"
            }

        return {
            "success": False,
            "error": "Navigation timeout"
        }

    except Exception as error:

        print(
            "BROWSER NAVIGATION ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "error": str(error)
        }


# ==========================================================
# GOOGLE
# ==========================================================

def browser_google_search(page, query):

    url = (
        "https://www.google.com/search?q="
        +
        urllib.parse.quote_plus(query)
    )

    result = browser_open_url(
        page,
        url
    )

    if result.get("success"):

        update_browser_state(
            site="google",
            query=query,
            url=result.get(
                "url",
                url
            )
        )

    return result


# ==========================================================
# YOUTUBE SEARCH
# ==========================================================

def browser_youtube_search(page, query):

    url = (
        "https://www.youtube.com/results?search_query="
        +
        urllib.parse.quote_plus(query)
    )

    result = browser_open_url(
        page,
        url
    )

    if result.get("success"):

        update_browser_state(
            site="youtube",
            query=query,
            url=result.get(
                "url",
                url
            ),
            video_active=False,
            video_paused=True,
            video_time=0
        )

    return result


# ==========================================================
# YOUTUBE STATE
# ==========================================================

def youtube_get_state(page):

    try:

        state = page.evaluate(
            """
            () => {

                const video =
                    document.querySelector("video");

                if (!video) {

                    return {
                        found: false,
                        paused: true,
                        currentTime: 0,
                        ended: false,
                        duration: 0
                    };
                }

                return {

                    found: true,

                    paused:
                        video.paused,

                    currentTime:
                        Number(
                            video.currentTime || 0
                        ),

                    ended:
                        video.ended,

                    duration:
                        Number(
                            video.duration || 0
                        )
                };
            }
            """
        )

        print(
            "YOUTUBE STATE:",
            state
        )

        return state

    except Exception as error:

        print(
            "YOUTUBE STATE ERROR:",
            repr(error)
        )

        return {
            "found": False,
            "paused": True,
            "currentTime": 0,
            "ended": False,
            "duration": 0
        }


# ==========================================================
# YOUTUBE PLAY
# ==========================================================

def browser_youtube_play(page, query):

    print()
    print(
        "YOUTUBE PLAY:",
        query
    )

    search_url = (
        "https://www.youtube.com/results?search_query="
        +
        urllib.parse.quote_plus(query)
    )

    try:

        # --------------------------------------------------
        # SEARCH
        # --------------------------------------------------

        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=20000
        )

        time.sleep(2)

        locator = page.locator(
            'a[href*="/watch?v="]'
        )

        count = locator.count()

        print(
            "YOUTUBE VIDEO LINKS:",
            count
        )

        if count == 0:

            return {
                "success": False,
                "error": "No YouTube video found"
            }

        # --------------------------------------------------
        # GET REAL WATCH URL
        # --------------------------------------------------

        video_url = None

        for index in range(
            min(count, 20)
        ):

            try:

                href = locator.nth(
                    index
                ).get_attribute(
                    "href"
                )

                if href and "/watch?v=" in href:

                    video_url = href

                    if video_url.startswith("/"):

                        video_url = (
                            "https://www.youtube.com"
                            +
                            video_url
                        )

                    break

            except Exception:

                continue

        if not video_url:

            return {
                "success": False,
                "error":
                    "Could not find real YouTube video URL"
            }

        print(
            "YOUTUBE FOUND VIDEO:",
            video_url
        )

        # --------------------------------------------------
        # OPEN REAL VIDEO DIRECTLY
        # --------------------------------------------------

        print(
            "YOUTUBE DIRECT VIDEO URL:",
            video_url
        )

        page.goto(
            video_url,
            wait_until="domcontentloaded",
            timeout=20000
        )

        time.sleep(3)

        print(
            "YOUTUBE OPEN RESULT:",
            page.url
        )

        # --------------------------------------------------
        # WAIT FOR HTML5 VIDEO
        # --------------------------------------------------

        try:

            page.locator(
                "video"
            ).wait_for(
                state="attached",
                timeout=12000
            )

        except Exception:

            pass

        time.sleep(1)

        # --------------------------------------------------
        # JARVIS VIDEO CONTROLLER
        # --------------------------------------------------

        page.evaluate(
            """
            () => {

                window.__jarvisWantedPlaying = true;

                const video =
                    document.querySelector("video");

                if (!video) {
                    return false;
                }

                if (!video.__jarvisControllerInstalled) {

                    video.__jarvisControllerInstalled = true;

                    video.addEventListener(
                        "pause",
                        () => {

                            if (
                                window.__jarvisWantedPlaying
                                &&
                                !video.ended
                            ) {

                                setTimeout(
                                    () => {

                                        if (
                                            window.__jarvisWantedPlaying
                                            &&
                                            video.paused
                                            &&
                                            !video.ended
                                        ) {

                                            video.play().catch(
                                                () => {}
                                            );
                                        }

                                    },
                                    200
                                );
                            }
                        }
                    );
                }

                return true;
            }
            """
        )

        # --------------------------------------------------
        # PLAY
        # --------------------------------------------------

        page.evaluate(
            """
            async () => {

                const video =
                    document.querySelector("video");

                if (!video) {
                    return false;
                }

                window.__jarvisWantedPlaying = true;

                try {

                    await video.play();

                } catch (error) {

                    // Button fallback below.
                }

                return !video.paused;
            }
            """
        )

        time.sleep(1)

        state1 = youtube_get_state(page)

        print(
            "YOUTUBE STATE AFTER HTML5:",
            state1
        )

        # --------------------------------------------------
        # PLAY BUTTON
        # --------------------------------------------------

        if state1.get("paused"):

            try:

                button = page.locator(
                    ".ytp-play-button"
                ).first

                if button.count() > 0:

                    aria = (
                        button.get_attribute(
                            "aria-label"
                        )
                        or ""
                    )

                    print(
                        "YOUTUBE PLAY BUTTON:",
                        aria
                    )

                    if "Play" in aria:

                        button.click(
                            force=True,
                            timeout=5000
                        )

            except Exception as error:

                print(
                    "PLAY BUTTON ERROR:",
                    repr(error)
                )

        time.sleep(1)

        # --------------------------------------------------
        # KEYBOARD FALLBACK
        # --------------------------------------------------

        state2 = youtube_get_state(page)

        if state2.get("paused"):

            try:

                print(
                    "YOUTUBE KEYBOARD FALLBACK: K"
                )

                page.keyboard.press("k")

            except Exception as error:

                print(
                    "KEYBOARD PLAY ERROR:",
                    repr(error)
                )

        time.sleep(1)

        # --------------------------------------------------
        # FINAL CHECK
        # --------------------------------------------------

        before = youtube_get_state(page)

        time.sleep(1.5)

        after = youtube_get_state(page)

        print(
            "VIDEO CHECK BEFORE:",
            before
        )

        print(
            "VIDEO CHECK AFTER:",
            after
        )

        playing = (

            after.get("found")

            and not after.get("paused")

            and
            after.get(
                "currentTime",
                0
            )
            >
            before.get(
                "currentTime",
                0
            )
            + 0.1
        )

        # --------------------------------------------------
        # SECOND PLAY ATTEMPT
        # --------------------------------------------------

        if not playing:

            page.evaluate(
                """
                () => {

                    const video =
                        document.querySelector("video");

                    if (!video) {
                        return false;
                    }

                    window.__jarvisWantedPlaying = true;

                    video.play().catch(
                        () => {}
                    );

                    return true;
                }
                """
            )

            time.sleep(1)

            after = youtube_get_state(page)

            playing = (
                after.get("found")
                and not after.get("paused")
            )

        if not playing:

            return {
                "success": False,
                "error":
                    "YouTube video opened but playback could not be maintained",
                "url": page.url,
                "video_url": page.url,
                "state": after
            }

        # --------------------------------------------------
        # SAVE STATE
        # --------------------------------------------------

        update_browser_state(
            site="youtube",
            url=page.url,
            query=query,
            video_url=page.url,
            video_active=True,
            video_paused=False,
            video_time=after.get(
                "currentTime",
                0
            )
        )

        return {
            "success": True,
            "url": page.url,
            "video_url": page.url,
            "state": after
        }

    except Exception as error:

        print(
            "YOUTUBE PLAY ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "error": str(error)
        }


# ==========================================================
# YOUTUBE PAUSE
# ==========================================================

def browser_youtube_pause(page):

    print(
        "YOUTUBE PAUSE"
    )

    try:

        state = youtube_get_state(page)

        if not state.get("found"):

            return {
                "success": False,
                "error":
                    "No YouTube video is currently open"
            }

        # --------------------------------------------------
        # DISABLE AUTO PLAY CONTROLLER
        # --------------------------------------------------

        page.evaluate(
            """
            () => {

                window.__jarvisWantedPlaying = false;

                const video =
                    document.querySelector("video");

                if (video) {

                    video.pause();
                }
            }
            """
        )

        time.sleep(0.7)

        verify = youtube_get_state(page)

        print(
            "PAUSE VERIFY:",
            verify
        )

        # --------------------------------------------------
        # KEYBOARD FALLBACK
        # --------------------------------------------------

        if not verify.get("paused"):

            try:

                page.keyboard.press("k")

            except Exception:
                pass

            time.sleep(0.7)

            verify = youtube_get_state(page)

        # --------------------------------------------------
        # SECOND HTML5 PAUSE
        # --------------------------------------------------

        if not verify.get("paused"):

            page.evaluate(
                """
                () => {

                    const video =
                        document.querySelector("video");

                    if (video) {
                        video.pause();
                    }
                }
                """
            )

            time.sleep(0.5)

            verify = youtube_get_state(page)

        if not verify.get("paused"):

            return {
                "success": False,
                "error":
                    "YouTube video is still playing",
                "state": verify
            }

        update_browser_state(
            site="youtube",
            url=page.url,
            video_active=True,
            video_paused=True,
            video_time=verify.get(
                "currentTime",
                0
            )
        )

        return {
            "success": True,
            "state": verify
        }

    except Exception as error:

        print(
            "YOUTUBE PAUSE ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "error": str(error)
        }


# ==========================================================
# YOUTUBE RESUME
# ==========================================================

def browser_youtube_resume(page):

    print(
        "YOUTUBE RESUME"
    )

    try:

        state = youtube_get_state(page)

        if not state.get("found"):

            return {
                "success": False,
                "error":
                    "No YouTube video is currently open"
            }

        # --------------------------------------------------
        # ENABLE PLAY CONTROLLER
        # --------------------------------------------------

        page.evaluate(
            """
            () => {

                window.__jarvisWantedPlaying = true;

                const video =
                    document.querySelector("video");

                if (!video) {
                    return false;
                }

                video.play().catch(
                    () => {}
                );

                return true;
            }
            """
        )

        time.sleep(1)

        verify1 = youtube_get_state(page)

        print(
            "RESUME VERIFY 1:",
            verify1
        )

        # --------------------------------------------------
        # BUTTON FALLBACK
        # --------------------------------------------------

        if verify1.get("paused"):

            try:

                button = page.locator(
                    ".ytp-play-button"
                ).first

                if button.count() > 0:

                    aria = (
                        button.get_attribute(
                            "aria-label"
                        )
                        or ""
                    )

                    print(
                        "RESUME BUTTON:",
                        aria
                    )

                    if "Play" in aria:

                        button.click(
                            force=True,
                            timeout=5000
                        )

            except Exception as error:

                print(
                    "RESUME BUTTON ERROR:",
                    repr(error)
                )

        time.sleep(0.8)

        # --------------------------------------------------
        # KEYBOARD FALLBACK
        # --------------------------------------------------

        verify2 = youtube_get_state(page)

        if verify2.get("paused"):

            try:

                print(
                    "RESUME KEYBOARD FALLBACK: K"
                )

                page.keyboard.press("k")

            except Exception as error:

                print(
                    "RESUME KEY ERROR:",
                    repr(error)
                )

        time.sleep(1)

        verify3 = youtube_get_state(page)

        print(
            "RESUME VERIFY 3:",
            verify3
        )

        # --------------------------------------------------
        # FINAL HTML5 ATTEMPT
        # --------------------------------------------------

        if verify3.get("paused"):

            page.evaluate(
                """
                () => {

                    const video =
                        document.querySelector("video");

                    if (video) {

                        window.__jarvisWantedPlaying = true;

                        video.play().catch(
                            () => {}
                        );
                    }
                }
                """
            )

            time.sleep(1)

            verify3 = youtube_get_state(page)

        if not verify3.get("paused"):

            update_browser_state(
                site="youtube",
                url=page.url,
                video_active=True,
                video_paused=False,
                video_time=verify3.get(
                    "currentTime",
                    0
                )
            )

            return {
                "success": True,
                "state": verify3
            }

        return {
            "success": False,
            "error":
                "YouTube video did not resume",
            "state": verify3
        }

    except Exception as error:

        print(
            "YOUTUBE RESUME ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "error": str(error)
        }


# ==========================================================
# BACK
# ==========================================================

def browser_back(page):

    try:

        page.go_back(
            wait_until="domcontentloaded",
            timeout=15000
        )

        update_browser_state(
            url=page.url
        )

        return {
            "success": True,
            "url": page.url
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error)
        }


# ==========================================================
# FORWARD
# ==========================================================

def browser_forward(page):

    try:

        page.go_forward(
            wait_until="domcontentloaded",
            timeout=15000
        )

        update_browser_state(
            url=page.url
        )

        return {
            "success": True,
            "url": page.url
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error)
        }


# ==========================================================
# REFRESH
# ==========================================================

def browser_refresh(page):

    try:

        page.reload(
            wait_until="domcontentloaded",
            timeout=15000
        )

        update_browser_state(
            url=page.url
        )

        return {
            "success": True,
            "url": page.url
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error)
        }


# ==========================================================
# SITE ALIASES
# ==========================================================

SITE_ALIASES = {

    "google":
        "https://www.google.com",

    "youtube":
        "https://www.youtube.com",

    "gmail":
        "https://mail.google.com",

    "outlook":
        "https://outlook.live.com",

    "facebook":
        "https://www.facebook.com",

    "instagram":
        "https://www.instagram.com",

    "whatsapp":
        "https://web.whatsapp.com",

    "github":
        "https://github.com",

    "chatgpt":
        "https://chatgpt.com",

    "amazon":
        "https://www.amazon.in",

    "flipkart":
        "https://www.flipkart.com"
}


# ==========================================================
# COMMAND EXTRACTION
# ==========================================================

def extract_google_query(text):

    cleaned = clean_command_prefix(text)

    patterns = [

        r"(?:open\s+)?google\s+(?:and\s+)?search\s+(.+)$",

        r"(?:open\s+)?google\s+(?:and\s+)?type\s+(.+)$",

        r"search\s+google\s+for\s+(.+)$",

        r"search\s+(.+?)\s+on\s+google$",

        r"search\s+for\s+(.+?)\s+on\s+google$"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            cleaned,
            re.IGNORECASE
        )

        if match:

            return re.sub(
                r"[.!?]+$",
                "",
                match.group(1).strip()
            ).strip()

    return None


def extract_youtube_play(text):

    cleaned = clean_command_prefix(text)

    patterns = [

        r"^(?:in\s+)?youtube\s+(?:and\s+)?play\s+(.+)$",

        r"^youtube\s+play\s+(.+)$",

        r"^play\s+(.+?)\s+on\s+youtube$",

        r"^play\s+(.+?)\s+(?:song|video|trailer)"
        r"\s+on\s+youtube$",

        r"^open\s+youtube\s+and\s+play\s+(.+)$",

        r"^open\s+youtube\s+play\s+(.+)$"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            cleaned,
            re.IGNORECASE
        )

        if match:

            return re.sub(
                r"[.!?]+$",
                "",
                match.group(1).strip()
            ).strip()

    return None


def extract_youtube_search(text):

    cleaned = clean_command_prefix(text)

    patterns = [

        r"^(?:in\s+)?youtube\s+(?:and\s+)?search\s+(.+)$",

        r"^search\s+youtube\s+for\s+(.+)$",

        r"^search\s+(.+?)\s+on\s+youtube$",

        r"^youtube\s+search\s+(.+)$",

        r"^open\s+youtube\s+for\s+(.+)$"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            cleaned,
            re.IGNORECASE
        )

        if match:

            return re.sub(
                r"[.!?]+$",
                "",
                match.group(1).strip()
            ).strip()

    return None


def extract_website(text):

    cleaned = clean_command_prefix(text)

    match = re.search(

        r"\b(?:open|go\s+to|visit|launch)\s+"
        r"(https?://[^\s]+|www\.[^\s]+|"
        r"[a-zA-Z0-9-]+\.[a-zA-Z]{2,}"
        r"(?:/[^\s]*)?)",

        cleaned,
        re.IGNORECASE
    )

    if match:

        site = match.group(1).rstrip(
            ".,!?"
        )

        if not site.startswith(
            ("http://", "https://")
        ):

            site = "https://" + site

        return site

    return None


# ==========================================================
# NATURAL VIDEO QUERY
# ==========================================================

def extract_natural_youtube_video(text):

    cleaned = clean_command_prefix(text)

    lower = cleaned.lower().strip()

    state = get_browser_state()

    youtube_context = (
        state.get("site") == "youtube"
        or
        "youtube.com" in
        state.get("url", "").lower()
    )

    video_words = [
        "video",
        "trailer",
        "song",
        "music",
        "movie",
        "clip",
        "episode"
    ]

    looks_like_video = any(
        word in lower
        for word in video_words
    )

    if not youtube_context and not looks_like_video:

        return None

    patterns = [

        r"^play\s+(?:the\s+)?(.+)$",

        r"^watch\s+(?:the\s+)?(.+)$",

        r"^show\s+(?:me\s+)?(?:the\s+)?(.+)$",

        r"^put\s+on\s+(?:the\s+)?(.+)$",

        r"^launch\s+(?:the\s+)?(.+)$"
    ]

    for pattern in patterns:

        match = re.match(
            pattern,
            lower,
            re.IGNORECASE
        )

        if not match:
            continue

        query = match.group(1).strip()

        query = re.sub(
            r"\s+on\s+youtube$",
            "",
            query,
            flags=re.IGNORECASE
        )

        query = re.sub(
            r"[.!?,]+$",
            "",
            query
        ).strip()

        if query.lower() in {
            "it",
            "this",
            "the video",
            "video",
            "the trailer",
            "trailer"
        }:

            return None

        return query

    return None


# ==========================================================
# RETRY
# ==========================================================

def retry_last_action():

    action = get_last_action()

    action_type = action.get("type")

    query = action.get("query")

    url = action.get("url")

    if action_type == "youtube_play":

        result = BROWSER.execute(
            browser_youtube_play,
            query,
            timeout=45
        )

        if result.get("success"):

            return {
                "handled": True,
                "success": True,
                "type": "youtube_play",
                "message":
                    f"I retried it and started "
                    f"{query} on YouTube, Sir."
            }

    if action_type == "youtube_search":

        result = BROWSER.execute(
            browser_youtube_search,
            query,
            timeout=30
        )

        if result.get("success"):

            return {
                "handled": True,
                "success": True,
                "type": "youtube_search",
                "message":
                    f"I retried the YouTube search "
                    f"for {query}, Sir."
            }

    if action_type == "google":

        result = BROWSER.execute(
            browser_google_search,
            query,
            timeout=30
        )

        if result.get("success"):

            return {
                "handled": True,
                "success": True,
                "type": "google",
                "message":
                    f"I retried the Google search "
                    f"for {query}, Sir."
            }

    if action_type == "website":

        result = BROWSER.execute(
            browser_open_url,
            url,
            timeout=30
        )

        if result.get("success"):

            return {
                "handled": True,
                "success": True,
                "type": "website",
                "message":
                    "I retried it and opened "
                    "the website, Sir."
            }

    return {
        "handled": True,
        "success": False,
        "type": "retry",
        "message":
            "I retried the previous action, Sir, "
            "but it still did not succeed."
    }


# ==========================================================
# BROWSER ACTION SYSTEM
# ==========================================================

def perform_action(text):

    cleaned = clean_command_prefix(text)

    lower = cleaned.lower().strip()

    print()
    print(
        "ACTION CHECK:",
        cleaned
    )

    state = get_browser_state()

    youtube_context = (
        state.get("site") == "youtube"
        or
        "youtube.com" in
        state.get("url", "").lower()
    )


    # ======================================================
    # RETRY
    # ======================================================

    if re.fullmatch(
        r"(retry|again|try again|do it again)",
        lower
    ):

        return retry_last_action()


    # ======================================================
    # PAUSE - NATURAL LANGUAGE
    # ======================================================

    pause_match = re.search(
        r"\b(pause|stop)\b",
        lower
    )

    if youtube_context and pause_match:

        result = BROWSER.execute(
            browser_youtube_pause,
            timeout=20
        )

        if result.get("success"):

            return {
                "handled": True,
                "success": True,
                "type": "youtube_pause",
                "message":
                    "The video is paused, Sir."
            }

        return {
            "handled": True,
            "success": False,
            "type": "youtube_pause",
            "message":
                "I couldn't pause the video, Sir."
        }


    # ======================================================
    # RESUME / CONTINUE
    # ======================================================

    resume_match = re.search(
        r"\b(resume|continue)\b",
        lower
    )

    if youtube_context and resume_match:

        result = BROWSER.execute(
            browser_youtube_resume,
            timeout=20
        )

        if result.get("success"):

            return {
                "handled": True,
                "success": True,
                "type": "youtube_resume",
                "message":
                    "The video is playing again, Sir."
            }

        return {
            "handled": True,
            "success": False,
            "type": "youtube_resume",
            "message":
                "I couldn't resume the video, Sir."
        }


    # ======================================================
    # PLAY CURRENT VIDEO
    # ======================================================

    if youtube_context and re.fullmatch(
        r"(play|start)\s+(it|this|the\s+video|the\s+trailer|video|trailer)",
        lower
    ):

        result = BROWSER.execute(
            browser_youtube_resume,
            timeout=20
        )

        if result.get("success"):

            return {
                "handled": True,
                "success": True,
                "type": "youtube_resume",
                "message":
                    "The video is playing again, Sir."
            }

        return {
            "handled": True,
            "success": False,
            "type": "youtube_resume",
            "message":
                "I couldn't resume the video, Sir."
        }


    # ======================================================
    # BACK
    # ======================================================

    if re.fullmatch(
        r"(go\s+)?back",
        lower
    ):

        result = BROWSER.execute(
            browser_back,
            timeout=20
        )

        if result.get("success"):

            remember_action(
                "back",
                result.get("url", "")
            )

            return {
                "handled": True,
                "success": True,
                "type": "back",
                "message":
                    "I went back, Sir."
            }


    # ======================================================
    # FORWARD
    # ======================================================

    if re.fullmatch(
        r"(go\s+)?forward",
        lower
    ):

        result = BROWSER.execute(
            browser_forward,
            timeout=20
        )

        if result.get("success"):

            remember_action(
                "forward",
                result.get("url", "")
            )

            return {
                "handled": True,
                "success": True,
                "type": "forward",
                "message":
                    "I went forward, Sir."
            }


    # ======================================================
    # REFRESH
    # ======================================================

    if re.fullmatch(
        r"(refresh|reload)(\s+(the\s+)?page)?",
        lower
    ):

        result = BROWSER.execute(
            browser_refresh,
            timeout=20
        )

        if result.get("success"):

            remember_action(
                "refresh",
                result.get("url", "")
            )

            return {
                "handled": True,
                "success": True,
                "type": "refresh",
                "message":
                    "I refreshed the page, Sir."
            }


    # ======================================================
    # OPEN GOOGLE + PLAY YOUTUBE
    # ======================================================

    combined = re.match(
        r"^open\s+google\s+and\s+play\s+(.+)$",
        lower,
        re.IGNORECASE
    )

    if combined:

        query = combined.group(1).strip()

        query = re.sub(
            r"[.!?]+$",
            "",
            query
        ).strip()

        result = BROWSER.execute(
            browser_youtube_play,
            query,
            timeout=45
        )

        if result.get("success"):

            remember_action(
                "youtube_play",
                result.get("url", ""),
                query,
                f"Played {query} on YouTube"
            )

            return {
                "handled": True,
                "success": True,
                "type": "youtube_play",
                "message":
                    f"I started {query} on YouTube, Sir."
            }

        return {
            "handled": True,
            "success": False,
            "type": "youtube_play",
            "message":
                f"I couldn't start {query} on YouTube, Sir."
        }


    # ======================================================
    # EXPLICIT YOUTUBE PLAY
    # ======================================================

    youtube_play_query = extract_youtube_play(
        cleaned
    )

    if youtube_play_query:

        result = BROWSER.execute(
            browser_youtube_play,
            youtube_play_query,
            timeout=45
        )

        if result.get("success"):

            remember_action(
                "youtube_play",
                result.get("url", ""),
                youtube_play_query,
                f"Played {youtube_play_query} on YouTube"
            )

            return {
                "handled": True,
                "success": True,
                "type": "youtube_play",
                "message":
                    f"I started "
                    f"{youtube_play_query} "
                    f"on YouTube, Sir."
            }

        return {
            "handled": True,
            "success": False,
            "type": "youtube_play",
            "message":
                f"I couldn't start "
                f"{youtube_play_query} "
                f"on YouTube, Sir."
        }


    # ======================================================
    # NATURAL YOUTUBE PLAY
    # ======================================================

    natural_query = extract_natural_youtube_video(
        cleaned
    )

    if natural_query:

        result = BROWSER.execute(
            browser_youtube_play,
            natural_query,
            timeout=45
        )

        if result.get("success"):

            remember_action(
                "youtube_play",
                result.get("url", ""),
                natural_query,
                f"Played {natural_query} on YouTube"
            )

            return {
                "handled": True,
                "success": True,
                "type": "youtube_play",
                "message":
                    f"I started "
                    f"{natural_query} "
                    f"on YouTube, Sir."
            }

        return {
            "handled": True,
            "success": False,
            "type": "youtube_play",
            "message":
                f"I couldn't start "
                f"{natural_query} "
                f"on YouTube, Sir."
        }


    # ======================================================
    # YOUTUBE SEARCH
    # ======================================================

    youtube_search_query = extract_youtube_search(
        cleaned
    )

    if youtube_search_query:

        result = BROWSER.execute(
            browser_youtube_search,
            youtube_search_query,
            timeout=30
        )

        if result.get("success"):

            remember_action(
                "youtube_search",
                result.get("url", ""),
                youtube_search_query,
                f"Searched YouTube for {youtube_search_query}"
            )

            return {
                "handled": True,
                "success": True,
                "type": "youtube_search",
                "message":
                    f"I searched YouTube for "
                    f"{youtube_search_query}, Sir."
            }


    # ======================================================
    # GOOGLE SEARCH
    # ======================================================

    google_query = extract_google_query(
        cleaned
    )

    if google_query:

        result = BROWSER.execute(
            browser_google_search,
            google_query,
            timeout=30
        )

        if result.get("success"):

            remember_action(
                "google",
                result.get("url", ""),
                google_query,
                f"Searched Google for {google_query}"
            )

            return {
                "handled": True,
                "success": True,
                "type": "google",
                "message":
                    f"I searched Google for "
                    f"{google_query}, Sir."
            }


    # ======================================================
    # OPEN GOOGLE
    # ======================================================

    if re.fullmatch(
        r"(open|launch|go\s+to|visit)\s+google",
        lower
    ):

        result = BROWSER.execute(
            browser_open_url,
            "https://www.google.com",
            timeout=25
        )

        if result.get("success"):

            update_browser_state(
                site="google",
                url=result.get("url", "")
            )

            remember_action(
                "website",
                result.get("url", ""),
                "",
                "Opened Google"
            )

            return {
                "handled": True,
                "success": True,
                "type": "website",
                "message":
                    "Google is open, Sir."
            }


    # ======================================================
    # OPEN YOUTUBE
    # ======================================================

    if re.fullmatch(
        r"(open|launch|go\s+to|visit)\s+youtube",
        lower
    ):

        result = BROWSER.execute(
            browser_open_url,
            "https://www.youtube.com",
            timeout=25
        )

        if result.get("success"):

            update_browser_state(
                site="youtube",
                url=result.get("url", "")
            )

            remember_action(
                "website",
                result.get("url", ""),
                "",
                "Opened YouTube"
            )

            return {
                "handled": True,
                "success": True,
                "type": "website",
                "message":
                    "YouTube is open, Sir."
            }


    # ======================================================
    # SITE ALIASES
    # ======================================================

    for name, url in SITE_ALIASES.items():

        if re.fullmatch(
            rf"(open|launch|visit|go\s+to)\s+"
            rf"{re.escape(name)}",
            lower
        ):

            result = BROWSER.execute(
                browser_open_url,
                url,
                timeout=25
            )

            if result.get("success"):

                update_browser_state(
                    site=name,
                    url=result.get(
                        "url",
                        url
                    )
                )

                remember_action(
                    "website",
                    result.get(
                        "url",
                        url
                    ),
                    "",
                    f"Opened {name}"
                )

                return {
                    "handled": True,
                    "success": True,
                    "type": "website",
                    "message":
                        f"I opened {name}, Sir."
                }

        # ======================================================
    # NATURAL WEBSITE OPENING
    # ======================================================

    natural_site = re.search(
        r"\b(?:open|launch|visit|go\s+to)\s+(.+?)(?:\s+kiya)?[.!?]*$",
        cleaned,
        re.IGNORECASE
    )

    if natural_site:

        site_name = natural_site.group(1).strip()

        # Remove common spoken words
        site_name = re.sub(
            r"\b(the|website|site)\b",
            "",
            site_name,
            flags=re.IGNORECASE
        ).strip()

        # Ignore commands that are clearly not website names
        if site_name and len(site_name) > 2:

            # If user gave a domain, open it directly
            if re.match(
                r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}",
                site_name
            ):

                website_url = site_name

                if not website_url.startswith(
                    ("http://", "https://")
                ):
                    website_url = (
                        "https://" + website_url
                    )

                result = BROWSER.execute(
                    browser_open_url,
                    website_url,
                    timeout=30
                )

                if result.get("success"):

                    remember_action(
                        "website",
                        result.get(
                            "url",
                            website_url
                        ),
                        "",
                        f"Opened {website_url}"
                    )

                    return {
                        "handled": True,
                        "success": True,
                        "type": "website",
                        "message":
                            f"I opened {site_name}, Sir."
                    }

            # Otherwise search Google
            result = BROWSER.execute(
                browser_google_search,
                site_name,
                timeout=30
            )

            if result.get("success"):

                remember_action(
                    "google",
                    result.get(
                        "url",
                        ""
                    ),
                    site_name,
                    f"Searched Google for {site_name}"
                )

                return {
                    "handled": True,
                    "success": True,
                    "type": "google",
                    "message":
                        f"I searched Google for "
                        f"{site_name}, Sir."
                }

    # ======================================================
    # DIRECT WEBSITE
    # ======================================================

    website = extract_website(
        cleaned
    )

    if website:

        result = BROWSER.execute(
            browser_open_url,
            website,
            timeout=30
        )

        if result.get("success"):

            remember_action(
                "website",
                result.get(
                    "url",
                    website
                ),
                "",
                f"Opened {website}"
            )

            return {
                "handled": True,
                "success": True,
                "type": "website",
                "message":
                    f"I opened {website}, Sir."
            }


    return {
        "handled": False
    }


# ==========================================================
# FAST LOCAL RESPONSES
# ==========================================================

def local_response(text):

    lower = text.lower().strip()

    match = re.search(
        r"\bmy name is\s+(.+)",
        text,
        re.IGNORECASE
    )

    if match:

        name = match.group(1).strip()

        name = re.sub(
            r"[.!?]+$",
            "",
            name
        )

        if name:

            MEMORY["name"] = name.title()

            save_memory()

            return (
                "I'll remember that, Sir."
            )

    if re.search(
        r"\b(what is|what's|whats)\s+my\s+name\b",
        lower
    ):

        return (
            f"Your name is "
            f"{MEMORY['name']}, Sir."
        )

    if re.search(
        r"\b(what is|what's|whats)\s+your\s+name\b",
        lower
    ):

        return (
            "I am JARVIS, Sir."
        )

    if re.fullmatch(
        r"(hi|hello|hey)(\s+jarvis)?[.!]?",
        lower
    ):

        return (
            "Hello, Sir. "
            "How can I assist you?"
        )

    if re.fullmatch(
        r"(thanks|thank you|thankyou)"
        r"(\s+jarvis)?[.!]?",
        lower
    ):

        return (
            "You're welcome, Sir."
        )

    if re.fullmatch(
        r"how are you[.!]?",
        lower
    ):

        return (
            "I'm doing great, Sir."
        )

    if re.fullmatch(
        r"(who are you|what are you)[.!]?",
        lower
    ):

        return (
            "I'm JARVIS, your local AI assistant, Sir."
        )

    if re.search(
        r"\bwhat did you just do\b",
        lower
    ):

        action = get_last_action()

        if action.get("description"):

            return (
                f"I "
                f"{action['description'].lower()}, "
                f"Sir."
            )

        return (
            "I haven't performed a browser action yet, Sir."
        )

    return None


# ==========================================================
# WEB SEARCH
# ==========================================================
def needs_web_search(text):

    lower = text.lower().strip()

    # Always use live web for questions where information
    # can change over time.

    patterns = [

        # Time / updates
        r"\blatest\b",
        r"\bupdate\b",
        r"\bupdates\b",
        r"\bnew update\b",
        r"\brecent\b",
        r"\brecently\b",
        r"\btoday\b",
        r"\btomorrow\b",
        r"\byesterday\b",
        r"\bcurrent\b",
        r"\bcurrently\b",
        r"\bright now\b",
        r"\bnow\b",
        r"\bthis week\b",
        r"\bthis month\b",

        # News
        r"\bnews\b",
        r"\bwhat happened\b",
        r"\bwhat's happening\b",
        r"\bwhats happening\b",

        # Movies / films / entertainment
        r"\brelease date\b",
        r"\breleasing\b",
        r"\brelease\b",
        r"\bwhen is .* coming\b",
        r"\bwhen will .* release\b",
        r"\bmovie update\b",
        r"\bfilm update\b",
        r"\bmovie news\b",
        r"\bfilm news\b",
        r"\btrailer\b",
        r"\bteaser\b",
        r"\bcast\b",
        r"\bdirector\b",
        r"\bbox office\b",

        # Weather
        r"\bweather\b",
        r"\btemperature\b",
        r"\bforecast\b",
        r"\brain\b",

        # Sports
        r"\bscore\b",
        r"\bmatch result\b",
        r"\bwho won\b",
        r"\bmatch\b",
        r"\bipl\b",
        r"\bcricket\b",
        r"\bfootball\b",
        r"\bsoccer\b",

        # Prices / finance
        r"\bprice\b",
        r"\bstock price\b",
        r"\bshare price\b",
        r"\bgold price\b",
        r"\bsilver price\b",
        r"\bbitcoin\b",
        r"\bcryptocurrency\b",

        # General live information
        r"\bhow much does\b",
        r"\bhow much is\b",
        r"\bwho is\b",
        r"\bwhere is\b",
        r"\bwhen is\b",
        r"\bwhen will\b",
        r"\bwhat is the latest\b",
        r"\bwhat are the latest\b"
    ]

    return any(
        re.search(
            pattern,
            lower,
            re.IGNORECASE
        )
        for pattern in patterns
    )


def build_search_query(text):

    query = normalize_text(text)

    query = re.sub(
        r"^(jarvis|javis)\s*[,;:]?\s*",
        "",
        query,
        flags=re.IGNORECASE
    )

    return query.strip()


# ==========================================================
# TAVILY
# ==========================================================
def get_live_weather():

    try:

        # Bengaluru / Karnataka area
        latitude = 12.9716
        longitude = 77.5946

        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&current=temperature_2m,relative_humidity_2m,"
            "apparent_temperature,weather_code,wind_speed_10m"
            "&timezone=auto"
        )

        response = requests.get(
            url,
            timeout=8
        )

        response.raise_for_status()

        data = response.json()

        current = data.get(
            "current",
            {}
        )

        temperature = current.get(
            "temperature_2m"
        )

        feels_like = current.get(
            "apparent_temperature"
        )

        humidity = current.get(
            "relative_humidity_2m"
        )

        wind = current.get(
            "wind_speed_10m"
        )

        weather_code = current.get(
            "weather_code"
        )

        weather_names = {
            0: "clear sky",
            1: "mainly clear",
            2: "partly cloudy",
            3: "overcast",
            45: "foggy",
            48: "foggy",
            51: "light drizzle",
            53: "moderate drizzle",
            55: "heavy drizzle",
            61: "light rain",
            63: "moderate rain",
            65: "heavy rain",
            80: "rain showers",
            81: "rain showers",
            82: "heavy rain showers",
            95: "thunderstorm",
            96: "thunderstorm with hail",
            99: "thunderstorm with hail"
        }

        condition = weather_names.get(
            weather_code,
            "unknown conditions"
        )

        return (
            f"Sir, the current weather is "
            f"{temperature}°C with {condition}. "
            f"It feels like {feels_like}°C, "
            f"humidity is {humidity}%, "
            f"and wind speed is {wind} km/h."
        )

    except Exception as error:

        print(
            "WEATHER ERROR:",
            repr(error)
        )

        return None

def tavily_search(query):

    print()
    print(
        "WEB SEARCH:",
        query
    )

    if not TAVILY_API_KEY:

        print(
            "TAVILY ERROR: API KEY NOT FOUND"
        )

        return []

    payload = {

        "api_key":
            TAVILY_API_KEY,

        "query":
            query,

        "search_depth":
            "basic",

        "max_results":
            5,

        "include_answer":
            False
    }

    try:

        response = requests.post(
            TAVILY_URL,
            json=payload,
            timeout=WEB_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        results = data.get(
            "results",
            []
        )

        print(
            "WEB RESULTS:",
            len(results)
        )

        return results

    except Exception as error:

        print(
            "TAVILY ERROR:",
            repr(error)
        )

        return []


def format_web_results(results):

    if not results:
        return ""

    output = []

    for index, result in enumerate(
        results[:5],
        start=1
    ):

        title = result.get(
            "title",
            ""
        )

        content = result.get(
            "content",
            ""
        )

        url = result.get(
            "url",
            ""
        )

        content = re.sub(
            r"\s+",
            " ",
            str(content)
        ).strip()

        if len(content) > 700:

            content = (
                content[:700]
                + "..."
            )

        output.append(
            f"{index}. {title}\n"
            f"{content}\n"
            f"Source: {url}"
        )

    return "\n\n".join(output)


# ==========================================================
# OLLAMA
# ==========================================================

def ask_ollama(
    user_text,
    web_results=""
):

    with history_lock:

        recent_history = list(
            conversation_history[
                -MAX_HISTORY:
            ]
        )

    memory_text = (
        f"Chandan's name is "
        f"{MEMORY['name']}."
    )

    if MEMORY.get("facts"):

        memory_text += (
            "\nUseful remembered facts:"
        )

        for fact in MEMORY[
            "facts"
        ][-5:]:

            memory_text += (
                f"\n- {fact}"
            )

    messages = [

        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },

        {
            "role": "system",
            "content": memory_text
        },

        {
            "role": "system",
            "content":
                "Current browser context:\n"
                +
                str(
                    get_browser_state()
                )
        },

        {
            "role": "system",
            "content":
                "Previous action:\n"
                +
                str(
                    get_last_action()
                )
        }
    ]

    if web_results:

        messages.append({

            "role": "system",

            "content":
                "LIVE WEB SEARCH RESULTS\n\n"
                +
                web_results
        })

    messages.extend(
        recent_history
    )

    messages.append({

        "role": "user",

        "content":
            user_text
    })

    payload = {

        "model":
            MODEL,

        "messages":
            messages,

        "stream":
            False,

        "think":
            False,

        "keep_alive":
            "10m",

        "options": {

            "num_predict":
                100,

            "temperature":
                0.2,

            "num_ctx":
                2048,

            "top_p":
                0.7,

            "repeat_penalty":
                1.05
        }
    }

    try:

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=OLLAMA_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        answer = (
            data
            .get(
                "message",
                {}
            )
            .get(
                "content",
                ""
            )
        )

        answer = clean_ai_response(
            answer
        )

        if not answer:

            answer = (
                "I'm listening, Sir."
            )

        add_to_history(
            user_text,
            answer
        )

        return answer

    except requests.exceptions.Timeout:

        return (
            "My local AI is taking too long, Sir."
        )

    except requests.exceptions.ConnectionError:

        return (
            "My local AI is not connected, Sir."
        )

    except Exception as error:

        print(
            "OLLAMA ERROR:",
            repr(error)
        )

        return (
            "I had trouble processing that, Sir."
        )


# ==========================================================
# COMMAND API
# ==========================================================

@app.route(
    "/command",
    methods=["POST"]
)
def command():

    try:

        data = (
            request.get_json(
                silent=True
            )
            or {}
        )

        text = normalize_text(
            data.get(
                "text",
                ""
            )
        )

        if not text:

            return jsonify({
                "response":
                    "I'm listening, Sir."
            })

        print()
        print(
            "WEB:",
            text
        )

        print(
            "NORMALIZED:",
            text.lower()
        )

        # ==================================================
        # ACTIONS FIRST
        # ==================================================

        action = perform_action(
            text
        )

        if action.get("handled"):

            answer = action.get(
                "message",
                "Done, Sir."
            )

            print(
                "ACTION RESULT:",
                answer
            )

            add_to_history(
                text,
                answer
            )

            return jsonify({

                "response":
                    answer,

                "action":
                    action.get(
                        "type",
                        ""
                    ),

                "success":
                    action.get(
                        "success",
                        False
                    ),

                "browser":
                    get_browser_state()
            })
          
                # ==================================================
        # LIVE WEATHER - FAST PATH
        # ==================================================

        if re.search(
            r"\b(weather|temperature|forecast)\b",
            text.lower()
        ):

            weather = get_live_weather()

            if weather:

                print(
                    "LIVE WEATHER:",
                    weather
                )

                add_to_history(
                    text,
                    weather
                )

                return jsonify({
                    "response": weather,
                    "action": "weather",
                    "success": True
                })

        # ==================================================
        # FAST RESPONSE
        # ==================================================

        fast = local_response(
            text
        )

        if fast:

            print(
                "FAST:",
                fast
            )

            add_to_history(
                text,
                fast
            )

            return jsonify({
                "response": fast
            })


        # ==================================================
        # WEB SEARCH
        # ==================================================

 # ==================================================
# LIVE WEATHER - FAST PATH
# ==================================================


        web_results = ""

        if needs_web_search(text):

            query = build_search_query(
                text
            )

            results = tavily_search(
                query
            )

            web_results = format_web_results(
                results
            )


        # ==================================================
        # OLLAMA
        # ==================================================

        answer = ask_ollama(
            text,
            web_results
        )

        print(
            "JARVIS:",
            answer
        )

        return jsonify({
            "response":
                answer
        })

    except Exception as error:

        print(
            "COMMAND ERROR:",
            repr(error)
        )

        return jsonify({
            "response":
                "Something went wrong, Sir."
        }), 500


# ==========================================================
# HOME
# ==========================================================

@app.route("/")
def home():

    return send_from_directory(
        "web",
        "index.html"
    )


# ==========================================================
# STATIC FILES
# ==========================================================

@app.route(
    "/<path:path>"
)
def static_files(path):

    file_path = os.path.join(
        "web",
        path
    )

    if os.path.isfile(file_path):

        return send_from_directory(
            "web",
            path
        )

    return (
        "Not found",
        404
    )


# ==========================================================
# START
# ==========================================================

if __name__ == "__main__":

    print()
    print(
        "=========================================="
    )

    print(
        "              J A R V I S"
    )

    print(
        "=========================================="
    )

    print()

    print(
        "LOCAL AI:",
        MODEL
    )

    print(
        "TAVILY KEY:",
        "LOADED"
        if TAVILY_API_KEY
        else
        "NOT FOUND"
    )

    print(
        "PLAYWRIGHT BROWSER: ON"
    )

    print(
        "GOOGLE SEARCH: ON"
    )

    print(
        "YOUTUBE SEARCH: ON"
    )

    print(
        "YOUTUBE PLAY: ON"
    )

    print(
        "YOUTUBE PAUSE: ON"
    )

    print(
        "YOUTUBE RESUME: ON"
    )

    print(
        "NATURAL COMMANDS: ON"
    )

    print(
        "WEBSITE OPENING: ON"
    )

    print(
        "ACTION RETRY: ON"
    )

    print(
        "CONVERSATION MEMORY: ON"
    )

    print(
        "PERSISTENT MEMORY: ON"
    )

    print()

    print(
        "Open:"
    )

    print(
        "http://127.0.0.1:5000"
    )

    print()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )