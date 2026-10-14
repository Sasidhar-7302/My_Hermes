#!/usr/bin/env bash
echo "Waking Hermes PC (00:13:EF:60:04:42)..."
python3 -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1); [s.sendto(b'\xFF'*6 + bytes.fromhex(m.replace(':',''))*16, (b, 9)) for m in ['00:13:EF:60:04:42','04:42:1A:EA:BF:E7'] for b in ['10.0.0.255','255.255.255.255']]"
echo "Magic packets sent successfully!"
