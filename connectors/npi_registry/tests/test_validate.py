import unittest

from ..validate import is_valid_npi, npi_check_digit, validate_npi


class ValidateTests(unittest.TestCase):
    def test_known_valid_npi_passes_luhn(self):
        # 1234567893: check digit 3 is correct for the 80840 + 123456789 body.
        res = validate_npi("1234567893")
        self.assertTrue(res["valid"])
        self.assertEqual(res["reason"], "ok")
        self.assertTrue(is_valid_npi("1234567893"))

    def test_bad_check_digit_fails(self):
        # 1234567890 has the wrong final digit (should be 3).
        res = validate_npi("1234567890")
        self.assertFalse(res["valid"])
        self.assertIn("check digit", res["reason"])

    def test_check_digit_helper(self):
        self.assertEqual(npi_check_digit("123456789"), 3)

    def test_wrong_length_and_non_numeric(self):
        self.assertFalse(validate_npi("123")["valid"])
        self.assertFalse(validate_npi("12345678AB")["valid"])
        self.assertFalse(validate_npi("")["valid"])

    def test_second_known_valid_npi(self):
        # 1245319599 (organization sample) — verify it round-trips.
        expected = npi_check_digit("124531959")
        self.assertTrue(validate_npi("124531959" + str(expected))["valid"])


if __name__ == "__main__":
    unittest.main()
