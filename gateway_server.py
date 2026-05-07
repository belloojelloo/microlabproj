# Project ID: 61-7460
# Raspberry Pi Edge Gateway Setup
import base64
import binascii
import json
import os
import socket
import struct
import subprocess
import time

UART_PORT = "/dev/ttyAMA0"
BAUD_RATE = 115200
HOST = "0.0.0.0"
PORT = 5000
BITSTREAM_DIR = "."
BITSTREAM_FILENAME = "design.bit"

HEADER_FMT = ">I"
HEADER_SIZE = struct.calcsize(HEADER_FMT)
MAX_PAYLOAD = 16 * 1024 * 1024
RECV_CHUNK_SIZE = 4096
ALSU_RESPONSE_TIMEOUT = 2.0
VALID_ALSU_OPS = {"ADD", "SUB", "MUL", "SHIFT", "BYPASS", "XOR"}


class ProtocolError(Exception):
    pass


def encode_message(message):
    payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
    return struct.pack(HEADER_FMT, len(payload)) + payload


def recv_message(conn):
    raw_header = recv_exact(conn, HEADER_SIZE)
    if len(raw_header) < HEADER_SIZE:
        raise EOFError("Connection closed before header was received.")

    (payload_length,) = struct.unpack(HEADER_FMT, raw_header)
    if payload_length > MAX_PAYLOAD:
        raise ProtocolError(
            f"Declared payload length {payload_length} exceeds limit {MAX_PAYLOAD}."
        )

    raw_payload = recv_exact(conn, payload_length)
    if len(raw_payload) < payload_length:
        raise EOFError(
            f"Connection closed after {len(raw_payload)} of {payload_length} bytes."
        )

    try:
        message = json.loads(raw_payload.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ProtocolError("Payload is not valid UTF-8.") from exc
    except json.JSONDecodeError as exc:
        raise ProtocolError("Payload is not valid JSON.") from exc

    if not isinstance(message, dict):
        raise ProtocolError("JSON payload must be an object.")
    return message


def recv_exact(conn, size):
    data = bytearray()
    while len(data) < size:
        chunk = conn.recv(min(RECV_CHUNK_SIZE, size - len(data)))
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def send_response(conn, response):
    conn.sendall(encode_message(response))


def ok_response(**fields):
    response = {"status": "ok"}
    response.update(fields)
    return response


def error_response(message):
    return {"status": "error", "message": message}


def program_fpga(bitstream_path):
    print(f"Programming FPGA with {bitstream_path}...")
    result = subprocess.run(
        ["openFPGALoader", "-b", "bpi_f5", bitstream_path],
        check=False,
    )
    if result.returncode == 0:
        print("FPGA configured successfully.")
        return True

    print(f"Programming failed with exit code {result.returncode}.")
    return False


def handle_message(message, ser):
    header = message.get("header")

    if header == "PING":
        return ok_response()

    if header == "FILE":
        return handle_file_message(message)

    if header == "ALSU":
        return handle_alsu_message(message, ser)

    return error_response(f"Unknown header: {header!r}")


def handle_file_message(message):
    filename = os.path.basename(str(message.get("filename") or BITSTREAM_FILENAME))
    declared_size = message.get("size")
    encoded_payload = message.get("payload")

    if not isinstance(declared_size, int) or declared_size < 0:
        return error_response("FILE size must be a non-negative integer.")
    if not isinstance(encoded_payload, str):
        return error_response("FILE payload must be a Base64 string.")

    try:
        bitstream = base64.b64decode(encoded_payload, validate=True)
    except (binascii.Error, ValueError):
        return error_response("FILE payload is not valid Base64.")

    if len(bitstream) != declared_size:
        return error_response(
            f"FILE size mismatch: declared {declared_size}, decoded {len(bitstream)}."
        )

    save_path = os.path.join(BITSTREAM_DIR, filename)
    with open(save_path, "wb") as bitstream_file:
        bitstream_file.write(bitstream)
    print(f"Saved bitstream {save_path} ({len(bitstream)} bytes).")

    if not program_fpga(save_path):
        return error_response("FPGA programming failed.")

    return ok_response(message="FPGA programmed", filename=filename, size=len(bitstream))


def handle_alsu_message(message, ser):
    op = str(message.get("op", "")).strip().upper()
    a = message.get("a")
    b = message.get("b")

    if op not in VALID_ALSU_OPS:
        return error_response(f"Invalid ALSU op: {op!r}")
    if not isinstance(a, int) or not 0 <= a <= 255:
        return error_response("ALSU field 'a' must be an integer from 0 to 255.")
    if not isinstance(b, int) or not 0 <= b <= 255:
        return error_response("ALSU field 'b' must be an integer from 0 to 255.")

    uart_payload = build_alsu_uart_payload(op, a, b)
    print(f"Routing ALSU command to FPGA: op={op} a={a} b={b}")
    ser.reset_input_buffer()
    ser.write(uart_payload)
    ser.flush()

    raw_result = read_uart_response(ser)
    if not raw_result:
        return error_response("Timed out waiting for FPGA ALSU response.")

    return parse_alsu_response(raw_result)


def build_alsu_uart_payload(op, a, b):
    return json.dumps({"op": op, "a": a, "b": b}, separators=(",", ":")).encode(
        "utf-8"
    ) + b"\n"


def read_uart_response(ser):
    deadline = time.monotonic() + ALSU_RESPONSE_TIMEOUT
    response = bytearray()

    while time.monotonic() < deadline:
        waiting = ser.in_waiting
        if waiting:
            response.extend(ser.read(waiting))
            if b"\n" in response:
                break
        time.sleep(0.01)

    return bytes(response).strip()


def parse_alsu_response(raw_result):
    text = raw_result.decode("utf-8", errors="replace").strip()
    try:
        response = json.loads(text)
    except json.JSONDecodeError:
        try:
            return ok_response(result=int(text, 0))
        except ValueError:
            return error_response(f"FPGA returned an invalid ALSU result: {text!r}")

    if isinstance(response, int):
        return ok_response(result=response)
    if not isinstance(response, dict):
        return error_response("FPGA ALSU JSON response must be an object.")
    if response.get("status") == "error":
        return error_response(str(response.get("message", "FPGA reported an error.")))
    if "result" not in response:
        return error_response("FPGA ALSU response did not include a result.")

    try:
        return ok_response(result=int(response["result"]))
    except (TypeError, ValueError):
        return error_response("FPGA ALSU result was not an integer.")


def start_gateway():
    import serial

    ser = serial.Serial(UART_PORT, BAUD_RATE, timeout=0)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)

    print(f"Pi Gateway: Listening for PC on port {PORT}...")

    try:
        while True:
            conn, addr = server_socket.accept()
            print(f"Connected to {addr}")

            try:
                while True:
                    try:
                        request = recv_message(conn)
                    except EOFError:
                        break
                    except ProtocolError as exc:
                        send_response(conn, error_response(str(exc)))
                        continue

                    response = handle_message(request, ser)
                    send_response(conn, response)

            except OSError as exc:
                print(f"Connection error: {exc}")
            finally:
                conn.close()
                print("Connection to PC closed. Waiting for new connection...")
    finally:
        server_socket.close()
        ser.close()


if __name__ == "__main__":
    start_gateway()
