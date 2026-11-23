import unittest

from cidr_validator import is_valid_ipv4_cidr


class IsValidIPv4CIDRTests(unittest.TestCase):
    def test_accepts_valid_common_values(self):
        valid_values = [
            "0.0.0.0/0",
            "10.0.0.1/8",
            "192.168.1.1/24",
            "255.255.255.255/32",
            "172.16.5.10/16",
            "1.2.3.4/9",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(is_valid_ipv4_cidr(value))

    def test_accepts_host_bits_set(self):
        valid_values = [
            "192.168.1.129/24",
            "10.255.255.255/8",
            "1.1.1.1/0",
            "203.0.113.7/31",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(is_valid_ipv4_cidr(value))

    def test_accepts_boundary_octets_and_prefixes(self):
        valid_values = [
            "0.0.0.0/32",
            "255.0.0.0/0",
            "255.255.255.0/32",
            "127.0.0.1/1",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(is_valid_ipv4_cidr(value))

    def test_rejects_malformed_ipv4_parts(self):
        invalid_values = [
            "256.0.0.1/24",
            "192.168.1/24",
            "192.168.1.1.1/24",
            "192.168.-1.1/24",
            "192.168.1.a/24",
            "999.999.999.999/32",
            "01.2.3.4/24",
            "1.02.3.4/24",
            "1.2.003.4/24",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_ipv4_cidr(value))

    def test_rejects_invalid_prefixes(self):
        invalid_values = [
            "192.168.1.1",
            "192.168.1.1/",
            "192.168.1.1/-1",
            "192.168.1.1/33",
            "192.168.1.1/003",
            "192.168.1.1/+24",
            "192.168.1.1/24/7",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_ipv4_cidr(value))

    def test_rejects_non_cidr_forms_and_ipv6(self):
        invalid_values = [
            "192.168.1.1/255.255.255.0",
            "2001:db8::/32",
            "::1/128",
            "192.168.1.1:24",
            "192.168.1.1 /24",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_ipv4_cidr(value))

    def test_rejects_surrounding_or_embedded_whitespace(self):
        invalid_values = [
            " 192.168.1.1/24",
            "192.168.1.1/24 ",
            "\t192.168.1.1/24",
            "192.168.1.1/24\n",
            "192.168. 1.1/24",
            "192.168.1.1/ 24",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_ipv4_cidr(value))

    def test_rejects_non_string_inputs(self):
        invalid_values = [None, 123, 3.14, [], {}, object()]

        for value in invalid_values:
            with self.subTest(value=repr(value)):
                self.assertFalse(is_valid_ipv4_cidr(value))


if __name__ == "__main__":
    unittest.main()
