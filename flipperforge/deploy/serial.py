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
        raise FlipperConnectionError("No Flipper Zero detected. Check USB connection.")

    def __init__(self, port: str | None = None) -> None:
        """Open a serial connection to the Flipper Zero.

        Args:
            port: The serial port to connect to (e.g. 'COM3').
                  If None, auto-detects the Flipper Zero.

        Raises:
            FlipperConnectionError: If the connection cannot be opened.
        """
        if port is None:
            port = self.detect_port()
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=self.BAUD_RATE,
                timeout=self.TIMEOUT,
            )
        except serial.SerialException as exc:
            raise FlipperConnectionError(f"Failed to open port {port}: {exc}") from exc

    def _send_command(self, command: str, *, retries: int = 1) -> str:
        """Send a command to the Flipper and read the response.

        Args:
            command: The CLI command string to send.
            retries: Number of retries on timeout (default 1).

        Returns:
            The response text from the Flipper.

        Raises:
            FlipperConnectionError: If a storage error is detected.
        """
        for attempt in range(1 + retries):
            self._serial.write(f"{command}\r\n".encode())
            response = b""
            while True:
                chunk = self._serial.read(256)
                if not chunk:
                    break
                response += chunk
                if self.PROMPT.encode("utf-8") in response:
                    break
                if len(response) > 1024 * 1024:
                    break

            text = response.decode("utf-8", errors="replace")
            if "Storage error:" in text:
                raise FlipperConnectionError(f"Storage error: {text}")

            if text.strip() or attempt == retries:
                return text

        return ""

    def list_badusb_files(self) -> list[dict[str, str]]:
        """List files in the BadUSB directory on the Flipper.

        Returns:
            A list of dicts with 'name' and 'size' keys.
        """
        output = self._send_command("storage list /ext/badusb")
        files: list[dict[str, str]] = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("[F]"):
                # Format: [F] filename.txt 1234
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    size = parts[2] if len(parts) >= 3 else ""
                    files.append({"name": name, "size": size})
        return files

    def deploy(self, filename: str, script: str) -> None:
        """Write a payload script to the Flipper BadUSB directory.

        Uses the storage write_chunk command to transfer the payload
        and verifies the file was written with storage stat.

        Args:
            filename: The name of the file to create on the Flipper.
            script: The DuckyScript payload content.

        Raises:
            FlipperConnectionError: If the deploy fails or verification fails.
        """
        filepath = f"/ext/badusb/{filename}"
        self._send_command(f"storage write_chunk {filepath}")
        self._serial.write(script.encode("utf-8"))
        self._serial.write(b"\x00")  # null terminator to signal end
        self._serial.read(256)  # read acknowledgment

        # Verify the file was written
        stat_output = self._send_command(f"storage stat {filepath}")
        if "Storage error:" in stat_output or "not found" in stat_output.lower():
            raise FlipperConnectionError(
                f"Deploy verification failed: {filepath} not found after write"
            )

    def _strip_protocol(self, output: str, command: str) -> str:
        """Strip the command echo and prompt from serial output."""
        lines = output.splitlines()
        cleaned: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped == command.strip():
                continue
            if stripped == self.PROMPT.strip():
                continue
            if stripped.endswith(self.PROMPT.strip()):
                line = line.replace(self.PROMPT.strip(), "").rstrip()
                if line.strip():
                    cleaned.append(line)
                continue
            cleaned.append(line)
        return "\n".join(cleaned).strip()

    def read_file(self, filename: str) -> str:
        """Read a payload file from the Flipper.

        Args:
            filename: The name of the file in /ext/badusb.

        Returns:
            The file content as a string (protocol overhead stripped).
        """
        filepath = f"/ext/badusb/{filename}"
        command = f"storage read {filepath}"
        output = self._send_command(command)
        return self._strip_protocol(output, command)

    def delete_file(self, filename: str) -> None:
        """Delete a payload file from the Flipper.

        Args:
            filename: The name of the file in /ext/badusb.
        """
        filepath = f"/ext/badusb/{filename}"
        self._send_command(f"storage remove {filepath}")

    def close(self) -> None:
        """Close the serial connection."""
        if hasattr(self, "_serial") and self._serial and self._serial.is_open:
            self._serial.close()

    def __enter__(self) -> "FlipperConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
