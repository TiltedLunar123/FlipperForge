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


# -- Command sending tests --


@patch("flipperforge.deploy.serial.serial.Serial")
def test_send_command(mock_serial_cls):
    """_send_command should write the command and return the response."""
    mock_serial = MagicMock()
    mock_serial_cls.return_value = mock_serial
    mock_serial.read.return_value = b"OK\r\n>: "

    conn = FlipperConnection("COM3")
    result = conn._send_command("storage list /ext/badusb")

    mock_serial.write.assert_called_once_with(
        b"storage list /ext/badusb\r\n"
    )
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
def test_list_files_parses_response(mock_serial_cls):
    """list_badusb_files should parse [F] entries from the output."""
    mock_serial = MagicMock()
    mock_serial_cls.return_value = mock_serial

    listing_output = (
        b"[D] .tmp\r\n"
        b"[F] hello.txt 128\r\n"
        b"[F] payload.txt 256\r\n"
        b">: "
    )
    mock_serial.read.return_value = listing_output

    conn = FlipperConnection("COM3")
    files = conn.list_badusb_files()

    assert files == ["hello.txt", "payload.txt"]


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
