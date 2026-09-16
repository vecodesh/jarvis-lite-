"""
JARVIS-lite: Voice Input/Output Module (Phase 5 - Feature 3c)

Provides optional:
1. Text-to-Speech (TTS) using pyttsx3 (offline, Windows SAPI5 support).
2. Speech-to-Text (STT) using SpeechRecognition (Microphone and Audio File).

Operates as an alternate input/output modality alongside typed text,
keeping the frozen V1 core isolated and untouched.
"""

import sys
import threading
from pathlib import Path

# Ensure UTF-8 output encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Optional library imports with safe fallbacks
try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    STT_AVAILABLE = False


# --------------------------------------------------
# Text-To-Speech (TTS) Engine
# --------------------------------------------------

_tts_lock = threading.Lock()


def speak(text, async_mode=True):
    """
    Speaks the given text using pyttsx3 (offline TTS).
    If async_mode is True, runs in a background daemon thread to avoid blocking.
    """
    if not text:
        return

    if not TTS_AVAILABLE:
        print(f"[TTS Not Installed] {text}")
        return

    def _run_tts():
        with _tts_lock:
            try:
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)     # Natural speaking speed
                engine.setProperty("volume", 0.9)   # Volume level
                engine.say(text)
                engine.runAndWait()
            except Exception as e:
                print(f"[TTS Error] {e}")

    if async_mode:
        threading.Thread(target=_run_tts, daemon=True).start()
    else:
        _run_tts()


# --------------------------------------------------
# Speech-To-Text (STT) Engine
# --------------------------------------------------

def listen_to_microphone(timeout=5, phrase_time_limit=8):
    """
    Listens to the default microphone and transcribes spoken audio to text.
    Returns:
        (text, None) on success
        (None, error_message) on failure
    """
    if not STT_AVAILABLE:
        return None, "SpeechRecognition library is not installed."

    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("\n🎤 Listening... (speak now)")
            recognizer.adjust_for_ambient_noise(source, duration=0.6)
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

        print("Transcribing audio...")
        transcribed_text = recognizer.recognize_google(audio)
        return transcribed_text, None

    except sr.WaitTimeoutError:
        return None, "No speech detected before timeout."
    except sr.UnknownValueError:
        return None, "Could not understand audio."
    except sr.RequestError as e:
        return None, f"Recognition service error: {e}"
    except Exception as e:
        return None, f"Microphone error: {e}"


def transcribe_audio_file(audio_file_path):
    """
    Transcribes a pre-recorded audio file (WAV/AIFF/FLAC).
    Useful for scripted testing, recorded voice notes, and automated verification.
    """
    if not STT_AVAILABLE:
        return None, "SpeechRecognition library is not installed."

    path = Path(audio_file_path)
    if not path.exists():
        return None, f"Audio file not found: {audio_file_path}"

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(str(path)) as source:
            audio = recognizer.record(source)
        transcribed_text = recognizer.recognize_google(audio)
        return transcribed_text, None
    except Exception as e:
        return None, f"Error transcribing file: {e}"


# --------------------------------------------------
# Standalone Voice Mode for CLI
# --------------------------------------------------

def voice_talk_session():
    """
    Interactive hands-free voice loop for CLI users.
    Calls frozen assistant.process_input with spoken text and speaks responses.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(BASE_DIR / "src"))
    from assistant import process_input

    print("========================================")
    print("      JARVIS-lite Voice Mode")
    print("========================================")
    print("Speak your study updates or tasks.")
    print("Press Ctrl+C to exit voice mode.\n")

    speak("JARVIS voice assistant ready. What are you working on today?")

    while True:
        try:
            text, err = listen_to_microphone(timeout=6, phrase_time_limit=10)
            if err:
                print(f"[{err}]")
                continue

            print(f"You said: \"{text}\"")
            process_input(text)
            speak("Got it. I updated your memory.")

        except KeyboardInterrupt:
            print("\nExiting voice mode.")
            speak("Goodbye!")
            break


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        voice_talk_session()
    else:
        # Self-test TTS
        print("Testing TTS output...")
        speak("JARVIS voice module initialized.", async_mode=False)
        print("✓ Voice module self-test complete.")
