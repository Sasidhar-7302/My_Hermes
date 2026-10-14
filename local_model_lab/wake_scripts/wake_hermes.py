# -*- coding: utf-8 -*-
import socket

MACS = ["00:13:EF:60:04:42", "04:42:1A:EA:BF:E7"]
BROADCASTS = ["10.0.0.255", "255.255.255.255"]
PORTS = [9, 7]

def wake():
    print("[Hermes WoL] Waking Hermes PC...")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for mac in MACS:
            cleaned = mac.replace(":", "").replace("-", "")
            packet = b"\xFF" * 6 + (bytes.fromhex(cleaned) * 16)
            for b_ip in BROADCASTS:
                for port in PORTS:
                    s.sendto(packet, (b_ip, port))
            print(f"  -> Sent magic packet for MAC {mac}")
    print("[Hermes WoL] Packets broadcasted. PC waking up in ~10-15s.")

if __name__ == "__main__":
    wake()
