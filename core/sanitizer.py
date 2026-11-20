"""Pre-LLM cleaning and prompt-injection detection."""

import html
import re
import unicodedata
import uuid


INJECTION_PATTERNS = (
    r"\bignore\W*(?:all\W*)?(?:previous|prior)\W*(?:instructions?|prompts?)\b",
    r"\b(?:show|reveal|print|repeat|expose)\W*(?:the\W*)?(?:system|developer)\W*(?:prompt|instructions?)\b",
    r"\bsystem\W*prompt\b",
    r"\byou\W+are\W+now\b",
    r"<\|im_start\|>",
    r"###\W*system\b",
    r"\breveal\W+(?:owner|private|hidden)\W+(?:data|notes|info(?:rmation)?)\b",
)


def sanitize_untrusted_text(
    raw_text: str, max_chars: int = 8_000
) -> tuple[str, bool, list[str]]:
    """Clean external text and report suspicious prompt-injection signatures."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")

    alerts: list[str] = []
    cleaned = html.unescape(html.unescape(str(raw_text)))
    cleaned = unicodedata.normalize("NFKC", cleaned)
    cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
    cleaned = "".join(
        character
        if unicodedata.category(character) not in ("Cf", "Cc")
        or character in ("\n", "\t")
        else " "
        for character in cleaned
    )
    cleaned = re.sub(r"[ \f\v]+", " ", cleaned)
    if len(cleaned) > max_chars:
        alerts.append(f"Input was truncated to {max_chars:,} characters.")
    cleaned = cleaned[:max_chars].strip()

    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, cleaned, flags=re.IGNORECASE):
            alerts.append(f"Blocked suspicious pattern matching: `{pattern}`")

    return cleaned, any("Blocked" in alert for alert in alerts), alerts


def spotlight_untrusted(text: str) -> str:
    """Wrap external text in a randomized boundary for privilege separation."""
    tag = f"untrusted_data_{uuid.uuid4().hex[:8]}"
    return f"<{tag}>\n{text}\n</{tag}>"

