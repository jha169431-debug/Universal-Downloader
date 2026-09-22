import hashlib
import tempfile
import unittest
from pathlib import Path

from checksum import hash_file, parse_checksum


class ChecksumTests(unittest.TestCase):
    def test_sha256_hash_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.bin"
            path.write_bytes(b"abc")

            actual = hash_file(path, "sha256")
            expected = hashlib.sha256(b"abc").hexdigest()

            self.assertEqual(actual, expected)

    def test_parse_sha256(self):
        digest = "a" * 64
        spec = parse_checksum("sha256", digest)

        self.assertEqual(spec.algorithm, "sha256")
        self.assertEqual(spec.expected, digest)
        self.assertEqual(spec.label, "SHA-256")

    def test_rejects_bad_length(self):
        with self.assertRaises(ValueError):
            parse_checksum("sha256", "abc")

    def test_rejects_non_hex(self):
        with self.assertRaises(ValueError):
            parse_checksum("md5", "z" * 32)


if __name__ == "__main__":
    unittest.main()
