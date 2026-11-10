"""Speech in (microphone -> text) and speech out (text -> speaker)."""
import threading

YES_WORDS = ("yes", "yeah", "yep", "confirm", "go ahead", "do it", "proceed", "sure", "affirmative")


class Voice:
    def __init__(self):
        import pyttsx3
        import speech_recognition as sr

        self.sr = sr
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = 0.8
        self.mic = sr.Microphone()
        with self.mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
        self._tts = pyttsx3.init()
        self._tts.setProperty("rate", 185)
        self._lock = threading.Lock()

    def speak(self, text: str) -> None:
        print(f"JARVIS: {text}")
        with self._lock:
            self._tts.say(text)
            self._tts.runAndWait()

    def listen(self, timeout: int = 6, phrase_limit: int = 15) -> str:
        """Block until speech is heard; return the transcript or '' on silence / failure."""
        with self.mic as source:
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            except self.sr.WaitTimeoutError:
                return ""
        try:
            text = self.recognizer.recognize_google(audio)
            print(f"YOU: {text}")
            return text
        except self.sr.UnknownValueError:
            return ""
        except self.sr.RequestError as exc:
            print(f"[speech recognition unavailable: {exc}]")
            return ""

    def confirm(self, summary: str) -> bool:
        self.speak("I need your confirmation. " + summary[:200] + ". Shall I proceed?")
        answer = self.listen(timeout=8, phrase_limit=5).lower()
        return any(w in answer for w in YES_WORDS)
