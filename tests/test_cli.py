import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

from numerus.cli import main


class DecodeArgvTest(unittest.TestCase):
    def test_single_value(self):
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = main(["MCMXCIV"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(out.getvalue(), "1994\n")

    def test_multiple_values(self):
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = main(["MCMXCIV", "XLII"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(out.getvalue(), "1994\n42\n")


class EncodeArgvTest(unittest.TestCase):
    def test_encode_flag(self):
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = main(["-e", "1994", "42"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(out.getvalue(), "MCMXCIV\nXLII\n")

    def test_encode_rejects_non_integer(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = main(["-e", "abc"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("is not an integer", err.getvalue())

    def test_encode_rejects_out_of_range(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = main(["-e", "4000"])
        self.assertEqual(exit_code, 1)
        self.assertIn("out of range", err.getvalue())


class ErrorReportingTest(unittest.TestCase):
    def test_invalid_value_reported_and_exit_code_nonzero(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = main(["IIII"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("<argv>:1:4: error:", err.getvalue())

    def test_valid_and_invalid_values_both_processed(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = main(["XLII", "IIII", "IX"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(out.getvalue(), "42\n9\n")
        self.assertIn("error:", err.getvalue())


class StdinTest(unittest.TestCase):
    def test_reads_stdin_when_no_values_given(self):
        out = io.StringIO()
        fake_stdin = io.StringIO("MCMXCIV\nXLII\n")
        with mock.patch("sys.stdin", fake_stdin), redirect_stdout(out):
            exit_code = main([])
        self.assertEqual(exit_code, 0)
        self.assertEqual(out.getvalue(), "1994\n42\n")

    def test_blank_lines_are_skipped(self):
        out = io.StringIO()
        fake_stdin = io.StringIO("MCMXCIV\n\n   \nXLII\n")
        with mock.patch("sys.stdin", fake_stdin), redirect_stdout(out):
            exit_code = main([])
        self.assertEqual(exit_code, 0)
        self.assertEqual(out.getvalue(), "1994\n42\n")

    def test_stdin_error_reports_stdin_as_source(self):
        out, err = io.StringIO(), io.StringIO()
        fake_stdin = io.StringIO("IL\n")
        with mock.patch("sys.stdin", fake_stdin), redirect_stdout(out), redirect_stderr(err):
            exit_code = main([])
        self.assertEqual(exit_code, 1)
        self.assertIn("<stdin>:1:2: error:", err.getvalue())


class FileTest(unittest.TestCase):
    def test_reads_values_from_file(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as handle:
            handle.write("MCMXCIV\nIIII\nxiv\n")
            path = handle.name
        try:
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                exit_code = main(["-f", path])
            self.assertEqual(exit_code, 1)
            self.assertEqual(out.getvalue(), "1994\n")
            self.assertIn(f"{path}:2:4: error:", err.getvalue())
            self.assertIn(f"{path}:3:1: error:", err.getvalue())
        finally:
            os.unlink(path)


class QuietFlagTest(unittest.TestCase):
    def test_quiet_suppresses_successful_output(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = main(["--quiet", "MCMXCIV", "IIII"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("error:", err.getvalue())

    def test_quiet_still_exits_zero_when_all_valid(self):
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = main(["--quiet", "MCMXCIV"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(out.getvalue(), "")


class JsonFormatTest(unittest.TestCase):
    def test_json_success(self):
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = main(["--format", "json", "MCMXCIV"])
        self.assertEqual(exit_code, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload, {
            "source": "<argv>", "line": 1, "input": "MCMXCIV", "ok": True, "output": "1994",
        })

    def test_json_error_goes_to_stdout_not_stderr(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = main(["--format", "json", "IIII"])
        self.assertEqual(exit_code, 1)
        self.assertEqual(err.getvalue(), "")
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["column"], 4)
        self.assertIn("repeated 4 times", payload["error"]["message"])

    def test_json_and_quiet_only_emits_errors(self):
        out = io.StringIO()
        with redirect_stdout(out):
            exit_code = main(["--format", "json", "--quiet", "MCMXCIV", "IIII"])
        self.assertEqual(exit_code, 1)
        lines = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual(len(lines), 1)
        self.assertFalse(lines[0]["ok"])


if __name__ == "__main__":
    unittest.main()
