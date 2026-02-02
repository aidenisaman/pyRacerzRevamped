"""TCP relay server for the client demo.

Accepts TCP connections, ingests per-client position updates, and
broadcasts the aggregated world state to all connected clients.
"""

import json
import selectors
import socket
import time
from typing import Dict, Set


SERVER_HOST = "0.0.0.0"
SERVER_PORT = 50051
BROADCAST_INTERVAL = 0.05
CLIENT_TIMEOUT = 3.0


ClientMap = Dict[socket.socket, Dict[str, object]]
PlayerMap = Dict[str, Dict[str, object]]


def accept_client(listen_sock: socket.socket, selector: selectors.BaseSelector, clients: ClientMap) -> None:
    conn, addr = listen_sock.accept()
    conn.setblocking(False)
    clients[conn] = {"addr": addr, "buffer": bytearray(), "ids": set()}
    selector.register(conn, selectors.EVENT_READ)
    print(f"Client connected from {addr}")


def drop_client(sock: socket.socket, selector: selectors.BaseSelector, clients: ClientMap, players: PlayerMap) -> None:
    info = clients.pop(sock, None)
    try:
        selector.unregister(sock)
    except Exception:
        pass
    try:
        sock.close()
    except Exception:
        pass
    if info:
        for pid in info.get("ids", set()):
            players.pop(pid, None)
        print(f"Client {info.get('addr')} disconnected")


def process_messages(sock: socket.socket, clients: ClientMap, players: PlayerMap) -> bool:
    buffer: bytearray = clients[sock]["buffer"]  # type: ignore
    try:
        data = sock.recv(4096)
    except BlockingIOError:
        return True
    except ConnectionResetError:
        return False

    if data == b"":
        return False

    buffer.extend(data)
    while b"\n" in buffer:
        line, _, rest = buffer.partition(b"\n")
        buffer[:] = rest
        if not line:
            continue
        try:
            msg = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue
        if msg.get("type") != "state":
            continue
        pid = msg.get("id")
        if pid is None:
            continue
        try:
            pid_str = str(pid)
            x = float(msg.get("x", 0.0))
            y = float(msg.get("y", 0.0))
        except (TypeError, ValueError):
            continue
        players[pid_str] = {"x": x, "y": y, "last_seen": time.time()}
        ids: Set[str] = clients[sock].get("ids", set())  # type: ignore
        ids.add(pid_str)
        clients[sock]["ids"] = ids
    return True


def broadcast_world(clients: ClientMap, players: PlayerMap) -> None:
    now = time.time()
    active_players = {
        pid: {"x": info["x"], "y": info["y"]}
        for pid, info in players.items()
        if now - info.get("last_seen", 0) <= CLIENT_TIMEOUT
    }
    players_to_drop = [pid for pid, info in players.items() if now - info.get("last_seen", 0) > CLIENT_TIMEOUT]
    for pid in players_to_drop:
        players.pop(pid, None)

    if not active_players:
        return

    payload = json.dumps({"type": "world", "players": active_players}).encode("utf-8") + b"\n"
    for sock in list(clients.keys()):
        try:
            sock.sendall(payload)
        except (BlockingIOError, BrokenPipeError, ConnectionResetError):
            continue


def run_server(host: str = SERVER_HOST, port: int = SERVER_PORT) -> None:
    listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listen_sock.bind((host, port))
    listen_sock.listen()
    listen_sock.setblocking(False)

    selector = selectors.DefaultSelector()
    selector.register(listen_sock, selectors.EVENT_READ)

    clients: ClientMap = {}
    players: PlayerMap = {}
    last_broadcast = time.time()

    print(f"Server listening on {host}:{port}")
    try:
        while True:
            events = selector.select(timeout=0.02)
            for key, _ in events:
                if key.fileobj is listen_sock:
                    accept_client(listen_sock, selector, clients)
                    continue
                sock = key.fileobj  # type: ignore
                alive = process_messages(sock, clients, players)
                if not alive:
                    drop_client(sock, selector, clients, players)

            now = time.time()
            if now - last_broadcast >= BROADCAST_INTERVAL:
                broadcast_world(clients, players)
                last_broadcast = now
    except KeyboardInterrupt:
        print("Shutting down server")
    finally:
        for sock in list(clients.keys()):
            drop_client(sock, selector, clients, players)
        selector.unregister(listen_sock)
        listen_sock.close()


if __name__ == "__main__":
    run_server()
