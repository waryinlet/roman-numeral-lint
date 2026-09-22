"""Parsing and rendering for strict-form Roman numerals (1..3999).

The grammar enforced here is the conventional "subtractive" form used on
clock faces and in print: at most three repeats of a repeatable symbol,
five-symbols (V, L, D) never repeat, and subtraction is only ever one
symbol below the next power of ten (IV, IX, XL, XC, CD, CM). Anything
outside that is rejected rather than guessed at.

Values above 3999 have no single standard notation; the closest thing is
the vinculum, a bar drawn over a numeral to multiply it by 1000. Since
to_int/to_roman work with plain text rather than typeset numerals, the
vinculum is spelled out with the Unicode combining overline (U+0305)
after each letter it covers, e.g. "V̅" for 5000. This is opt-in
(vinculum=True) since it is a text convention rather than a real ancient
one, and plain strict parsing should keep rejecting anything it doesn't
recognize.
"""

from __future__ import annotations

VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}

_OVERLINE = "̅"

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


def to_int(text: str, *, line: int = 1, source: str | None = None, vinculum: bool = False) -> int:
    """Parse a strict-form Roman numeral and return its integer value.

    Raises RomanNumeralError, whose message points at the exact character
    that made the numeral invalid, on any deviation from the grammar.

    With vinculum=True, a leading run of letters each followed by a
    combining overline (U+0305) is read as a numeral multiplied by 1000,
    optionally followed by an ordinary numeral for the remainder, e.g.
    "V̅XLII" is 5000 + 42. This extends the representable range to
    1..3999999. Without vinculum=True the overline is rejected like any
    other character outside I V X L C D M.
    """
    if text == "":
        raise RomanNumeralError(
            "empty input is not a valid Roman numeral", line=line, column=1, text=text, source=source
        )

    if vinculum:
        return _to_int_vinculum(text, line=line, source=source)

    return _to_int_strict(text, line=line, source=source)


def _to_int_strict(text: str, *, line: int, source: str | None) -> int:
    for index, char in enumerate(text):
        if char not in VALUES:
            if char == _OVERLINE:
                message = (
                    "combining overline must directly follow a Roman numeral letter "
                    "it multiplies by 1000 (vinculum notation, needs --vinculum)"
                )
            elif char.isalpha() and char.upper() in VALUES:
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


def _strip_vinculum_prefix(text: str) -> tuple[str, int]:
    """Split a leading run of (letter, combining overline) pairs off text.

    Returns the run with its overline marks removed, and the index in the
    original text where the run ends (0 if text has no overlined run).
    """
    letters = []
    i = 0
    n = len(text)
    while i + 1 < n and text[i + 1] == _OVERLINE:
        letters.append(text[i])
        i += 2
    return "".join(letters), i


def _to_int_vinculum(text: str, *, line: int, source: str | None) -> int:
    stripped, run_end = _strip_vinculum_prefix(text)

    thousands = 0
    if run_end:
        try:
            thousands = _to_int_strict(stripped, line=line, source=source) * 1000
        except RomanNumeralError as exc:
            # each overlined letter took two characters (letter + overline)
            # in the original text, so its column doubles.
            column = 2 * (exc.column - 1) + 1
            raise RomanNumeralError(exc.message, line=line, column=column, text=text, source=source) from None

    suffix = text[run_end:]
    remainder = 0
    if suffix:
        try:
            remainder = _to_int_strict(suffix, line=line, source=source)
        except RomanNumeralError as exc:
            raise RomanNumeralError(
                exc.message, line=line, column=run_end + exc.column, text=text, source=source
            ) from None

    return thousands + remainder


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


def to_roman(value: int, *, vinculum: bool = False) -> str:
    """Render an integer as a strict-form Roman numeral.

    Plain rendering supports 1..3999. With vinculum=True, values up to
    3999999 are supported: the thousands digits are rendered with a
    combining overline (see to_int), and any remainder below 1000 follows
    as an ordinary numeral, e.g. to_roman(5042, vinculum=True) == "V̅XLII".
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("value must be an integer")

    max_value = 3999999 if vinculum else 3999
    if not 1 <= value <= max_value:
        raise ValueError(f"{value} is out of range; this tool supports 1 to {max_value}")

    if value <= 3999:
        return _render_strict(value)

    thousands, remainder = divmod(value, 1000)
    overlined = "".join(char + _OVERLINE for char in _render_strict(thousands))
    if remainder == 0:
        return overlined
    return overlined + _render_strict(remainder)


def _render_strict(value: int) -> str:
    remaining = value
    parts = []
    for amount, symbol in _NUMERAL_TABLE:
        count, remaining = divmod(remaining, amount)
        parts.append(symbol * count)
    return "".join(parts)
