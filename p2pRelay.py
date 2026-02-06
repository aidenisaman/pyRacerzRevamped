"""Tiny TCP relay for the P2P demo.

Listens on TCP port 50051 (default) and forwards each JSON line it
receives to all other connected clients. Use with:

    python p2pRelay.py [--port 50051]

Then run clients with:

    python p2pDemoNetwork.py --relay RELAY_HOST[:PORT]
"""

import argparse
import selectors
import socket
import sys
from typing import Dict


def accept(sock: socket.socket, sel: selectors.BaseSelector) -> None:
    conn, addr = sock.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, data=bytearray())
    print(f"Client connected from {addr}")


def broadcast(sel: selectors.BaseSelector, sender: socket.socket, data: bytes) -> None:
    for key in sel.get_map().values():
        if key.fileobj is sender or key.data is None:
            continue
        try:
            key.fileobj.sendall(data)
        except Exception:
            try:
                sel.unregister(key.fileobj)
                key.fileobj.close()
            except Exception:
                pass


def serve(port: int) -> int:
    sel = selectors.DefaultSelector()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("", port))
    srv.listen()
    srv.setblocking(False)
    sel.register(srv, selectors.EVENT_READ, data=None)

    print(f"Relay listening on 0.0.0.0:{port}")

    try:
        while True:
            events = sel.select(timeout=1.0)
            for key, mask in events:
                if key.data is None:  # server socket
                    accept(key.fileobj, sel)
                else:  # client socket
                    conn = key.fileobj
                    buf: bytearray = key.data
                    try:
                        chunk = conn.recv(4096)
                    except ConnectionResetError:
                        chunk = b""
                    if not chunk:
                        print("Client disconnected")
                        sel.unregister(conn)
                        conn.close()
                        continue
                    buf.extend(chunk)
                    while b"\n" in buf:
                        line, _, rest = buf.partition(b"\n")
                        buf[:] = rest
                        if line:
                            broadcast(sel, conn, line + b"\n")
    except KeyboardInterrupt:
        print("\nShutting down relay...")
    finally:
        for key in list(sel.get_map().values()):
            try:
                sel.unregister(key.fileobj)
                key.fileobj.close()
            except Exception:
                pass
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Tiny TCP relay for P2P demo")
    parser.add_argument("--port", type=int, default=50051, help="TCP port to listen on")
    args = parser.parse_args()
    return serve(args.port)


if __name__ == "__main__":
    sys.exit(main())
