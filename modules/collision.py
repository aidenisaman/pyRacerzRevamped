# Copyright (C) 2005  Jujucece <jujucece@gmail.com>
#
# This file is part of pyRacerz.
#
# pyRacerz is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# pyRacerz is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyRacerz; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""Broad-phase 2-D collision detection via a uniform spatial grid.

Only object pairs that share at least one grid cell are surfaced as
*candidates* for the more expensive narrow-phase rect checks, cutting the
O(n²) pair count for objects that are far apart on the track.

Typical use inside the game loop::

    # Create once before the race loop (cell_size ~2× the car's sizeRect):
    grid = SpatialGrid(cell_size=int(64 * misc.zoom))

    # Inside the loop, rebuild and iterate over candidate pairs only:
    grid.rebuild(list_player, get_rect=lambda p: p.car.rect)
    for a, b in grid.candidate_pairs():
        _narrow_phase(a, b)   # process a→b direction
        _narrow_phase(b, a)   # process b→a direction (symmetric response)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Iterable, Iterator


class SpatialGrid:
  """Uniform spatial hash-grid for broad-phase 2-D collision detection.

  Objects are inserted by their axis-aligned bounding rectangle (AABB).
  Only pairs that share at least one cell are surfaced as *candidates* for
  the more expensive narrow-phase check, cutting the O(n²) pair count for
  objects that are far apart.

  Parameters
  ----------
  cell_size:
      Edge length (in pixels) of each square grid cell.  Choosing a value
      roughly 2–3× the largest object diameter keeps each object in at most
      four cells, which is optimal.
  """

  def __init__(self, cell_size: int) -> None:
    if cell_size <= 0:
      raise ValueError(f"cell_size must be > 0, got {cell_size!r}")
    self._cell: int = cell_size
    self._buckets: defaultdict[tuple[int, int], list] = defaultdict(list)
    self._objects: list = []

  # ------------------------------------------------------------------
  # Private helpers
  # ------------------------------------------------------------------

  def _cells_for_rect(self, rect) -> Iterator[tuple[int, int]]:
    """Yield every (col, row) cell that *rect* overlaps."""
    x0 = rect.left // self._cell
    y0 = rect.top // self._cell
    x1 = rect.right // self._cell
    y1 = rect.bottom // self._cell
    for cx in range(x0, x1 + 1):
      for cy in range(y0, y1 + 1):
        yield cx, cy

  # ------------------------------------------------------------------
  # Public API
  # ------------------------------------------------------------------

  def rebuild(
    self,
    objects: Iterable,
    get_rect: Callable | None = None,
  ) -> None:
    """Rebuild the grid from *objects*.

    Clears all previous contents before inserting the new objects.

    Parameters
    ----------
    objects:
        Any iterable of objects.  By default each object must have a
        ``.rect`` attribute (a :class:`pygame.Rect`).
    get_rect:
        Optional callable ``get_rect(obj) -> pygame.Rect`` that extracts
        the bounding rectangle from an object.  Overrides the default
        ``.rect`` attribute access.
    """
    self._buckets.clear()
    self._objects = list(objects)
    if get_rect is None:
      _get = lambda obj: obj.rect  # noqa: E731
    else:
      _get = get_rect
    for obj in self._objects:
      for cell in self._cells_for_rect(_get(obj)):
        self._buckets[cell].append(obj)

  def candidate_pairs(self) -> Iterator[tuple]:
    """Yield unique unordered ``(a, b)`` candidate pairs.

    A pair is yielded if and only if the two objects share at least one
    grid cell.  Each pair appears at most once (identity-based
    deduplication via ``id``), so the caller is responsible for
    processing both directions of the collision response where needed.
    """
    seen: set[tuple[int, int]] = set()
    for bucket in self._buckets.values():
      for i, a in enumerate(bucket):
        for b in bucket[i + 1:]:
          low = id(a) if id(a) < id(b) else id(b)
          high = id(b) if id(a) < id(b) else id(a)
          key = (low, high)
          if key not in seen:
            seen.add(key)
            yield a, b
