# numerus

A command-line tool that converts between Roman numerals and integers,
and refuses to guess when the input is wrong.

Most Roman numeral code you find treats parsing as "sum the values, maybe
subtract sometimes." That accepts nonsense like `IIII`, `VV`, `IM`, or
lowercase `xiv` as if they meant something. numerus enforces the actual
grammar (at most three repeated symbols, five-symbols never repeat,
subtraction only ever one symbol below the next power of ten) and when
a numeral breaks that grammar, it tells you exactly where and why, the
way a compiler points at a syntax error rather than just saying "no."

## Install

No dependencies beyond the Python standard library. From a checkout:

```
python -m pip install --user .
```

That installs a `numerus` command. You can also run it in place with
`python -m numerus.cli`, or import `numerus` as a library.

## Usage

Convert Roman numerals to integers, one per argument:

```
$ numerus MCMXCIV XLII
1994
42
```

Convert integers to Roman numerals with `-e`/`--encode`:

```
$ numerus -e 1994 42
MCMXCIV
XLII
```

Read from a file, one value per line, with `-f`/`--file`:

```
$ cat numerals.txt
MCMXCIV
IIII
xiv
$ numerus -f numerals.txt
1994
numerals.txt:2:1: error: 'I' repeated 4 times in a row; at most 3 are allowed
    IIII
    ^
numerals.txt:3:1: error: 'x' is lowercase; Roman numerals use only uppercase I V X L C D M
    xiv
    ^
```

Values with no source file read from stdin the same way:

```
$ echo "IL" | numerus
<stdin>:1:2: error: unexpected 'L' here; symbol values must appear in descending order (thousands, then hundreds, then tens, then units)
    IL
     ^
```

Lines that fail to convert are reported to stderr and skipped; valid
lines still print their results, and the process exits non-zero if any
line failed.

Use `-q`/`--quiet` to check a file without printing every successful
conversion, useful when you only care whether something is wrong:

```
$ numerus -q -f numerals.txt
numerals.txt:2:1: error: 'I' repeated 4 times in a row; at most 3 are allowed
    IIII
    ^
numerals.txt:3:1: error: 'x' is lowercase; Roman numerals use only uppercase I V X L C D M
    xiv
    ^
```

Use `--format json` for machine-readable output, one JSON object per
input line on stdout, whether it succeeded or failed:

```
$ numerus --format json MCMXCIV IIII
{"source": "<argv>", "line": 1, "input": "MCMXCIV", "ok": true, "output": "1994"}
{"source": "<argv>", "line": 2, "input": "IIII", "ok": false, "error": {"message": "'I' repeated 4 times in a row; at most 3 are allowed", "column": 4}}
```

`--quiet` and `--format json` combine: only failed entries are printed.

## Library use

```python
from numerus import to_int, to_roman, RomanNumeralError

to_int("MCMXCIV")   # 1994
to_roman(1994)       # "MCMXCIV"

try:
    to_int("IIII")
except RomanNumeralError as exc:
    print(exc.line, exc.column, exc.message)
```

## Range

Supports 1 to 3999 by default. Roman numerals have no single standard
notation above that; the closest is the vinculum, a bar drawn over a
numeral to multiply it by 1000.

## Vinculum notation

Pass `--vinculum` to opt into vinculum notation for values from 4000 up
to 3999999. Since this tool works with plain text rather than typeset
numerals, the bar is spelled out as a combining overline (Unicode
U+0305) after each letter it covers:

```
$ numerus --vinculum V̄XLII
5042
$ numerus --vinculum -e 5042
V̄XLII
```

Without `--vinculum`, the overline character is rejected like any other
symbol outside I V X L C D M, so plain conversions are unaffected.

## License

MIT, see LICENSE.
