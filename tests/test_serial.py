"""Tests for Flipper Zero serial communication (all mocked, no hardware)."""

from unittest.mock import MagicMock, patch

import pytest

from flipperforge.deploy.serial import FlipperConnection, FlipperConnectionError

# -- Port detection tests --


@patch("flipperforge.deploy.serial.serial.tools.list_ports.comports")
def test_auto_detect_flipper(mock_comports):
    """detect_port should return the port matching Flipper VID/PID."""
    mock_port = MagicMock()
    mock_port.vid = 0x0483
    mock_port.pid = 0x5740
    mock_port.device = "COM3"
    mock_comports.return_value = [mock_port]

    port = FlipperConnection.detect_port()
    assert port == "COM3"


@patch("flipperforge.deploy.serial.serial.tools.list_ports.comports")
def test_no_flipper_found(mock_comports):
    """detect_port should raise FlipperConnectionError when no device found."""
    mock_comports.return_value = []

    with pytest.raises(FlipperConnectionError, match="No Flipper Zero detected"):
        FlipperConnection.detect_port()


@patch("flipperforge.deploy.serial.serial.tools.list_ports.comports")
@patch("flipperforge.deploy.serial.serial.Serial")
def test_auto_detect_when_port_none(mock_serial_cls, mock_comports):
    """FlipperConnection(port=None) should call detect_port automatically."""
    mock_port = MagicMock()
    mock_port.vid = 0x0483
    mock_port.pid = 0x5740
    mock_port.device = "COM3"
    mock_comports.return_value = [mock_port]
    mock_serial_cls.return_value = MagicMock()

    conn = FlipperConnection(port=None)
    mock_serial_cls.assert_called_once_with(
        port="COM3",
        baudrate=115200,
        timeout=5,
    )
    conn.close()


# -- Command sending tests --


@patch("flipperforge.deploy.serial.serial.Serial")
def test_send_command(mock_serial_cls):
    """_send_command should write the command and return the response."""
    mock_serial = MagicMock()
    mock_serial_cls.return_value = mock_serial
    mock_serial.read.return_value = b"OK\r\n>: "

    conn = FlipperConnection("COM3")
    result = conn._send_command("storage list /ext/badusb")

    mock_serial.write.assert_called_once_with(b"storage list /ext/badusb\r\n")
    assert "OK" in result


@patch("flipperforge.deploy.serial.serial.Serial")
def test_storage_error_raises_exception(mock_serial_cls):
    """_send_command should raise FlipperConnectionError on storage errors."""
    mock_serial = MagicMock()
    mock_serial_cls.return_value = mock_serial
    mock_serial.read.return_value = b"Storage error: file not found\r\n>: "

    conn = FlipperConnection("COM3")

    with pytest.raises(FlipperConnectionError, match="Storage error"):
        conn._send_command("storage read /ext/badusb/missing.txt")


# -- File listing tests --


@patch("flipperforge.deploy.serial.serial.Serial")
def test_list_files_returns_dicts(mock_serial_cls):
    """list_badusb_files should return dicts with 'name' and 'size' keys."""
    mock_serial = MagicMock()
    mock_serial_cls.return_value = mock_serial

    listing_output = b"[D] .tmp\r\n[F] hello.txt 128\r\n[F] payload.txt 256\r\n>: "
    mock_serial.read.return_value = listing_output

    conn = FlipperConnection("COM3")
    files = conn.list_badusb_files()

    assert len(files) == 2
    assert files[0] == {"name": "hello.txt", "size": "128"}
    assert files[1] == {"name": "payload.txt", "size": "256"}


@patch("flipperforge.deploy.serial.serial.Serial")
def test_list_files_no_size(mock_serial_cls):
    """list_badusb_files should handle entries without a size field."""
    mock_serial = MagicMock()
    mock_serial_cls.return_value = mock_serial

    listing_output = b"[F] nosize.txt\r\n>: "
    mock_serial.read.return_value = listing_output

    conn = FlipperConnection("COM3")
    files = conn.list_badusb_files()

    assert len(files) == 1
    assert files[0] == {"name": "nosize.txt", "size": ""}


# -- Deploy tests --


@patch("flipperforge.deploy.serial.serial.Serial")
def test_deploy_payload(mock_serial_cls):
    """deploy should write the command and the script data."""
    mock_serial = MagicMock()
    mock_serial_cls.return_value = mock_serial
    mock_serial.read.return_value = b"OK\r\n>: "

    conn = FlipperConnection("COM3")
    conn.deploy("test.txt", "STRING hello")

    # Should have written the write_chunk command and the payload
    calls = mock_serial.write.call_args_list
    assert len(calls) >= 2
    # First call is the command
    assert b"storage write_chunk /ext/badusb/test.txt" in calls[0][0][0]
    # Second call is the script content
    assert calls[1][0][0] == b"STRING hello"


# -- Read file tests --


@patch("flipperforge.deploy.serial.serial.Serial")
def test_read_file_strips_protocol(mock_serial_cls):
    """read_file should strip command echo and prompt from output."""
    mock_serial = MagicMock()
    mock_serial_cls.return_value = mock_serial

    raw_output = b"storage read /ext/badusb/test.txt\r\nREM My payload\r\nDELAY 500\r\n>: "
    mock_serial.read.return_value = raw_output

    conn = FlipperConnection("COM3")
    content = conn.read_file("test.txt")

    assert "REM My payload" in content
    assert "DELAY 500" in content
    assert "storage read" not in content
    assert ">:" not in content


# -- Close safety tests --


def test_close_safe_when_serial_not_set():
    """close() should not crash if _serial was never assigned."""
    conn = FlipperConnection.__new__(FlipperConnection)
    conn.close()  # Should not raise
