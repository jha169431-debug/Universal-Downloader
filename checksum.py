import hashlib
from dataclasses import dataclass
from pathlib import Path


SUPPORTED_CHECKSUMS = {
    "sha256": ("SHA-256", 64),
    "sha1": ("SHA-1", 40),
    "md5": ("MD5", 32),
}


@dataclass(frozen=True)
class ChecksumSpec:
    algorithm: str
    expected: str

    @property
    def label(self):
        return SUPPORTED_CHECKSUMS[self.algorithm][0]


class ChecksumMismatch(Exception):
    def __init__(
        self,
        spec,
        actual,
        file_path,
        quarantined_path=None,
    ):
        self.spec = spec
        self.actual = actual
        self.file_path = Path(file_path)
        self.quarantined_path = (
            Path(quarantined_path)
            if quarantined_path is not None
            else None
        )

        location = (
            f" Quarantined as: {self.quarantined_path}"
            if self.quarantined_path is not None
            else ""
        )

        super().__init__(
            f"{spec.label} mismatch. "
            f"Expected {spec.expected}; got {actual}."
            f"{location}"
        )


def parse_checksum(algorithm, value):
    if value is None:
        return None

    algorithm = algorithm.lower().replace("-", "")
    if algorithm not in SUPPORTED_CHECKSUMS:
        raise ValueError(
            "Unsupported checksum algorithm: "
            f"{algorithm}"
        )

    expected = value.strip().lower()

    if expected.startswith(f"{algorithm}:"):
        expected = expected.split(":", 1)[1].strip()

    _, required_length = SUPPORTED_CHECKSUMS[algorithm]

    if len(expected) != required_length:
        raise ValueError(
            f"{SUPPORTED_CHECKSUMS[algorithm][0]} must be "
            f"{required_length} hexadecimal characters."
        )

    try:
        int(expected, 16)
    except ValueError as exc:
        raise ValueError(
            f"{SUPPORTED_CHECKSUMS[algorithm][0]} contains "
            "non-hexadecimal characters."
        ) from exc

    return ChecksumSpec(
        algorithm=algorithm,
        expected=expected,
    )


def hash_file(
    path,
    algorithm,
    *,
    chunk_size=4 * 1024 * 1024,
    progress=None,
):
    path = Path(path)
    digest = hashlib.new(algorithm)
    total = path.stat().st_size
    processed = 0

    with path.open("rb") as stream:
        while True:
            chunk = stream.read(chunk_size)

            if not chunk:
                break

            digest.update(chunk)
            processed += len(chunk)

            if progress is not None:
                progress(processed, total)

    return digest.hexdigest().lower()
