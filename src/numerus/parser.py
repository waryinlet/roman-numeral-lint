"""Parsing and rendering for strict-form Roman numerals (1..3999).

The grammar enforced here is the conventional "subtractive" form used on
clock faces and in print: at most three repeats of a repeatable symbol,
five-symbols (V, L, D) never repeat, and subtraction is only ever one
symbol below the next power of ten (IV, IX, XL, XC, CD, CM). Anything
outside that is rejected rather than guessed at.
"""

from __future__ import annotations

VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

# (unit symbol, five symbol or None, ten symbol or None, place value)
# M has no five/ten symbol above it since 4000 and up aren't representable.
_GROUPS = [
    ("M", None, None, 1000),
    ("C", "D", "M", 100),
    ("X", "L", "C", 10),
    ("I", "V", "X", 1),
]

_NUMERAL_TABLE = [
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"),
    (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
    (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
]


class RomanNumeralError(ValueError):
    """A syntax error in a Roman numeral, with an exact source position."""

    def __init__(self, message: str, *, line: int, column: int, text: str, source: str | None = None):
        self.message = message
        self.line = line
        self.column = column
        self.text = text
        self.source = source
        super().__init__(self.format())

    def format(self) -> str:
        prefix = f"{self.source}:" if self.source else ""
        header = f"{prefix}{self.line}:{self.column}: error: {self.message}"
        pointer = " " * (self.column - 1) + "^"
        return f"{header}\n    {self.text}\n    {pointer}"


def to_int(text: str, *, line: int = 1, source: str | None = None) -> int:
    """Parse a strict-form Roman numeral and return its integer value.

    Raises RomanNumeralError, whose message points at the exact character
    that made the numeral invalid, on any deviation from the grammar.
    """
    if text == "":
        raise RomanNumeralError(
            "empty input is not a valid Roman numeral", line=line, column=1, text=text, source=source
        )

    for index, char in enumerate(text):
        if char not in VALUES:
            if char.isalpha() and char.upper() in VALUES:
                message = f"'{char}' is lowercase; Roman numerals use only uppercase I V X L C D M"
            else:
                message = f"'{char}' is not a Roman numeral character (allowed: I V X L C D M)"
            raise RomanNumeralError(message, line=line, column=index + 1, text=text, source=source)

    pos = 0
    total = 0
    for unit, five, ten, place in _GROUPS:
        pos, value = _parse_group(text, pos, unit, five, ten, place, line=line, source=source)
        total += value

    if pos != len(text):
        raise RomanNumeralError(
            f"unexpected '{text[pos]}' here; symbol values must appear in descending "
            "order (thousands, then hundreds, then tens, then units)",
            line=line, column=pos + 1, text=text, source=source,
        )

    return total


def _parse_group(text, pos, unit, five, ten, place, *, line, source):
    n = len(text)

    if ten and pos + 1 < n and text[pos] == unit and text[pos + 1] == ten:
        return pos + 2, 9 * place

    if five and pos + 1 < n and text[pos] == unit and text[pos + 1] == five:
        return pos + 2, 4 * place

    value = 0
    p = pos

    if five and p < n and text[p] == five:
        value += 5 * place
        p += 1
        if p < n and text[p] == five:
            raise RomanNumeralError(
                f"'{five}' cannot repeat; it may appear at most once per numeral",
                line=line, column=p + 1, text=text, source=source,
            )

    run_start = p
    while p < n and text[p] == unit:
        p += 1
    run_length = p - run_start
    if run_length > 3:
        raise RomanNumeralError(
            f"'{unit}' repeated {run_length} times in a row; at most 3 are allowed",
            line=line, column=run_start + 4, text=text, source=source,
        )
    value += run_length * place

    return p, value


def to_roman(value: int) -> str:
    """Render an integer in the range 1..3999 as a strict-form Roman numeral."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("value must be an integer")
    if not 1 <= value <= 3999:
        raise ValueError(f"{value} is out of range; this tool supports 1 to 3999")

    remaining = value
    parts = []
    for amount, symbol in _NUMERAL_TABLE:
        count, remaining = divmod(remaining, amount)
        parts.append(symbol * count)
    return "".join(parts)
