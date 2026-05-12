import json
import time

import serial

VALID_OPERATIONS = {"ADD", "SUB", "MUL", "SHIFT", "BYPASS", "XOR"}
_RESULT_MASK = 0xFFFF
_UART_PORT = "/dev/ttyAMA0"
_BAUD_RATE = 115200
_RESPONSE_TIMEOUT = 2.0


class FPGABridgeError(Exception):
    pass


class FPGABridge:
    def __init__(self, port: str = _UART_PORT, baud: int = _BAUD_RATE):
        self._ser = serial.Serial(port, baud, timeout=0)

    def compute(self, operation: str, a: int, b: int) -> int:
        op = operation.upper()
        if op not in VALID_OPERATIONS:
            raise FPGABridgeError(f"Unknown operation: {operation!r}")

        payload = json.dumps({"op": op, "a": a, "b": b}, separators=(",", ":")).encode("utf-8") + b"\n"
        try:
            self._ser.reset_input_buffer()
            self._ser.write(payload)
            self._ser.flush()
        except serial.SerialException as exc:
            raise FPGABridgeError(f"UART write error: {exc}") from exc

        raw = self._read_response()
        if not raw:
            raise FPGABridgeError("Timed out waiting for FPGA ALSU response.")

        return self._parse_response(raw)

    def _read_response(self) -> bytes:
        deadline = time.monotonic() + _RESPONSE_TIMEOUT
        buf = bytearray()
        try:
            while time.monotonic() < deadline:
                waiting = self._ser.in_waiting
                if waiting:
                    buf.extend(self._ser.read(waiting))
                    if b"\n" in buf:
                        break
                time.sleep(0.01)
        except serial.SerialException as exc:
            raise FPGABridgeError(f"UART read error: {exc}") from exc
        return bytes(buf).strip()

    def _parse_response(self, raw: bytes) -> int:
        text = raw.decode("utf-8", errors="replace").strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            try:
                return int(text, 0) & _RESULT_MASK
            except ValueError:
                raise FPGABridgeError(f"FPGA returned invalid ALSU result: {text!r}")

        if isinstance(data, int):
            return data & _RESULT_MASK
        if isinstance(data, dict):
            if data.get("status") == "error":
                raise FPGABridgeError(str(data.get("message", "FPGA reported an error.")))
            if "result" in data:
                return int(data["result"]) & _RESULT_MASK
        raise FPGABridgeError(f"Unexpected FPGA response: {text!r}")

    def close(self):
        self._ser.close()
