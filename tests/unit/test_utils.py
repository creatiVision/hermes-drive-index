from datetime import UTC, datetime

import pytest

from hermes_drive_index.core.utils import human_bytes, now_iso


def test_now_iso():
    iso_str = now_iso()
    assert isinstance(iso_str, str)
    dt = datetime.fromisoformat(iso_str)
    assert dt.microsecond == 0
    assert dt.tzinfo is not None
    assert dt.utcoffset() == UTC.utcoffset(dt)


@pytest.mark.parametrize(
    "n, expected",
    [
        (0, "0 B"),
        (1, "1 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        (1024, "1.0 KiB"),
        (1536, "1.5 KiB"),
        (1048575, "1024.0 KiB"),
        (1048576, "1.0 MiB"),
        (1572864, "1.5 MiB"),
        (1073741824, "1.0 GiB"),
        (5368709120, "5.0 GiB"),
        (2147483648000, "2000.0 GiB"),
    ],
)
def test_human_bytes(n, expected):
    assert human_bytes(n) == expected
