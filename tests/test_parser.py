import unittest

from numerus.parser import RomanNumeralError, to_int, to_roman


class ToIntValidTest(unittest.TestCase):
    def test_simple_additive(self):
        self.assertEqual(to_int("I"), 1)
        self.assertEqual(to_int("III"), 3)
        self.assertEqual(to_int("VIII"), 8)
        self.assertEqual(to_int("XXX"), 30)

    def test_subtractive_pairs(self):
        cases = {
            "IV": 4, "IX": 9, "XL": 40, "XC": 90, "CD": 400, "CM": 900,
        }
        for numeral, value in cases.items():
            self.assertEqual(to_int(numeral), value)

    def test_mixed(self):
        self.assertEqual(to_int("MCMXCIV"), 1994)
        self.assertEqual(to_int("XLII"), 42)
        self.assertEqual(to_int("MMXXIV"), 2024)

    def test_boundaries(self):
        self.assertEqual(to_int("I"), 1)
        self.assertEqual(to_int("MMMCMXCIX"), 3999)


class ToIntInvalidCharacterTest(unittest.TestCase):
    def test_empty_string(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("")
        self.assertEqual(ctx.exception.column, 1)

    def test_unknown_character(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("XAV")
        self.assertEqual(ctx.exception.column, 2)
        self.assertIn("not a Roman numeral character", ctx.exception.message)

    def test_lowercase_character(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("xiv")
        self.assertEqual(ctx.exception.column, 1)
        self.assertIn("lowercase", ctx.exception.message)


class ToIntGrammarTest(unittest.TestCase):
    def test_four_repeats_rejected(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("IIII")
        self.assertIn("repeated 4 times", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 4)

    def test_four_repeats_rejected_in_hundreds_group(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("CCCC")
        self.assertIn("repeated 4 times", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 4)

    def test_five_symbol_cannot_repeat(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("VV")
        self.assertIn("cannot repeat", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 2)

    def test_five_symbol_cannot_repeat_in_hundreds_group(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("DD")
        self.assertIn("cannot repeat", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 2)

    def test_subtraction_more_than_one_power_below_rejected(self):
        # IM would mean "one below one thousand" skipping hundreds and
        # tens; only the next power of ten may be subtracted.
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("IM")
        self.assertIn("descending order", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 2)

    def test_five_symbol_followed_by_larger_unit_rejected(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("VX")
        self.assertIn("descending order", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 2)

    def test_out_of_order_units_rejected(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("IL")
        self.assertIn("descending order", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 2)


class ErrorFormattingTest(unittest.TestCase):
    def test_format_includes_source_line_and_pointer(self):
        try:
            to_int("IIII", line=3, source="numerals.txt")
        except RomanNumeralError as exc:
            formatted = exc.format()
        else:
            self.fail("expected RomanNumeralError")
        lines = formatted.splitlines()
        self.assertEqual(lines[0], (
            "numerals.txt:3:4: error: 'I' repeated 4 times "
            "in a row; at most 3 are allowed"
        ))
        self.assertEqual(lines[1], "    IIII")
        # the caret sits directly under the 4th 'I' (column 4), lined up
        # with the 4-space indent shared by both lines.
        caret_index = lines[2].index("^")
        numeral_index = lines[1].index("IIII") + 3
        self.assertEqual(caret_index, numeral_index)

    def test_format_without_source(self):
        try:
            to_int("")
        except RomanNumeralError as exc:
            formatted = exc.format()
        else:
            self.fail("expected RomanNumeralError")
        self.assertTrue(formatted.startswith("1:1: error:"))


class ToRomanTest(unittest.TestCase):
    def test_known_values(self):
        cases = {
            1: "I", 4: "IV", 9: "IX", 40: "XL", 90: "XC",
            400: "CD", 900: "CM", 1994: "MCMXCIV", 3999: "MMMCMXCIX",
        }
        for value, numeral in cases.items():
            self.assertEqual(to_roman(value), numeral)

    def test_round_trip_full_range(self):
        for value in range(1, 4000):
            self.assertEqual(to_int(to_roman(value)), value)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            to_roman(0)
        with self.assertRaises(ValueError):
            to_roman(4000)
        with self.assertRaises(ValueError):
            to_roman(-5)

    def test_rejects_non_integer(self):
        with self.assertRaises(ValueError):
            to_roman(4.0)
        with self.assertRaises(ValueError):
            to_roman("4")
        with self.assertRaises(ValueError):
            to_roman(True)


if __name__ == "__main__":
    unittest.main()
