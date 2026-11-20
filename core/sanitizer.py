"""Pre-LLM cleaning and prompt-injection detection."""

import re
import unicodedata
import uuid


INJECTION_PATTERNS = (
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s+prompt",
    r"you\s+are\s+now",
    r"<\|im_start\|>",
    r"###\s*SYSTEM",
    r"reveal\s+(owner|private|hidden)\s+(data|notes|info)",
)


def sanitize_untrusted_text(
    raw_text: str, max_chars: int = 8_000
) -> tuple[str, bool, list[str]]:
    """Clean external text and report suspicious prompt-injection signatures."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")

    alerts: list[str] = []
    cleaned = re.sub(r"<!--.*?-->", "", raw_text, flags=re.DOTALL)
    cleaned = "".join(
        character
        for character in cleaned
        if unicodedata.category(character) not in ("Cf", "Cc")
        or character in ("\n", "\t")
    )
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

