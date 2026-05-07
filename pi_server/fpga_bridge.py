VALID_OPERATIONS = {"ADD", "SUB", "MUL", "SHIFT", "BYPASS", "XOR"}
_RESULT_MASK = 0xFFFF


class FPGABridgeError(Exception):
    pass


class FPGABridge:
    def __init__(self):
        pass  # Future: open UART/SPI port here

    def compute(self, operation: str, a: int, b: int) -> int:
        op = operation.upper()
        if op not in VALID_OPERATIONS:
            raise FPGABridgeError(f"Unknown operation: {operation!r}")
        # Software simulation — replace with real FPGA comms
        if op == "ADD":
            return (a + b) & _RESULT_MASK
        if op == "SUB":
            return (a - b) & _RESULT_MASK
        if op == "MUL":
            return (a * b) & _RESULT_MASK
        if op == "SHIFT":
            return (a << b) & _RESULT_MASK
        if op == "BYPASS":
            return a & _RESULT_MASK
        if op == "XOR":
            return (a ^ b) & _RESULT_MASK
        raise FPGABridgeError(f"Unhandled operation: {op}")

    def close(self):
        pass  # Future: close serial port here
