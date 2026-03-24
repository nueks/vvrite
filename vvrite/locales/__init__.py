"""Internationalization (i18n) core for vvrite."""

import importlib

from Foundation import NSLocale

# (locale_code, native_name) — 14 languages supported by Qwen3-ASR
SUPPORTED_LANGUAGES = [
    ("en", "English"),
    ("ko", "\ud55c\uad6d\uc5b4"),
    ("ja", "\u65e5\u672c\u8a9e"),
    ("zh-Hans", "\u7b80\u4f53\u4e2d\u6587"),
    ("zh-Hant", "\u7e41\u9ad4\u4e2d\u6587"),
    ("es", "Espa\u00f1ol"),
    ("fr", "Fran\u00e7ais"),
    ("de", "Deutsch"),
    ("pt", "Portugu\u00eas"),
    ("ru", "\u0420\u0443\u0441\u0441\u043a\u0438\u0439"),
    ("ar", "\u0627\u0644\u0639\u0631\u0628\u064a\u0629"),
    ("hi", "\u0939\u093f\u0928\u094d\u0926\u0940"),
    ("tr", "T\u00fcrk\u00e7e"),
    ("it", "Italiano"),
]

# Map locale base codes to ASR language names used by the model
ASR_LANGUAGE_MAP = {
    "en": "English",
    "ko": "Korean",
    "ja": "Japanese",
    "zh-Hans": "Chinese",
    "zh-Hant": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "it": "Italian",
}

_SUPPORTED_CODES = {code for code, _ in SUPPORTED_LANGUAGES}

_current_locale = "en"
_strings_cache: dict[str, dict] = {}


def set_locale(code: str) -> None:
    """Set the active locale code."""
    global _current_locale
    _current_locale = code


def get_locale() -> str:
    """Return the active locale code."""
    return _current_locale


def resolve_system_locale() -> str:
    """Detect the system locale and return the best matching supported code.

    Uses NSLocale.preferredLanguages() from Foundation.
    Match strategy: exact match first, then base language, fallback to 'en'.
    """
    preferred = NSLocale.preferredLanguages()
    if not preferred:
        return "en"

    for lang in preferred:
        lang = str(lang)
        # Exact match (e.g. "zh-Hans")
        if lang in _SUPPORTED_CODES:
            return lang
        # Normalise Apple-style separators: "zh-Hans-US" -> try "zh-Hans"
        parts = lang.split("-")
        if len(parts) >= 2:
            candidate = f"{parts[0]}-{parts[1]}"
            if candidate in _SUPPORTED_CODES:
                return candidate
        # Base language match (e.g. "ko-KR" -> "ko")
        base = parts[0]
        if base in _SUPPORTED_CODES:
            return base

    return "en"


def t(key: str, **kwargs) -> str:
    """Translate a dot-separated key, with optional format parameters.

    Fallback chain: current locale -> English -> return key itself.
    """
    # Try current locale first
    result = _resolve(key, _current_locale)
    # Fallback to English
    if result is None and _current_locale != "en":
        result = _resolve(key, "en")
    # Missing key: return key itself
    if result is None:
        return key
    if kwargs:
        try:
            return result.format(**kwargs)
        except (KeyError, IndexError):
            return result
    return result


def _resolve(key: str, locale_code: str) -> str | None:
    """Look up a dot-separated key in the given locale's strings."""
    strings = _load_strings(locale_code)
    if strings is None:
        return None
    parts = key.split(".")
    return _lookup(parts, strings)


def _load_strings(locale_code: str) -> dict | None:
    """Import vvrite.locales.{code} module and return its ``strings`` dict.

    Results are cached. Returns None if the module cannot be loaded.
    """
    if locale_code in _strings_cache:
        return _strings_cache[locale_code]

    module_name = f"vvrite.locales.{locale_code.replace('-', '_')}"
    try:
        mod = importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError):
        _strings_cache[locale_code] = None
        return None

    strings = getattr(mod, "strings", None)
    _strings_cache[locale_code] = strings
    return strings


def _lookup(parts: list[str], strings: dict) -> str | None:
    """Traverse a nested dict by key parts. Returns None if not found."""
    current = strings
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    if isinstance(current, str):
        return current
    return None
