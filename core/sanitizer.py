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


def _preserve_comment_lines(match: re.Match[str]) -> str:
    """Remove an HTML comment without changing subsequent source line numbers."""
    return "\n" * match.group(0).count("\n")


def sanitize_untrusted_text(
    raw_text: str, max_chars: int = 8_000
) -> tuple[str, bool, list[str]]:
    """Clean external text and report suspicious patterns at 1-based source lines."""
    if max_chars < 1:
        raise ValueError("max_chars must be positive")

    alerts: list[str] = []
    cleaned = re.sub(
        r"<!--.*?-->", _preserve_comment_lines, raw_text, flags=re.DOTALL
    )
    cleaned = "".join(
        character
        for character in cleaned
        if unicodedata.category(character) not in ("Cf", "Cc")
        or character in ("\n", "\t")
    )
    if len(cleaned) > max_chars:
        alerts.append(f"Input was truncated to {max_chars:,} characters.")
    cleaned = cleaned[:max_chars]

    for pattern in INJECTION_PATTERNS:
        for match in re.finditer(pattern, cleaned, flags=re.IGNORECASE):
            start_line = cleaned.count("\n", 0, match.start()) + 1
            end_line = cleaned.count("\n", 0, match.end()) + 1
            location = (
                f"line {start_line}"
                if start_line == end_line
                else f"lines {start_line}-{end_line}"
            )
            alerts.append(
                f"Blocked suspicious pattern at {location} matching: `{pattern}`"
            )

    cleaned = cleaned.strip()
    return cleaned, any(alert.startswith("Blocked") for alert in alerts), alerts


def spotlight_untrusted(text: str) -> str:
    """Wrap external text in a randomized boundary for privilege separation."""
    tag = f"untrusted_data_{uuid.uuid4().hex[:8]}"
    return f"<{tag}>\n{text}\n</{tag}>"
