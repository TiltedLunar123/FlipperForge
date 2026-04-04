"""Flipper Zero serial communication for deploying BadUSB payloads."""

import serial
import serial.tools.list_ports


class FlipperConnectionError(Exception):
    """Raised when communication with the Flipper Zero fails."""


class FlipperConnection:
    """Manages serial communication with a Flipper Zero device.

    Provides methods for detecting the device, deploying payloads,
    listing files, and reading/deleting files on the Flipper.
    """

    FLIPPER_VID = 0x0483
    FLIPPER_PID = 0x5740
    BAUD_RATE = 115200
    TIMEOUT = 5
    PROMPT = ">: "

    @staticmethod
    def detect_port() -> str:
        """Scan COM ports for a connected Flipper Zero.

        Looks for devices matching VID 0x0483 and PID 0x5740.

        Returns:
            The port name (e.g. 'COM3' or '/dev/ttyACM0').

        Raises:
            FlipperConnectionError: If no Flipper Zero is found.
        """
        ports = serial.tools.list_ports.comports()
        for port_info in ports:
            if (
                port_info.vid == FlipperConnection.FLIPPER_VID
                and port_info.pid == FlipperConnection.FLIPPER_PID
            ):
                return port_info.device
        raise FlipperConnectionError(
            "No Flipper Zero detected. Check USB connection."
        )

    def __init__(self, port: str) -> None:
        """Open a serial connection to the Flipper Zero.

        Args:
            port: The serial port to connect to (e.g. 'COM3').

        Raises:
            FlipperConnectionError: If the connection cannot be opened.
        """
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=self.BAUD_RATE,
                timeout=self.TIMEOUT,
            )
        except serial.SerialException as exc:
            raise FlipperConnectionError(
                f"Failed to open port {port}: {exc}"
            ) from exc

    def _send_command(self, command: str) -> str:
        """Send a command to the Flipper and read the response.

        Args:
            command: The CLI command string to send.

        Returns:
            The response text from the Flipper.

        Raises:
            FlipperConnectionError: If a storage error is detected.
        """
        self._serial.write(f"{command}\r\n".encode("utf-8"))
        response = b""
        while True:
            chunk = self._serial.read(256)
            if not chunk:
                break
            response += chunk
            if self.PROMPT.encode("utf-8") in response:
                break

        text = response.decode("utf-8", errors="replace")
        if "Storage error:" in text:
            raise FlipperConnectionError(f"Storage error: {text}")
        return text

    def list_badusb_files(self) -> list[str]:
        """List files in the BadUSB directory on the Flipper.

        Returns:
            A list of filenames found in /ext/badusb.
        """
        output = self._send_command("storage list /ext/badusb")
        files: list[str] = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("[F]"):
                # Format: [F] filename.txt 1234
                parts = line.split()
                if len(parts) >= 2:
                    files.append(parts[1])
        return files

    def deploy(self, filename: str, script: str) -> None:
        """Write a payload script to the Flipper BadUSB directory.

        Uses the storage write_chunk command to transfer the payload.

        Args:
            filename: The name of the file to create on the Flipper.
            script: The DuckyScript payload content.
        """
        filepath = f"/ext/badusb/{filename}"
        # Use storage write_chunk to send payload data
        self._send_command(f"storage write_chunk {filepath}")
        self._serial.write(script.encode("utf-8"))
        self._serial.write(b"\x00")  # null terminator to signal end
        self._serial.read(256)  # read acknowledgment

    def read_file(self, filename: str) -> str:
        """Read a payload file from the Flipper.

        Args:
            filename: The name of the file in /ext/badusb.

        Returns:
            The file content as a string.
        """
        filepath = f"/ext/badusb/{filename}"
        output = self._send_command(f"storage read {filepath}")
        return output

    def delete_file(self, filename: str) -> None:
        """Delete a payload file from the Flipper.

        Args:
            filename: The name of the file in /ext/badusb.
        """
        filepath = f"/ext/badusb/{filename}"
        self._send_command(f"storage remove {filepath}")

    def close(self) -> None:
        """Close the serial connection."""
        if self._serial and self._serial.is_open:
            self._serial.close()

    def __enter__(self) -> "FlipperConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
