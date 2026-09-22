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


class VinculumToIntTest(unittest.TestCase):
    def test_overlined_letter_multiplies_by_thousand(self):
        self.assertEqual(to_int("V̅", vinculum=True), 5000)
        self.assertEqual(to_int("X̅", vinculum=True), 10000)
        self.assertEqual(to_int("M̅", vinculum=True), 1000000)

    def test_overlined_run_plus_remainder(self):
        self.assertEqual(to_int("V̅XLII", vinculum=True), 5042)
        self.assertEqual(to_int("I̅V̅CMXCIX", vinculum=True), 4999)

    def test_overlined_run_of_several_letters(self):
        # X overlined, III overlined: (10 + 3) * 1000 = 13000
        self.assertEqual(to_int("X̅I̅I̅I̅", vinculum=True), 13000)

    def test_plain_numeral_unaffected_by_vinculum_flag(self):
        self.assertEqual(to_int("MCMXCIV", vinculum=True), 1994)

    def test_overline_rejected_without_flag(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("V̅")
        self.assertIn("combining overline", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 2)

    def test_error_inside_overlined_run_maps_back_to_original_column(self):
        # "VV̅" overlined run is "VV", which repeats the five-symbol;
        # that error is at stripped column 2, i.e. original column 3.
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("V̅V̅", vinculum=True)
        self.assertIn("cannot repeat", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 3)

    def test_error_in_remainder_maps_back_to_original_column(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("V̅IIII", vinculum=True)
        self.assertIn("repeated 4 times", ctx.exception.message)
        self.assertEqual(ctx.exception.column, 6)

    def test_stray_overline_without_pairing_is_rejected(self):
        with self.assertRaises(RomanNumeralError) as ctx:
            to_int("XV̅I", vinculum=True)
        self.assertIn("combining overline", ctx.exception.message)


class VinculumToRomanTest(unittest.TestCase):
    def test_values_up_to_3999_are_unchanged(self):
        self.assertEqual(to_roman(3999, vinculum=True), to_roman(3999))
        self.assertEqual(to_roman(42, vinculum=True), "XLII")

    def test_exact_thousands(self):
        self.assertEqual(to_roman(5000, vinculum=True), "V̅")
        self.assertEqual(to_roman(4000, vinculum=True), "I̅V̅")

    def test_thousands_with_remainder(self):
        self.assertEqual(to_roman(5042, vinculum=True), "V̅XLII")

    def test_rejects_without_flag_above_3999(self):
        with self.assertRaises(ValueError):
            to_roman(4000)

    def test_rejects_out_of_range_even_with_flag(self):
        with self.assertRaises(ValueError):
            to_roman(4000000, vinculum=True)
        with self.assertRaises(ValueError):
            to_roman(0, vinculum=True)

    def test_round_trip(self):
        for value in [1000, 3999, 4000, 5042, 13000, 999999, 3999999]:
            numeral = to_roman(value, vinculum=True)
            self.assertEqual(to_int(numeral, vinculum=True), value)


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
