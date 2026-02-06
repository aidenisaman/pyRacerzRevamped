import json
import random
import socket
import time
from dataclasses import dataclass
from typing import Dict, Tuple

import pygame
import pygame_textinput

"""Overall client structure idea
open pygame window that prompts user to type ip address of the server
After user inputs the address, swap to the game window and connect to the server
Then enter the main loop where the users is moving the block around
The user will send their position to the server
The server will then broadcast the positions of all clients to each client
and each client will update the positions of the blocks accordingly
"""


WINDOW_SIZE = (800, 600)
BG_COLOR = (15, 18, 25)
LOCAL_COLOR = (90, 180, 255)
REMOTE_COLOR = (120, 220, 140)
SERVER_PORT = 50051
SEND_INTERVAL = 0.05
PING_INTERVAL = 1.0
DISCONNECT_TIMEOUT = 3.0


@dataclass
class PlayerState:
    x: float
    y: float
    size: int = 48
    speed: float = 5.0

    def move(self, dx: float, dy: float) -> None:
        self.x += dx * self.speed
        self.y += dy * self.speed
        self.x = max(0, min(self.x, WINDOW_SIZE[0] - self.size))
        self.y = max(0, min(self.y, WINDOW_SIZE[1] - self.size))

    def rect(self) -> pygame.Rect:
        return pygame.Rect(int(self.x), int(self.y), self.size, self.size)


def handle_input(player: PlayerState) -> None:
    dx = dy = 0
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_RIGHT]:
        dx += 1
    if keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_DOWN]:
        dy += 1
    if dx and dy:
        dx *= 0.7071
        dy *= 0.7071
    player.move(dx, dy)


def send_state(sock: socket.socket, player_id: str, player: PlayerState) -> bool:
    payload = {"type": "state", "id": player_id, "x": player.x, "y": player.y}
    data = (json.dumps(payload) + "\n").encode("utf-8")
    try:
        sock.sendall(data)
        return True
    except (BlockingIOError, BrokenPipeError):
        return False


def send_ping(sock: socket.socket, player_id: str) -> bool:
    payload = {"type": "ping", "id": player_id, "t": time.time()}
    data = (json.dumps(payload) + "\n").encode("utf-8")
    try:
        sock.sendall(data)
        return True
    except (BlockingIOError, BrokenPipeError):
        return False


def receive_world(
    sock: socket.socket,
    player_id: str,
    peers: Dict[str, Tuple[float, float]],
    buffer: bytearray,
    last_pong: float,
) -> Tuple[bool, float]:
    try:
        chunk = sock.recv(4096)
        if chunk == b"":
            return False, last_pong
        buffer.extend(chunk)
    except BlockingIOError:
        pass

    while b"\n" in buffer:
        line, _, rest = buffer.partition(b"\n")
        buffer[:] = rest
        if not line:
            continue
        try:
            message = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError:
            continue
        mtype = message.get("type")
        if mtype == "world":
            players = message.get("players", {})
            for pid, state in players.items():
                if pid == player_id:
                    continue
                try:
                    peers[pid] = (float(state.get("x", 0.0)), float(state.get("y", 0.0)))
                except (TypeError, ValueError):
                    continue
        elif mtype == "pong":
            last_pong = time.time()
    return True, last_pong


def draw(screen: pygame.Surface, player: PlayerState, peers: Dict[str, Tuple[float, float]]) -> None:
    screen.fill(BG_COLOR)
    pygame.draw.rect(screen, LOCAL_COLOR, player.rect(), border_radius=6)
    for x, y in peers.values():
        rect = pygame.Rect(int(x), int(y), player.size, player.size)
        pygame.draw.rect(screen, REMOTE_COLOR, rect, border_radius=6)
    pygame.display.flip()


def connect_to_server() -> str:
    pygame.init()
    ip = ""
    # Create TextInput-object
    manager1 = pygame_textinput.TextInputManager(validator=lambda input: len(input) <= 17)
    textinput = pygame_textinput.TextInputVisualizer(manager=manager1, font_color=(128, 0, 128))

    screen = pygame.display.set_mode((1000, 200))
    pygame.display.set_caption("Enter Server IP Address")
    clock = pygame.time.Clock()

    while True:
        screen.fill((0, 0, 0))
        events = pygame.event.get()

        # Feed it with events every frame
        textinput.update(events)
        # Blit its surface onto the screen
        screen.blit(textinput.surface, (10, 10))

        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                ip = textinput.value.strip()
                break

        pygame.display.update()
        clock.tick(30)
        if ip:
            pygame.quit()
            return ip


def main_game_loop(server_address: str) -> None:
    host, port = (server_address.split(":", 1) + [str(SERVER_PORT)])[:2]
    port_int = int(port) if port else SERVER_PORT

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((host, port_int))
    except OSError as exc:
        print(f"Failed to connect to server: {exc}")
        return
    sock.setblocking(False)

    pygame.init()
    screen = pygame.display.set_mode(WINDOW_SIZE)
    pygame.display.set_caption("Client-Server Demo")
    clock = pygame.time.Clock()

    player = PlayerState(x=(WINDOW_SIZE[0] - 48) / 2, y=(WINDOW_SIZE[1] - 48) / 2)
    player_id = hex(random.getrandbits(32))[2:]
    peers: Dict[str, Tuple[float, float]] = {}
    recv_buffer = bytearray()
    last_send = 0.0
    last_ping = 0.0
    last_pong = time.time()
    running = True

    while running:
        now = time.time()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        handle_input(player)

        if now - last_send >= SEND_INTERVAL:
            if not send_state(sock, player_id, player):
                running = False
                continue
            last_send = now

        if now - last_ping >= PING_INTERVAL:
            if not send_ping(sock, player_id):
                running = False
                continue
            last_ping = now

        alive, last_pong = receive_world(sock, player_id, peers, recv_buffer, last_pong)
        if not alive:
            running = False
            continue

        if now - last_pong > DISCONNECT_TIMEOUT:
            print("Lost connection to server (timeout)")
            running = False
            continue

        draw(screen, player, peers)
        clock.tick(60)

    sock.close()
    pygame.quit()


if __name__ == "__main__":
    server = connect_to_server()
    main_game_loop(server)