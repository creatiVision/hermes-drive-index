from datetime import UTC, datetime, timezone
from unittest.mock import patch

import pytest

from hermes_drive_index.core.utils import human_bytes, now_iso


def test_now_iso():
    iso_str = now_iso()
    assert isinstance(iso_str, str)
    dt = datetime.fromisoformat(iso_str)
    assert dt.microsecond == 0
    assert dt.tzinfo is not None
    assert dt.utcoffset() == UTC.utcoffset(dt)


def test_now_iso_deterministic():
    fixed_time = datetime(2026, 3, 30, 14, 25, 36, 987654, tzinfo=timezone.utc)
    with patch("hermes_drive_index.core.utils.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_time
        iso_str = now_iso()
        assert iso_str == "2026-03-30T14:25:36+00:00"
        mock_dt.now.assert_called_once_with(timezone.utc)


@pytest.mark.parametrize(
    "n, expected",
    [
        # Bytes range
        (0, "0 B"),
        (1, "1 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        # KiB range
        (1024, "1.0 KiB"),
        (1536, "1.5 KiB"),
        (1048575, "1024.0 KiB"),
        # MiB range
        (1048576, "1.0 MiB"),
        (1572864, "1.5 MiB"),
        (1073741823, "1024.0 MiB"),
        # GiB range and beyond (capped at GiB)
        (1073741824, "1.0 GiB"),
        (5368709120, "5.0 GiB"),
        (1099511627776, "1024.0 GiB"),  # 1 TiB
        (2147483648000, "2000.0 GiB"),
        # Negative values (n < 1024 is true, so formatted as bytes)
        (-100, "-100 B"),
        (-2048, "-2048 B"),
    ],
)
def test_human_bytes(n, expected):
    assert human_bytes(n) == expected
