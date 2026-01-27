"""Minimal pygame box-mover demo.

Arrow keys move a box around the window. This keeps the architecture
simple so we can later drop in P2P sync (send/receive player states
over LAN and render each remote box).
"""

import sys
from dataclasses import dataclass

import pygame


WINDOW_SIZE = (800, 600)
BG_COLOR = (15, 18, 25)
LOCAL_COLOR = (90, 180, 255)


@dataclass
class PlayerState:
	x: float
	y: float
	size: int = 48
	speed: float = 5.0

	def move(self, dx: float, dy: float) -> None:
		self.x += dx * self.speed
		self.y += dy * self.speed
		# Clamp to window bounds so we do not wander off-screen.
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
	# Normalize diagonal speed to keep movement consistent.
	if dx and dy:
		dx *= 0.7071
		dy *= 0.7071
	player.move(dx, dy)


def draw(screen: pygame.Surface, player: PlayerState) -> None:
	screen.fill(BG_COLOR)
	pygame.draw.rect(screen, LOCAL_COLOR, player.rect(), border_radius=6)
	pygame.display.flip()


def main() -> int:
	pygame.init()
	screen = pygame.display.set_mode(WINDOW_SIZE)
	pygame.display.set_caption("P2P Demo: Local Box")

	clock = pygame.time.Clock()
	player = PlayerState(
		x=(WINDOW_SIZE[0] - 48) / 2,
		y=(WINDOW_SIZE[1] - 48) / 2,
	)

	running = True
	while running:
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				running = False

		handle_input(player)
		draw(screen, player)
		clock.tick(60)

	pygame.quit()
	return 0


if __name__ == "__main__":
	sys.exit(main())
