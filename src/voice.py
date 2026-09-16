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

def listen_to_microphone(timeout=10, phrase_time_limit=15, status_callback=None, device_index=None):
    """
    Listens to the microphone and transcribes spoken audio to text.
    Parameters:
        timeout: Seconds to wait for speech to begin (default: 10s).
        phrase_time_limit: Maximum length of spoken phrase (default: 15s).
        status_callback: Optional callable(str) for real-time UI/CLI status updates.
        device_index: Optional device index for SpeechRecognition Microphone.
    Returns:
        (text, None) on success
        (None, error_message) on failure
    """
    if not STT_AVAILABLE:
        return None, "SpeechRecognition library is not installed."

    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold = 1.0  # Allow 1s pause between words

    try:
        if status_callback:
            status_callback("Calibrating microphone...")

        with sr.Microphone(device_index=device_index) as source:
            # Calibrate ambient noise quickly (0.4s) to avoid clipping user's speech
            recognizer.adjust_for_ambient_noise(source, duration=0.4)

            # Clamp threshold to prevent being too deaf (>800) or hypersensitive (<150)
            if recognizer.energy_threshold < 150:
                recognizer.energy_threshold = 150
            elif recognizer.energy_threshold > 800:
                recognizer.energy_threshold = 800

            if status_callback:
                status_callback(f"🎤 Listening... Speak now (up to {timeout}s)")
            print(f"\n🎤 Listening... Speak now ({timeout}s timeout)")

            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

        if status_callback:
            status_callback("Transcribing audio...")
        print("Transcribing audio...")

        transcribed_text = recognizer.recognize_google(audio)
        return transcribed_text, None

    except sr.WaitTimeoutError:
        return None, f"No speech detected within {timeout} seconds. Click 🎤 Mic again and speak clearly."
    except sr.UnknownValueError:
        return None, "Could not understand audio. Please speak a little louder and closer to the mic."
    except sr.RequestError as e:
        return None, f"Recognition service error (check internet connection): {e}"
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
            text, err = listen_to_microphone(timeout=10, phrase_time_limit=15)
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


def test_microphone_diagnostics():
    """
    Diagnostic tool to inspect audio hardware, volume levels, and test recognition.
    """
    print("========================================")
    print("    JARVIS-lite Microphone Diagnostics")
    print("========================================")

    if not STT_AVAILABLE:
        print("[-] SpeechRecognition is not installed.")
        return

    mics = sr.Microphone.list_microphone_names()
    print(f"[+] Found {len(mics)} audio device(s):")
    for i, name in enumerate(mics[:6]):
        print(f"    - Index {i}: {name}")
    if len(mics) > 6:
        print(f"    ... and {len(mics) - 6} more.")

    print("\n[+] Testing default microphone recording for 3 seconds...")
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            print("    Calibrating ambient noise...")
            r.adjust_for_ambient_noise(source, duration=0.5)
            print(f"    Calibrated energy threshold: {r.energy_threshold:.1f}")
            print("    🎤 Listening for 5 seconds... Speak something now!")
            audio = r.listen(source, timeout=5, phrase_time_limit=8)

        print("    Transcribing with Google Speech Recognition...")
        text = r.recognize_google(audio)
        print(f"    ✓ Successfully recognized: \"{text}\"")
    except sr.WaitTimeoutError:
        print("    [-] Timed out waiting for speech. Check if microphone is unmuted in Windows Settings.")
    except sr.UnknownValueError:
        print("    [!] Audio was recorded, but words were not clearly distinguishable.")
    except Exception as e:
        print(f"    [-] Diagnostic error: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--cli":
            voice_talk_session()
        elif sys.argv[1] == "--test-mic":
            test_microphone_diagnostics()
    else:
        # Self-test TTS
        print("Testing TTS output...")
        speak("JARVIS voice module initialized.", async_mode=False)
        print("✓ Voice module self-test complete.")

