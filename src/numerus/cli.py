"""Command-line entry point for numerus."""

from __future__ import annotations

import argparse
import json
import sys

from .parser import RomanNumeralError, to_int, to_roman


def _read_lines(path):
    if path is None or path == "-":
        for lineno, raw in enumerate(sys.stdin, start=1):
            yield lineno, raw.rstrip("\n"), "<stdin>"
    else:
        with open(path, "r", encoding="utf-8") as handle:
            for lineno, raw in enumerate(handle, start=1):
                yield lineno, raw.rstrip("\n"), path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="numerus",
        description="Convert between Roman numerals and integers, one value per line.",
    )
    parser.add_argument(
        "values", nargs="*",
        help="values to convert; reads stdin if omitted and --file is not given",
    )
    parser.add_argument(
        "-e", "--encode", action="store_true",
        help="convert integers to Roman numerals instead of the default, Roman numerals to integers",
    )
    parser.add_argument(
        "-f", "--file", metavar="PATH",
        help="read values from PATH instead of the command line or stdin",
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="suppress output for successful conversions; only report errors",
    )
    parser.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="output format for results and errors (default: text)",
    )
    return parser


def _convert_line(text: str, *, encode: bool, line: int, source: str) -> str:
    if encode:
        try:
            number = int(text)
        except ValueError:
            raise RomanNumeralError(
                f"'{text}' is not an integer", line=line, column=1, text=text, source=source
            ) from None
        try:
            return to_roman(number)
        except ValueError as exc:
            raise RomanNumeralError(str(exc), line=line, column=1, text=text, source=source) from None
    return str(to_int(text, line=line, source=source))


def _emit_success(result: str, *, source: str, line: int, text: str, fmt: str, quiet: bool) -> None:
    if quiet:
        return
    if fmt == "json":
        print(json.dumps({"source": source, "line": line, "input": text, "ok": True, "output": result}))
    else:
        print(result)


def _emit_error(exc: RomanNumeralError, *, fmt: str) -> None:
    # JSON errors go to stdout, alongside successes, so a consumer gets one
    # complete stream of results; text errors go to stderr, compiler-style.
    if fmt == "json":
        print(json.dumps({
            "source": exc.source,
            "line": exc.line,
            "input": exc.text,
            "ok": False,
            "error": {"message": exc.message, "column": exc.column},
        }))
    else:
        print(exc.format(), file=sys.stderr)


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    exit_code = 0

    if args.values and not args.file:
        sources = [(i + 1, value, "<argv>") for i, value in enumerate(args.values)]
    else:
        sources = list(_read_lines(args.file))

    for lineno, text, source in sources:
        stripped = text.strip()
        if not stripped:
            continue
        try:
            result = _convert_line(stripped, encode=args.encode, line=lineno, source=source)
        except RomanNumeralError as exc:
            exit_code = 1
            _emit_error(exc, fmt=args.format)
            continue
        _emit_success(result, source=source, line=lineno, text=stripped, fmt=args.format, quiet=args.quiet)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
