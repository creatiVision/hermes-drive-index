import re
from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from hermes_drive_index.core.utils import human_bytes, now_iso


def test_now_iso():
    iso_str = now_iso()
    assert isinstance(iso_str, str)
    # Check valid ISO 8601 UTC timestamp format: YYYY-MM-DDTHH:MM:SS+00:00 (no microseconds)
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$", iso_str) is not None
    dt = datetime.fromisoformat(iso_str)
    assert dt.microsecond == 0
    assert dt.tzinfo is not None
    assert dt.utcoffset() == UTC.utcoffset(dt)


def test_now_iso_deterministic():
    fixed_time = datetime(2026, 3, 30, 14, 25, 36, 987654, tzinfo=UTC)
    with patch("hermes_drive_index.core.utils.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_time
        iso_str = now_iso()
        assert iso_str == "2026-03-30T14:25:36+00:00"
        mock_dt.now.assert_called_once_with(UTC)


def test_now_iso_strips_microseconds():
    fixed_time_zero_micro = datetime(2026, 1, 1, 0, 0, 0, 0, tzinfo=UTC)
    with patch("hermes_drive_index.core.utils.datetime") as mock_dt:
        mock_dt.now.return_value = fixed_time_zero_micro
        assert now_iso() == "2026-01-01T00:00:00+00:00"


@pytest.mark.parametrize(
    "n, expected",
    [
        # Bytes range
        (0, "0 B"),
        (1, "1 B"),
        (512, "512 B"),
        (1023, "1023 B"),
        # KiB range and boundaries
        (1024, "1.0 KiB"),
        (1536, "1.5 KiB"),
        (2048, "2.0 KiB"),
        (1048575, "1024.0 KiB"),
        # MiB range and boundaries
        (1048576, "1.0 MiB"),
        (1572864, "1.5 MiB"),
        (2097152, "2.0 MiB"),
        (1073741823, "1024.0 MiB"),
        # GiB range and beyond (capped at GiB)
        (1073741824, "1.0 GiB"),
        (2147483648, "2.0 GiB"),
        (5368709120, "5.0 GiB"),
        (1099511627776, "1024.0 GiB"),  # 1 TiB
        (2147483648000, "2000.0 GiB"),
        # Negative values (n < 1024 is true, so formatted as bytes)
        (-1, "-1 B"),
        (-100, "-100 B"),
        (-1024, "-1024 B"),
        (-2048, "-2048 B"),
    ],
)
def test_human_bytes(n, expected):
    assert human_bytes(n) == expected


def test_human_bytes_float_rounding():
    # 1024 + 512 = 1536 (1.5 KiB)
    assert human_bytes(1536) == "1.5 KiB"
    # 1024 + 100 = 1124 -> 1124 / 1024 = 1.09765625 -> "1.1 KiB"
    assert human_bytes(1124) == "1.1 KiB"
    # 1024 + 50 = 1074 -> 1074 / 1024 = 1.048828125 -> "1.0 KiB"
    assert human_bytes(1074) == "1.0 KiB"
