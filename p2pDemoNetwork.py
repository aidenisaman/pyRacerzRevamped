"""P2P demo: LAN broadcast or relay-assisted for cross-subnet play.

Default: broadcast on LAN (same subnet only).
Relay mode: pass --relay host[:port] to tunnel through a TCP relay so
peers on different subnets can see each other.

Arrow keys move your box; remote boxes show up in green.
"""

import json
import random
import socket
import sys
import time
import argparse
from typing import Optional, Tuple
from dataclasses import dataclass

import pygame


WINDOW_SIZE = (800, 600)
BG_COLOR = (15, 18, 25)
LOCAL_COLOR = (90, 180, 255)
REMOTE_COLOR = (120, 220, 140)

# Networking settings
BROADCAST_ADDR = "<broadcast>"
PORT = 50050
RELAY_PORT_DEFAULT = 50051
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


def connect_relay(host: str, port: int) -> socket.socket:
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.setblocking(False)
	s.connect_ex((host, port))  # non-blocking connect
	return s


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


def send_state_udp(sock: socket.socket, player_id: str, player: PlayerState) -> None:
	payload = {"id": player_id, "x": player.x, "y": player.y}
	sock.sendto(json.dumps(payload).encode("utf-8"), (BROADCAST_ADDR, PORT))


def send_state_relay(sock: socket.socket, player_id: str, player: PlayerState) -> None:
	payload = {"id": player_id, "x": player.x, "y": player.y}
	data = (json.dumps(payload) + "\n").encode("utf-8")
	try:
		sock.sendall(data)
	except (BlockingIOError, BrokenPipeError):
		pass


def receive_peers_udp(sock: socket.socket, player_id: str, peers: dict[str, Peer], now: float) -> None:
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


def receive_peers_relay(sock: socket.socket, player_id: str, peers: dict[str, Peer], now: float, buffer: bytearray) -> None:
	try:
		chunk = sock.recv(4096)
		if not chunk:
			return
		buffer.extend(chunk)
	except BlockingIOError:
		pass

	while b"\n" in buffer:
		line, _, rest = buffer.partition(b"\n")
		buffer[:] = rest
		if not line:
			continue
		try:
			msg = json.loads(line.decode("utf-8"))
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


def parse_args() -> Tuple[Optional[str], int]:
	parser = argparse.ArgumentParser(description="P2P demo: LAN or relay")
	parser.add_argument("--relay", help="relay host[:port] to bridge subnets", default=None)
	args = parser.parse_args()
	if not args.relay:
		return None, RELAY_PORT_DEFAULT
	if ":" in args.relay:
		host, port_str = args.relay.split(":", 1)
		return host, int(port_str)
	return args.relay, RELAY_PORT_DEFAULT


def main() -> int:
	pygame.init()
	screen = pygame.display.set_mode(WINDOW_SIZE)
	pygame.display.set_caption("P2P Demo")

	clock = pygame.time.Clock()
	player = PlayerState(
		x=(WINDOW_SIZE[0] - 48) / 2,
		y=(WINDOW_SIZE[1] - 48) / 2,
	)

	relay_host, relay_port = parse_args()
	use_relay = relay_host is not None

	player_id = hex(random.getrandbits(32))[2:]
	peers: dict[str, Peer] = {}
	if use_relay:
		sock = connect_relay(relay_host, relay_port)
		recv_buffer = bytearray()
	else:
		sock = make_socket()
		recv_buffer = None  # type: ignore
	last_send = 0.0

	running = True
	while running:
		now = time.time()
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False

		handle_input(player)

		if now - last_send >= SEND_INTERVAL:
			if use_relay:
				send_state_relay(sock, player_id, player)
			else:
				send_state_udp(sock, player_id, player)
			last_send = now

		if use_relay:
			receive_peers_relay(sock, player_id, peers, now, recv_buffer)  # type: ignore
		else:
			receive_peers_udp(sock, player_id, peers, now)

		draw(screen, player, peers)
		clock.tick(60)

	sock.close()
	pygame.quit()
	return 0


if __name__ == "__main__":
	sys.exit(main())