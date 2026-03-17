#!/usr/bin/env python3
"""
Send TF-F6 / PowerLED-style ASCII commands over UDP to the controller.

Observed from Wireshark:
- Protocol: UDP
- Destination IP: 192.168.1.252
- Destination Port: 5959
- Payload examples:
    "*#1CNTS2,S1,0000"
    "*#1PRGC10000"
    etc.

This script sends a single ASCII command as one UDP datagram.
"""

import argparse
import socket


def send_udp_command(ip: str, port: int, command: str, add_crlf: bool = False) -> None:
    """
    Send a single ASCII command as UDP to the controller.

    :param ip: Controller IP address (e.g. "192.168.1.252")
    :param port: UDP port (e.g. 5959)
    :param command: Command string (e.g. "*#1RAMT1,4011Hello0000")
    :param add_crlf: If True, append "\r\n" at the end
                     (Wireshark capture showed no CR/LF, so default = False)
    """
    message = command + ("\r\n" if add_crlf else "")
    data = message.encode("ascii")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        print(f"[INFO] Sending to {ip}:{port}: {repr(message)}")
        sock.sendto(data, (ip, port))
        print("[INFO] UDP datagram sent.")
    finally:
        sock.close()


def send_heartbeat(ip: str, port: int) -> None:
    """
    Send the 12-byte 'heartbeat' / magic packet observed in Wireshark:

    00 0c 80 12 00 00 01 00 a5 00 44 01

    This seems to be sent periodically by the official software.
    Might not be strictly required to update RAMT, but included here in case.
    """
    payload = bytes.fromhex("00 0c 80 12 00 00 01 00 a5 00 44 01")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        print(f"[INFO] Sending heartbeat to {ip}:{port}: {payload.hex(' ')}")
        sock.sendto(payload, (ip, port))
        print("[INFO] Heartbeat sent.")
    finally:
        sock.close()


def main():
    parser = argparse.ArgumentParser(
        description="Send UDP commands to TF-F6 / PowerLED controller."
    )
    parser.add_argument(
        "command",
        nargs="?",
        help='Command to send, e.g. "*#1RAMT1,4011Hello0000"',
    )
    parser.add_argument(
        "--ip",
        default="192.168.1.252",
        help="Controller IP address (default: 192.168.1.252)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5959,
        help="Controller UDP port (default: 5959)",
    )
    parser.add_argument(
        "--add-crlf",
        action="store_true",
        help="Append \\r\\n to the command payload (default: off).",
    )
    parser.add_argument(
        "--heartbeat",
        action="store_true",
        help="Send only the 12-byte heartbeat packet (no ASCII command).",
    )

    args = parser.parse_args()

    if args.heartbeat:
        # Just send the magic 12-byte UDP frame
        send_heartbeat(args.ip, args.port)
    else:
        if not args.command:
            parser.error("You must provide a command, or use --heartbeat.")
        send_udp_command(args.ip, args.port, args.command, add_crlf=args.add_crlf)


if __name__ == "__main__":
    main()
