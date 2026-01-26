"""P2P demo: broadcast your box position, render peers.

Run this script on two + machines on the same network. Each instance
broadcasts its position over UDP and listens for others. Arrow keys move
your box; remote boxes show up in green.
"""

import json
import random
import socket
import sys
import time
from dataclasses import dataclass

import pygame


WINDOW_SIZE = (800, 600)
BG_COLOR = (15, 18, 25)
LOCAL_COLOR = (90, 180, 255)
REMOTE_COLOR = (120, 220, 140)

# Networking settings
BROADCAST_ADDR = "<broadcast>"
PORT = 50050
SEND_INTERVAL = 0.05  # seconds between state broadcasts
PEER_TIMEOUT = 3.0    # drop peers we have not heard from


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


@dataclass
class Peer:
	x: float
	y: float
	last_seen: float
	size: int = 48

	def rect(self) -> pygame.Rect:
		return pygame.Rect(int(self.x), int(self.y), self.size, self.size)


def make_socket() -> socket.socket:
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
	sock.setblocking(False)
	sock.bind(("", PORT))  # listen on all interfaces
	return sock


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


def send_state(sock: socket.socket, player_id: str, player: PlayerState, now: float) -> None:
	payload = {
		"id": player_id,
		"x": player.x,
		"y": player.y,
	}
	sock.sendto(json.dumps(payload).encode("utf-8"), (BROADCAST_ADDR, PORT))


def receive_peers(sock: socket.socket, player_id: str, peers: dict[str, Peer], now: float) -> None:
	while True:
		try:
			data, _ = sock.recvfrom(1024)
		except BlockingIOError:
			break
		try:
			msg = json.loads(data.decode("utf-8"))
			peer_id = msg.get("id")
			if peer_id is None or peer_id == player_id:
				continue
			x = float(msg.get("x", 0))
			y = float(msg.get("y", 0))
			peers[peer_id] = Peer(x=x, y=y, last_seen=now)
		except Exception:
			continue

	stale = [pid for pid, peer in peers.items() if now - peer.last_seen > PEER_TIMEOUT]
	for pid in stale:
		peers.pop(pid, None)


def draw(screen: pygame.Surface, player: PlayerState, peers: dict[str, Peer]) -> None:
	screen.fill(BG_COLOR)
	pygame.draw.rect(screen, LOCAL_COLOR, player.rect(), border_radius=6)
	for peer in peers.values():
		pygame.draw.rect(screen, REMOTE_COLOR, peer.rect(), border_radius=6)
	pygame.display.flip()


def main() -> int:
	pygame.init()
	screen = pygame.display.set_mode(WINDOW_SIZE)
	pygame.display.set_caption("P2P Demo")

	clock = pygame.time.Clock()
	player = PlayerState(
		x=(WINDOW_SIZE[0] - 48) / 2,
		y=(WINDOW_SIZE[1] - 48) / 2,
	)

	player_id = hex(random.getrandbits(32))[2:]
	peers: dict[str, Peer] = {}
	sock = make_socket()
	last_send = 0.0

	running = True
	while running:
		now = time.time()
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False

		handle_input(player)

		if now - last_send >= SEND_INTERVAL:
			send_state(sock, player_id, player, now)
			last_send = now

		receive_peers(sock, player_id, peers, now)
		draw(screen, player, peers)
		clock.tick(60)

	sock.close()
	pygame.quit()
	return 0


if __name__ == "__main__":
	sys.exit(main())