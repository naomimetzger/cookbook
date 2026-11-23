"""Speech to text for the recipes (free, offline with faster-whisper), in the right language.

- The language is checked first with a multilingual model. English speech uses an English model;
  any other language uses the multilingual model. The language is always printed.
- If the language can't be told for sure, it stops and asks for --language instead of guessing
  (an English model turns other languages into made-up English).
- --hint "bet on yourself" gives expected words or names, so they're heard right.
- No model is ever downloaded without allow_download; the message names the model and its size.
"""
import re

EN_MODELS = ("base.en", "small.en", "tiny.en")       # English only, best first
DETECT_MODELS = ("base", "small", "tiny")             # multilingual, lightest good one first
OTHER_MODELS = ("small", "base", "tiny")              # multilingual, most accurate first
SIZES = {"tiny": 75, "tiny.en": 75, "base": 145, "base.en": 145, "small": 465, "small.en": 465}
NAMES = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese",
         "nl": "Dutch", "pl": "Polish", "tr": "Turkish", "ru": "Russian", "uk": "Ukrainian", "ar": "Arabic",
         "hi": "Hindi", "zh": "Chinese", "ja": "Japanese", "ko": "Korean", "sv": "Swedish", "da": "Danish",
         "no": "Norwegian", "nn": "Norwegian Nynorsk", "fi": "Finnish", "el": "Greek", "he": "Hebrew",
         "cy": "Welsh", "ga": "Irish", "la": "Latin", "ca": "Catalan", "ro": "Romanian", "cs": "Czech",
         "hu": "Hungarian", "id": "Indonesian", "ms": "Malay", "vi": "Vietnamese", "th": "Thai",
         "yo": "Yoruba", "sw": "Swahili", "tl": "Tagalog", "ur": "Urdu", "bn": "Bengali", "fa": "Persian"}
# the most common English words: real English speech is full of them, made-up English isn't
COMMON_EN = set("""a about after again all also always am an and any are around as at back be because been
before being but by can can't come could day did didn't do does don't down even every feel first for from get
go going good got had has have he her here him his how i i'm if in into is isn't it it's just know last like
little look lot make many me more most much my need never new no not now of off on one only or other our out
over people really right said say see she should so some something still take than that that's the their them
then there these they thing things think this those time to too two up us very want was way we well were what
when where which who why will with work would year years yes you you're your yourself""".split())


def name(code):
    return NAMES.get(code, code)


def _load(names, allow_download):
    """The first of these models that's on the computer; else download the first (only if allowed)."""
    from faster_whisper import WhisperModel
    for n in names:
        try:
            return WhisperModel(n, device="cpu", compute_type="int8", local_files_only=True), n
        except Exception:
            continue
    if allow_download:
        print(f"Downloading the '{names[0]}' speech model once (about {SIZES.get(names[0], '?')} MB)...")
        return WhisperModel(names[0], device="cpu", compute_type="int8"), names[0]
    return None, None


def _need(n, why):
    return SystemExit(f"{why} Ask the user, then rerun with --allow-download "
                      f"(downloads the '{n}' speech model once, about {SIZES[n]} MB).")


def english_share(words):
    keys = [re.sub(r"[^a-z']", "", w["word"].lower()) for w in words]
    keys = [k for k in keys if k]
    return sum(k in COMMON_EN for k in keys) / len(keys) if keys else 1.0


class Speech:
    """Speech(wav, language=None, hint=None, allow_download=False); then .words(path, vad) any number of times."""

    def __init__(self, wav, language=None, hint=None, allow_download=False):
        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            import sys
            raise SystemExit("Speech-to-text isn't installed. Ask the user, then run: "
                             f"{sys.executable} -m pip install faster-whisper")
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        self.hint = (hint or "").strip() or None
        self.done = {}
        how = "you chose"
        lang = (language or "").strip().lower() or None
        if lang and lang not in _LANGUAGE_CODES:
            raise SystemExit(f"'{language}' isn't a language code the speech model knows. Use a short code like "
                             "en, es, fr, de, pt, it.")
        if lang is None:
            det, dname = _load(DETECT_MODELS, allow_download)
            if det is None:
                raise _need("base", "No multilingual speech model on this computer, so the language can't be "
                                    "checked. (If the speech is English, --language en works with an English model.)")
            from faster_whisper import decode_audio
            code, prob, ranked = det.detect_language(decode_audio(wav), vad_filter=True)
            heard = ", ".join(f"{name(c)} {p:.0%}" for c, p in ranked[:3])
            if code == "en" and prob >= 0.9:
                lang, how = "en", f"detected, {prob:.0%} sure"
            elif code != "en" and prob >= 0.5:
                lang, how = code, f"detected, {prob:.0%} sure"
            else:
                # unsure: listen as English and see if it really is English, or stop and ask
                model, mname = _load(EN_MODELS, False)
                model, mname = (model, mname) if model else (det, dname)
                self.model, self.model_name, self.language = model, mname, "en"
                trial = self.words(wav, True)
                if english_share(trial) < 0.4:
                    raise SystemExit(f"Can't tell which language this is (heard: {heard}), and it doesn't sound like "
                                     "English. Ask the user which language is spoken, then rerun with --language CODE "
                                     "(e.g. es for Spanish, fr for French, pt for Portuguese).")
                lang, how = "en", f"checked by listening (first guess: {heard})"
            del det  # free its memory before the next model loads (unless it's the one in use)
        self.language = lang
        if getattr(self, "model", None) is None:
            # English: an English model, else any multilingual one. Other languages: multilingual only.
            first = EN_MODELS + OTHER_MODELS if lang == "en" else OTHER_MODELS
            self.model, self.model_name = _load(first, False)
            if self.model is None:
                n = "base.en" if lang == "en" else "base"
                if not allow_download:
                    raise _need(n, "No speech model for " + name(lang) + " on this computer yet.")
                self.model, self.model_name = _load((n,), True)
        print(f"Language: {name(lang)} ({lang}, {how}). Speech model: {self.model_name}"
              + (f'. Hint: "{self.hint}"' if self.hint else ""))

    def words(self, path, vad=True):
        """[{word, start, end}] in seconds from the start of this audio file."""
        key = (path, vad)
        if key not in self.done:
            segs, _ = self.model.transcribe(path, language=self.language, word_timestamps=True, vad_filter=vad,
                                            initial_prompt=self.hint)
            self.done[key] = [{"word": w.word.strip(), "start": w.start, "end": w.end}
                              for s in segs for w in (s.words or []) if w.word.strip()]
        return [dict(w) for w in self.done[key]]
