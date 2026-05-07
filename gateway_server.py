# Project ID: 61-7460
# Raspberry Pi Edge Gateway Setup
import socket
import serial
import os
import struct
import select

UART_PORT = '/dev/ttyAMA0'
BAUD_RATE = 115200
HOST = '0.0.0.0'
PORT = 5000
BITSTREAM_FILENAME = 'design.bit'

def program_fpga(bitstream_path):
    print(f"Programming FPGA with {bitstream_path}...")
    result = os.system(f"openFPGALoader -b bpi_f5 {bitstream_path}")
    if result == 0:
        print("FPGA Configured successfully.")
    else:
        print("Programming failed.")

def start_gateway():
    ser = serial.Serial(UART_PORT, BAUD_RATE, timeout=0) 
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    
    print(f"Pi Gateway: Listening for PC on port {PORT}...")

    while True:
        conn, addr = server_socket.accept()
        print(f"Connected to {addr}")
        
        try:
            while True:
                ready_to_read, _, _ = select.select([conn], [], [], 0.1)
                
                if ready_to_read:
                    header_data = conn.recv(5)
                    if not header_data:
                        break 
                        
                    if len(header_data) == 5:
                        msg_type, payload_length = struct.unpack('!BI', header_data)
                        
                        payload = bytearray()
                        while len(payload) < payload_length:
                            chunk = conn.recv(min(4096, payload_length - len(payload)))
                            if not chunk: break
                            payload.extend(chunk)
                            
                        if msg_type == 0x01: 
                            print(f"Receiving bitstream... size: {len(payload)} bytes")
                            with open(BITSTREAM_FILENAME, 'wb') as f:
                                f.write(payload)
                            program_fpga(BITSTREAM_FILENAME)
                            conn.send(b'SUCCESS: FPGA Programmed\n')
                            
                        elif msg_type == 0x02: 
                            print("Routing ALSU command to FPGA...")
                            ser.write(payload)
                
                if ser.in_waiting > 0:
                    fpga_result = ser.read(ser.in_waiting)
                    conn.send(fpga_result)
                    
        except Exception as e:
            print(f"Connection error: {e}")
        finally:
            conn.close()
            print("Connection to PC closed. Waiting for new connection...")

if __name__ == '__main__':
    start_gateway()