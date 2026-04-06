from dataclasses import dataclass
from dataclasses import field
from typing import Dict, List, Set, Tuple
from collections import deque
import heapq

from . import misc


Vector2 = Tuple[float, float]


@dataclass
class TrackModel:
  """Stores checkpoint centroid positions indexed by their red-channel ID.

  The AI uses this to look up where the next checkpoint physically is
  on the map and steer directly toward it.
  """
  # Map from checkpoint red value (16, 32, 48...) to (x, y) centroid.
  checkpoint_centroids: Dict[int, Tuple[float, float]]
  # Total number of checkpoints on this track.
  nb_checkpoints: int
  # Whether this track runs in reverse.
  reverse: int
  # Track name, useful for per-track caution profiles.
  name: str = ""
  # Ordered checkpoint ids in lap order.
  checkpoint_ids: List[int] = field(default_factory=list)
  # Planner grid tile size in pixels.
  tile_size: int = 4
  # Planner grid dimensions.
  grid_w: int = 0
  grid_h: int = 0
  # Drivable road tiles (tx, ty), extracted from green channel == 255.
  road_tiles: Set[Tuple[int, int]] = field(default_factory=set)
  # Checkpoint tiles by checkpoint id.
  checkpoint_tiles: Dict[int, Set[Tuple[int, int]]] = field(default_factory=dict)
  # Planned segment path: start checkpoint id -> list of tiles to next checkpoint.
  checkpoint_paths: Dict[int, List[Tuple[int, int]]] = field(default_factory=dict)
  # Road tiles that belong to the optional underpass/blue overlay.
  blue_tiles: Set[Tuple[int, int]] = field(default_factory=set)
  # Blue-zone regions with unlock checkpoint metadata.
  blue_regions: List[dict] = field(default_factory=list)
  # Segment index -> allowed drivable tile mask for that segment.
  segment_masks: Dict[int, Set[Tuple[int, int]]] = field(default_factory=dict)
  # Segment index -> precomputed flow vectors for that segment.
  segment_flow_fields: Dict[int, Dict[Tuple[int, int], Tuple[float, float]]] = field(default_factory=dict)


class TrackModelCache:
  """Lazily builds and caches checkpoint centroid maps.

  The AI navigates by targeting one checkpoint at a time:
  it reads the bot's lastCheckpoint to know its progress,
  computes the next checkpoint ID, looks up the centroid,
  and steers directly toward it.
  """

  def __init__(self):
    self._cache: Dict[str, TrackModel] = {}

  def get_for_track(self, track_obj):
    key = self._track_key(track_obj)
    if key not in self._cache:
      self._cache[key] = self._build(track_obj)
    return self._cache[key]

  def _track_key(self, track_obj):
    reverse = getattr(track_obj, "reverse", 0)
    name = getattr(track_obj, "name", "unknown")
    return "%s:%s" % (name, reverse)

  def _build(self, track_obj):
    track_f = track_obj.trackF
    bot_surface = getattr(track_obj, "trackF_bot_nav", None) or track_f
    nb = int(getattr(track_obj, "nbCheckpoint", 0))
    reverse = int(getattr(track_obj, "reverse", 0))

    # Scan every pixel to find checkpoint centroids from anti-aliased paint.
    width = track_f.get_width()
    height = track_f.get_height()

    all_cp_ids = set(16 * i for i in range(1, nb + 1))

    sums: Dict[int, List[float]] = {}
    counts: Dict[int, int] = {}
    for y in range(height):
      for x in range(width):
        pix = track_f.get_at((x, y))
        r = int(pix[0])
        g = int(pix[1])
        b = int(pix[2])
        if g < 200 or b > 30 or r < 16:
          continue
        cp_id = int(round(r / 16.0) * 16)
        if cp_id not in all_cp_ids:
          continue
        if cp_id not in sums:
          sums[cp_id] = [0.0, 0.0]
          counts[cp_id] = 0
        sums[cp_id][0] += x
        sums[cp_id][1] += y
        counts[cp_id] += 1

    centroids: Dict[int, Tuple[float, float]] = {}
    for cp_id in all_cp_ids:
      if cp_id in counts and counts[cp_id] > 0:
        centroids[cp_id] = (sums[cp_id][0] / counts[cp_id], sums[cp_id][1] / counts[cp_id])

    tile_size = 4
    road_tiles_full, grid_w, grid_h = self._build_road_grid(
      bot_surface,
      tile_size,
      allow_cyan=True,
      allow_blue=True,
    )
    road_tiles_no_cyan, _, _ = self._build_road_grid(
      bot_surface,
      tile_size,
      allow_cyan=False,
      allow_blue=False,
    )
    checkpoint_tiles = self._build_checkpoint_tiles(
      track_f,
      all_cp_ids,
      tile_size,
      road_tiles_full,
    )
    checkpoint_ids = self._build_checkpoint_order(nb, reverse)
    blue_tiles = self._build_blue_tiles(bot_surface, tile_size, road_tiles_full)
    checkpoint_paths = self._build_checkpoint_paths(checkpoint_ids, checkpoint_tiles, road_tiles_full, grid_w, grid_h)
    blue_regions = self._build_blue_regions(blue_tiles, checkpoint_ids, centroids, tile_size)
    self._annotate_blue_region_segments(
      blue_regions,
      checkpoint_ids,
      checkpoint_tiles,
      road_tiles_full,
      blue_tiles,
    )
    segment_masks = self._build_segment_masks(
      checkpoint_ids,
      checkpoint_paths,
      checkpoint_tiles,
      centroids,
      tile_size,
      road_tiles_full,
      road_tiles_no_cyan,
      blue_tiles,
      blue_regions,
      grid_w,
      grid_h,
    )
    segment_flow_fields = self._build_segment_flow_fields(
      checkpoint_ids,
      checkpoint_tiles,
      centroids,
      segment_masks,
      blue_tiles,
      tile_size,
      grid_w,
      grid_h,
    )

    return TrackModel(
      checkpoint_centroids=centroids,
      nb_checkpoints=nb,
      reverse=reverse,
      name=getattr(track_obj, "name", ""),
      checkpoint_ids=checkpoint_ids,
      tile_size=tile_size,
      grid_w=grid_w,
      grid_h=grid_h,
      road_tiles=road_tiles_full,
      checkpoint_tiles=checkpoint_tiles,
      checkpoint_paths=checkpoint_paths,
      blue_tiles=blue_tiles,
      blue_regions=blue_regions,
      segment_masks=segment_masks,
      segment_flow_fields=segment_flow_fields,
    )

  def _build_road_grid(self, track_f, tile_size, allow_cyan=True, allow_blue=True):
    width = track_f.get_width()
    height = track_f.get_height()
    grid_w = max(1, width // tile_size)
    grid_h = max(1, height // tile_size)
    road_tiles: Set[Tuple[int, int]] = set()

    # One-time load per track: exhaustive tile scan is acceptable.
    for ty in range(grid_h):
      y0 = ty * tile_size
      y1 = min(height, y0 + tile_size)
      for tx in range(grid_w):
        x0 = tx * tile_size
        x1 = min(width, x0 + tile_size)
        found = False
        for y in range(y0, y1):
          for x in range(x0, x1):
            if self._is_drivable_pixel(
              track_f.get_at((x, y)),
              allow_cyan=allow_cyan,
              allow_blue=allow_blue,
            ):
              road_tiles.add((tx, ty))
              found = True
              break
          if found:
            break

    return road_tiles, grid_w, grid_h

  def _is_drivable_pixel(self, pix, allow_cyan=True, allow_blue=True):
    r = int(pix[0])
    g = int(pix[1])
    b = int(pix[2])

    # Green road surface.
    green_road = (g > 150 and r < 120 and b < 150)
    # Cyan underpass road surface (high green + high blue).
    cyan_road = allow_cyan and (g > 150 and b > 150 and r < 140)
    # Canonical checkpoint paint over road in this project.
    checkpoint_over_road = (g > 150 and r > 0 and (r % 16 == 0))

    # Defensive fallbacks for alternate assets/debug renders.
    white = (r > 200 and g > 200 and b > 200)
    checkpoint_red = (r > 200 and g < 80 and b < 80)
    underpass_blue = allow_blue and (b > 200 and r < 140 and g > 120)

    return green_road or cyan_road or checkpoint_over_road or white or checkpoint_red or underpass_blue

  def _is_underpass_pixel(self, pix, blue_threshold=200):
    r = int(pix[0])
    g = int(pix[1])
    b = int(pix[2])
    return (b >= blue_threshold and g > 150 and r < 140)

  def _build_checkpoint_tiles(self, track_f, cp_ids, tile_size, road_tiles):
    """Find checkpoint lines from anti-aliased yellow paint and map to road tiles."""
    checkpoint_tiles: Dict[int, Set[Tuple[int, int]]] = {cp: set() for cp in cp_ids}
    width = track_f.get_width()
    height = track_f.get_height()

    # First pass: collect checkpoint-painted pixels and map to nearby road tiles.

    for y in range(height):
      for x in range(width):
        pix = track_f.get_at((x, y))
        r = int(pix[0])
        g = int(pix[1])
        b = int(pix[2])

        # Yellow-green checkpoint paint can be anti-aliased and off exact ID values.
        if g < 200 or b > 30 or r < 16:
          continue
        cp_id = int(round(r / 16.0) * 16)
        if cp_id not in cp_ids:
          continue

        tx = x // tile_size
        ty = y // tile_size
        tile = (tx, ty)

        if tile in road_tiles:
          checkpoint_tiles[cp_id].add(tile)
          continue

        found = False
        for dy in range(-2, 3):
          for dx in range(-2, 3):
            n = (tx + dx, ty + dy)
            if n in road_tiles:
              checkpoint_tiles[cp_id].add(n)
              found = True
              break
          if found:
            break

    # Filter broad/noisy clusters down to line-like structures.
    clean: Dict[int, Set[Tuple[int, int]]] = {cp: set() for cp in cp_ids}
    for cp_id, tiles in checkpoint_tiles.items():
      if not tiles:
        continue

      xs = [t[0] for t in tiles]
      ys = [t[1] for t in tiles]
      x_range = max(xs) - min(xs)
      y_range = max(ys) - min(ys)

      # Keep obvious line-shaped sets directly.
      if x_range < 8 or y_range < 8:
        clean[cp_id] = tiles
        continue

      # Otherwise keep the tightest dominant band.
      from collections import Counter
      if x_range < y_range:
        x_counts = Counter(t[0] for t in tiles)
        best_x = x_counts.most_common(1)[0][0]
        clean[cp_id] = set(t for t in tiles if abs(t[0] - best_x) <= 3)
      else:
        y_counts = Counter(t[1] for t in tiles)
        best_y = y_counts.most_common(1)[0][0]
        clean[cp_id] = set(t for t in tiles if abs(t[1] - best_y) <= 3)

    return clean

  def _build_blue_tiles(self, track_f, tile_size, road_tiles, blue_threshold=200):
    blue_tiles: Set[Tuple[int, int]] = set()
    width = track_f.get_width()
    height = track_f.get_height()

    for y in range(height):
      for x in range(width):
        pix = track_f.get_at((x, y))
        if not self._is_underpass_pixel(pix, blue_threshold=blue_threshold):
          continue
        tile = (x // tile_size, y // tile_size)
        if tile in road_tiles:
          blue_tiles.add(tile)

    return blue_tiles

  def _build_blue_regions(self, blue_tiles, checkpoint_ids, checkpoint_centroids, tile_size):
    if not blue_tiles:
      return []

    cp_index = {cp_id: i for i, cp_id in enumerate(checkpoint_ids)}
    regions = []
    remaining = set(blue_tiles)
    rid = 0

    while remaining:
      start = next(iter(remaining))
      q = deque([start])
      remaining.remove(start)
      tiles = set([start])

      while q:
        cur = q.popleft()
        for nxt in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]), (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
          if nxt in remaining:
            remaining.remove(nxt)
            q.append(nxt)
            tiles.add(nxt)

      # Small regions are usually anti-aliased artifacts, keep them always passable.
      if len(tiles) <= 3:
        unlock_idx = 0
      else:
        cx = sum(t[0] for t in tiles) / float(len(tiles))
        cy = sum(t[1] for t in tiles) / float(len(tiles))
        world = ((cx + 0.5) * tile_size, (cy + 0.5) * tile_size)
        nearest_cp = None
        nearest_d2 = 10 ** 12
        for cp_id, cp_world in checkpoint_centroids.items():
          dx = cp_world[0] - world[0]
          dy = cp_world[1] - world[1]
          d2 = dx * dx + dy * dy
          if d2 < nearest_d2:
            nearest_d2 = d2
            nearest_cp = cp_id
        # Pre-unlock by one checkpoint so the lane is available before entry.
        # This avoids deadlocks when the nearest checkpoint lies inside/after
        # an underpass branch.
        unlock_idx = max(0, cp_index.get(nearest_cp, 0) - 1)

      regions.append({
        "id": rid,
        "tiles": tiles,
        "unlock_after_checkpoint": int(unlock_idx),
      })
      rid += 1

    return regions

  def _build_checkpoint_paths(self, checkpoint_ids, checkpoint_tiles, road_tiles, grid_w, grid_h):
    paths: Dict[int, List[Tuple[int, int]]] = {}
    if not checkpoint_ids:
      return paths

    for i, cp in enumerate(checkpoint_ids):
      nxt = checkpoint_ids[(i + 1) % len(checkpoint_ids)]
      starts = checkpoint_tiles.get(cp, set())
      goals = checkpoint_tiles.get(nxt, set())
      paths[cp] = self._bfs_tile_path(starts, goals, road_tiles, grid_w, grid_h)

    return paths

  def _annotate_blue_region_segments(self, blue_regions, checkpoint_ids, checkpoint_tiles, road_tiles, blue_tiles):
    if not blue_regions or not checkpoint_ids:
      return

    # Default metadata.
    for region in blue_regions:
      region["used_in_segment"] = []
      region["direction"] = "under"

    # A segment may use blue only if removing all blue disconnects its CP-to-CP road.
    road_no_blue = set(road_tiles)
    road_no_blue.difference_update(blue_tiles)

    for seg_idx, cp_id in enumerate(checkpoint_ids):
      next_cp = checkpoint_ids[(seg_idx + 1) % len(checkpoint_ids)]
      starts = checkpoint_tiles.get(cp_id, set())
      goals = checkpoint_tiles.get(next_cp, set())

      # If still connected without blue, block all blue for this segment.
      if self._segment_connected(road_no_blue, starts, goals):
        continue

      # Otherwise, only enable regions that restore connectivity.
      for region in blue_regions:
        test_mask = set(road_no_blue)
        test_mask.update(region.get("tiles", set()))
        if self._segment_connected(test_mask, starts, goals):
          region["used_in_segment"].append(seg_idx)

    # Lightweight direction tag for debugging: classify by region centroid vertical position.
    all_y = [tile[1] for region in blue_regions for tile in region.get("tiles", set())]
    mid_y = sum(all_y) / float(len(all_y)) if all_y else 0.0
    for region in blue_regions:
      if not region.get("tiles"):
        region["direction"] = "under"
        continue
      cy = sum(tile[1] for tile in region["tiles"]) / float(len(region["tiles"]))
      region["direction"] = "over" if cy < mid_y else "under"
      region["used_in_segment"] = sorted(set(region.get("used_in_segment", [])))

  def _dilate_tiles(self, seeds, radius, grid_w, grid_h):
    if radius <= 0:
      return set(seeds)
    out = set()
    for tile in seeds:
      tx, ty = tile
      for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
          if dx * dx + dy * dy > radius * radius:
            continue
          nx = tx + dx
          ny = ty + dy
          if nx < 0 or ny < 0 or nx >= grid_w or ny >= grid_h:
            continue
          out.add((nx, ny))
    return out

  def _erode_tiles(self, seeds, radius, valid_area):
    if radius <= 0:
      return set(seeds)
    seed_set = set(seeds)
    out = set()
    for tile in seed_set:
      if tile not in valid_area:
        continue
      tx, ty = tile
      keep = True
      for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
          if dx * dx + dy * dy > radius * radius:
            continue
          n = (tx + dx, ty + dy)
          if n not in valid_area:
            continue
          if n not in seed_set:
            keep = False
            break
        if not keep:
          break
      if keep:
        out.add(tile)
    return out

  def _close_and_fill_mask(self, mask, valid_area, grid_w, grid_h, allowed_tiles=None):
    if not mask:
      return set()

    if allowed_tiles is None:
      allowed = set(valid_area)
    else:
      allowed = set(valid_area).intersection(set(allowed_tiles))
    if not allowed:
      return set()

    # Morphological closing to bridge 1-tile cracks at color boundaries.
    dilated = self._dilate_tiles(mask, 1, grid_w, grid_h)
    dilated.intersection_update(allowed)
    closed = self._erode_tiles(dilated, 1, allowed)
    if not closed:
      closed = set(mask).intersection(allowed)

    # Fill tiny single-tile holes inside the valid corridor.
    hole_filled = set(closed)
    for tile in allowed:
      if tile in hole_filled:
        continue
      x, y = tile
      neighbors = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
      hit = 0
      for n in neighbors:
        if n in hole_filled:
          hit += 1
      if hit >= 3:
        hole_filled.add(tile)

    return hole_filled

  def _segment_connected(self, mask, starts, goals):
    if not starts or not goals or not mask:
      return False

    goal_set = set(goals)
    q = deque([s for s in starts if s in mask])
    if not q:
      return False
    seen = set(q)

    while q:
      cur = q.popleft()
      if cur in goal_set:
        return True
      for nxt in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]), (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
        if nxt in mask and nxt not in seen:
          seen.add(nxt)
          q.append(nxt)
    return False

  def _reachable_component(self, mask, starts):
    if not mask or not starts:
      return set()
    q = deque([s for s in starts if s in mask])
    if not q:
      return set()
    seen = set(q)
    while q:
      cur = q.popleft()
      for nxt in (
        (cur[0] + 1, cur[1]),
        (cur[0] - 1, cur[1]),
        (cur[0], cur[1] + 1),
        (cur[0], cur[1] - 1),
      ):
        if nxt in mask and nxt not in seen:
          seen.add(nxt)
          q.append(nxt)
    return seen

  def _components_touching_starts(self, mask, starts):
    starts_in = [s for s in starts if s in mask]
    if not starts_in:
      return []

    seen_global = set()
    components = []
    for s in starts_in:
      if s in seen_global:
        continue
      q = deque([s])
      comp = set([s])
      seen_global.add(s)
      while q:
        cur = q.popleft()
        for nxt in (
          (cur[0] + 1, cur[1]),
          (cur[0] - 1, cur[1]),
          (cur[0], cur[1] + 1),
          (cur[0], cur[1] - 1),
        ):
          if nxt in mask and nxt not in seen_global:
            seen_global.add(nxt)
            comp.add(nxt)
            q.append(nxt)
      components.append(comp)
    return components

  def _nearest_mask_tile(self, center, mask):
    if not mask:
      return None
    cx, cy = center
    best = None
    best_d2 = 10 ** 12
    for tile in mask:
      dx = tile[0] - cx
      dy = tile[1] - cy
      d2 = dx * dx + dy * dy
      if d2 < best_d2:
        best_d2 = d2
        best = tile
    return best

  def _smart_seed_from_checkpoint(self, start_tiles, base_mask, grid_w, grid_h, end_center_tile=None):
    if not start_tiles:
      return None

    xs = [t[0] for t in start_tiles]
    ys = [t[1] for t in start_tiles]
    cx = int(sum(xs) / float(len(xs)))
    cy = int(sum(ys) / float(len(ys)))
    cp_w = max(xs) - min(xs) + 1
    cp_h = max(ys) - min(ys) + 1

    seed = None

    # If next checkpoint direction is known, prefer that side over local pixel counts.
    if end_center_tile is not None:
      ex, ey = end_center_tile
      dir_x = ex - cx
      dir_y = ey - cy

      if cp_h > cp_w:
        # Vertical checkpoint: seed left/right based on end checkpoint direction.
        offset = 5 if dir_x > 0 else -5
        seed = (cx + offset, cy)
      else:
        # Horizontal checkpoint: seed above/below based on end checkpoint direction.
        offset = 5 if dir_y > 0 else -5
        seed = (cx, cy + offset)
    else:
      # Fallback: choose side with more nearby road tiles.
      if cp_h > cp_w:
        left_cnt = 0
        right_cnt = 0
        for yy in range(max(0, cy - 3), min(grid_h, cy + 4)):
          for xx in range(max(0, cx - 10), max(0, cx - 1)):
            if (xx, yy) in base_mask:
              left_cnt += 1
          for xx in range(min(grid_w, cx + 1), min(grid_w, cx + 11)):
            if (xx, yy) in base_mask:
              right_cnt += 1
        seed = (cx - 4, cy) if left_cnt > right_cnt else (cx + 4, cy)
      else:
        up_cnt = 0
        down_cnt = 0
        for xx in range(max(0, cx - 3), min(grid_w, cx + 4)):
          for yy in range(max(0, cy - 10), max(0, cy - 1)):
            if (xx, yy) in base_mask:
              up_cnt += 1
          for yy in range(min(grid_h, cy + 1), min(grid_h, cy + 11)):
            if (xx, yy) in base_mask:
              down_cnt += 1
        seed = (cx, cy - 4) if up_cnt > down_cnt else (cx, cy + 4)

    # Snap to nearest valid road tile around estimated seed.
    sx, sy = seed
    if (sx, sy) in base_mask:
      return (sx, sy)
    for r in range(1, 12):
      for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
          nx = sx + dx
          ny = sy + dy
          if nx < 0 or ny < 0 or nx >= grid_w or ny >= grid_h:
            continue
          if (nx, ny) in base_mask:
            return (nx, ny)
    return (cx, cy)

  def _seed_past_checkpoint(self, start_tiles, start_center, end_center, base_mask, end_tiles, grid_w, grid_h):
    if not start_tiles:
      return self._nearest_mask_tile(start_center, base_mask)

    smart_seed = self._smart_seed_from_checkpoint(
      start_tiles,
      base_mask,
      grid_w,
      grid_h,
      end_center_tile=end_center,
    )
    if smart_seed is not None and smart_seed not in end_tiles:
      return smart_seed

    sx, sy = start_center
    ex, ey = end_center
    dir_x = float(ex - sx)
    dir_y = float(ey - sy)
    dir_n = (dir_x * dir_x + dir_y * dir_y) ** 0.5
    if dir_n > 1e-6:
      dir_x /= dir_n
      dir_y /= dir_n

    ring = self._dilate_tiles(start_tiles, 3, grid_w, grid_h)
    ring = set(tile for tile in ring if tile in base_mask and tile not in start_tiles and tile not in end_tiles)
    if not ring:
      return self._nearest_mask_tile(start_center, set(tile for tile in base_mask if tile not in end_tiles))

    best = None
    best_score = -10 ** 12
    for tile in ring:
      vx = float(tile[0] - sx)
      vy = float(tile[1] - sy)
      proj = vx * dir_x + vy * dir_y if dir_n > 1e-6 else 0.0
      dist2 = vx * vx + vy * vy
      score = proj * 10.0 - dist2 * 0.05
      if score > best_score:
        best_score = score
        best = tile
    return best

  def _flood_fill_segment(self, base_mask, seed, end_tiles, blocked_tiles):
    if seed is None or seed not in base_mask:
      return set()

    traversable = set(base_mask)
    traversable.difference_update(blocked_tiles)
    traversable.difference_update(end_tiles)
    if seed not in traversable:
      return set()

    q = deque([seed])
    seen = set([seed])

    while q:
      cur = q.popleft()
      for nxt in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]), (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
        if nxt in traversable and nxt not in seen:
          seen.add(nxt)
          q.append(nxt)

    # Add checkpoint strips back as trigger-compatible drivable seam.
    seen.update(set(tile for tile in end_tiles if tile in base_mask))
    return seen

  def _flood_fill_bounded(self, nav_mask, seed, target_tiles, start_tiles, blocked_tiles):
    """Flood-fill from seed while treating start/target strips as walls.

    Returns (filled_tiles, target_reached).
    """
    if seed is None or seed not in nav_mask:
      return set(), False

    blocked = set(blocked_tiles)
    blocked.update(start_tiles)
    blocked.update(target_tiles)

    traversable = set(tile for tile in nav_mask if tile not in blocked)
    if seed in blocked:
      return set(), False
    if seed not in traversable:
      return set(), False

    q = deque([seed])
    seen = set([seed])
    reached = False

    while q:
      cur = q.popleft()
      for nxt in (
        (cur[0] + 1, cur[1]),
        (cur[0] - 1, cur[1]),
        (cur[0], cur[1] + 1),
        (cur[0], cur[1] - 1),
      ):
        if nxt in target_tiles:
          reached = True
          continue
        if nxt in traversable and nxt not in seen:
          seen.add(nxt)
          q.append(nxt)

    return seen, reached

  def _touching_checkpoint_tiles(self, filled_tiles, checkpoint_tiles):
    if not filled_tiles or not checkpoint_tiles:
      return set()
    edge = set()
    for tile in checkpoint_tiles:
      for n in (
        (tile[0] + 1, tile[1]),
        (tile[0] - 1, tile[1]),
        (tile[0], tile[1] + 1),
        (tile[0], tile[1] - 1),
      ):
        if n in filled_tiles:
          edge.add(tile)
          break
    return edge

  def _region_distance_to_seed(self, region_tiles, seed):
    if not region_tiles or seed is None:
      return 10 ** 12
    sx, sy = seed
    best = 10 ** 12
    for tx, ty in region_tiles:
      d = abs(tx - sx) + abs(ty - sy)
      if d < best:
        best = d
    return best

  def _build_segment_road_grid(
    self,
    segment_index,
    checkpoint_ids,
    checkpoint_tiles,
    checkpoint_centroids,
    tile_size,
    road_tiles_full,
    road_tiles_no_cyan,
    blocked_cp,
    grid_w,
    grid_h,
  ):
    """Auto-detect whether this segment requires cyan/blue roads.

    Returns: (base_mask, requires_underpass)
    """
    if not checkpoint_ids:
      return set(road_tiles_no_cyan), False

    start_cp = checkpoint_ids[segment_index]
    end_cp = checkpoint_ids[(segment_index + 1) % len(checkpoint_ids)]
    start_tiles = set(checkpoint_tiles.get(start_cp, set()))
    end_tiles = set(checkpoint_tiles.get(end_cp, set()))

    ts = max(1, int(tile_size))
    start_center = checkpoint_centroids.get(start_cp, (0.0, 0.0))
    end_center = checkpoint_centroids.get(end_cp, start_center)
    start_center_tile = (int(start_center[0]) // ts, int(start_center[1]) // ts)
    end_center_tile = (int(end_center[0]) // ts, int(end_center[1]) // ts)

    no_cyan = set(road_tiles_no_cyan)
    seed = self._seed_past_checkpoint(start_tiles, start_center_tile, end_center_tile, no_cyan, end_tiles, grid_w, grid_h)
    _, reached_no = self._flood_fill_bounded(no_cyan, seed, end_tiles, start_tiles, blocked_cp)
    if reached_no:
      return no_cyan, False

    full = set(road_tiles_full)
    _, reached_full = self._flood_fill_bounded(full, seed, end_tiles, start_tiles, blocked_cp)
    if reached_full:
      # Segment may need underpass-capable routing; keep no-cyan base and
      # selectively add cyan regions in bounded fill.
      return no_cyan, True

    # Fallback for malformed tracks.
    return full, True

  def _build_segment_masks(self, checkpoint_ids, checkpoint_paths, checkpoint_tiles, checkpoint_centroids, tile_size, road_tiles_full, road_tiles_no_cyan, blue_tiles, blue_regions, grid_w, grid_h):
    segment_masks: Dict[int, Set[Tuple[int, int]]] = {}
    if not checkpoint_ids:
      return segment_masks

    for region in blue_regions:
      region["used_in_segment"] = []

    all_cp_tiles = set()
    for cp_id in checkpoint_ids:
      all_cp_tiles.update(checkpoint_tiles.get(cp_id, set()))

    for seg_idx, cp_id in enumerate(checkpoint_ids):
      start_cp = checkpoint_ids[seg_idx]
      end_cp = checkpoint_ids[(seg_idx + 1) % len(checkpoint_ids)]
      start_tiles = set(checkpoint_tiles.get(start_cp, set()))
      end_tiles = set(checkpoint_tiles.get(end_cp, set()))

      # Root extraction: flood-fill reachable road from just past start checkpoint,
      # while treating other checkpoint strips as barriers.
      start_center = checkpoint_centroids.get(start_cp, (0.0, 0.0))
      end_center = checkpoint_centroids.get(end_cp, start_center)
      ts = max(1, int(tile_size))
      start_center_tile = (int(start_center[0]) // ts, int(start_center[1]) // ts)
      end_center_tile = (int(end_center[0]) // ts, int(end_center[1]) // ts)

      blocked_cp = set(all_cp_tiles)
      blocked_cp.difference_update(start_tiles)
      blocked_cp.difference_update(end_tiles)

      base_mask, requires_underpass = self._build_segment_road_grid(
        seg_idx,
        checkpoint_ids,
        checkpoint_tiles,
        checkpoint_centroids,
        tile_size,
        road_tiles_full,
        road_tiles_no_cyan,
        blocked_cp,
        grid_w,
        grid_h,
      )

      seed = self._seed_past_checkpoint(start_tiles, start_center_tile, end_center_tile, base_mask, end_tiles, grid_w, grid_h)
      flood_mask, reached = self._flood_fill_bounded(base_mask, seed, end_tiles, start_tiles, blocked_cp)

      used_region_ids = set()
      if requires_underpass and (not reached) and blue_regions:
        # Enable only the cyan region(s) that are needed to reach the target.
        ordered_regions = sorted(
          blue_regions,
          key=lambda r: self._region_distance_to_seed(r.get("tiles", set()), seed),
        )
        working_mask = set(base_mask)
        for region in ordered_regions:
          rid = int(region.get("id", -1))
          tiles = set(region.get("tiles", set()))
          if not tiles:
            continue
          working_mask.update(tiles)
          trial_mask, trial_reached = self._flood_fill_bounded(working_mask, seed, end_tiles, start_tiles, blocked_cp)
          if trial_reached:
            flood_mask = trial_mask
            reached = True
            if rid >= 0:
              used_region_ids.add(rid)
            break

      # If a direct one-region unlock failed, allow cumulative regions until reachable.
      if requires_underpass and (not reached) and blue_regions:
        working_mask = set(base_mask)
        ordered_regions = sorted(
          blue_regions,
          key=lambda r: self._region_distance_to_seed(r.get("tiles", set()), seed),
        )
        for region in ordered_regions:
          rid = int(region.get("id", -1))
          tiles = set(region.get("tiles", set()))
          if not tiles:
            continue
          working_mask.update(tiles)
          if rid >= 0:
            used_region_ids.add(rid)
          flood_mask, reached = self._flood_fill_bounded(working_mask, seed, end_tiles, start_tiles, blocked_cp)
          if reached:
            break

      for rid in used_region_ids:
        for region in blue_regions:
          if int(region.get("id", -1)) == rid:
            region.setdefault("used_in_segment", []).append(seg_idx)
            break

      path = checkpoint_paths.get(cp_id, [])
      candidate = set(flood_mask)

      # Add only local start/end seam tiles (not full strips) to keep triggers usable.
      candidate.update(self._touching_checkpoint_tiles(candidate, start_tiles))
      candidate.update(self._touching_checkpoint_tiles(candidate, end_tiles))

      # If flood-fill collapses due to overlap edge-cases, fall back to the
      # corridor-guided construction to keep segment usable.
      if (not candidate) or (not self._segment_connected(candidate, start_tiles, end_tiles)):
        for corridor_radius in (6, 8, 10, 12):
          if path:
            valid_area = self._dilate_tiles(path, corridor_radius, grid_w, grid_h)
          else:
            valid_area = set(road_tiles_full)

          mask = set(base_mask)
          mask.intersection_update(valid_area)
          mask = self._close_and_fill_mask(mask, valid_area, grid_w, grid_h, allowed_tiles=base_mask)
          if start_tiles:
            mask.update(tile for tile in start_tiles if tile in valid_area and tile in base_mask)
          if end_tiles:
            mask.update(tile for tile in end_tiles if tile in valid_area and tile in base_mask)

          candidate = mask
          if self._segment_connected(mask, start_tiles, end_tiles):
            break

      segment_masks[seg_idx] = candidate

      # Remove disconnected scraps that can bend gradients toward the wrong corner.
      reachable = self._reachable_component(segment_masks[seg_idx], start_tiles)
      if reachable:
        keep = set(reachable)
        # Keep end checkpoint seam tiles that touch the reachable road body.
        edge = self._dilate_tiles(reachable, 1, grid_w, grid_h)
        keep.update(tile for tile in end_tiles if tile in segment_masks[seg_idx] and tile in edge)
        segment_masks[seg_idx] = keep

    return segment_masks

  def _build_segment_flow_fields(self, checkpoint_ids, checkpoint_tiles, checkpoint_centroids, segment_masks, blue_tiles, tile_size, grid_w, grid_h):
    flow_fields: Dict[int, Dict[Tuple[int, int], Tuple[float, float]]] = {}
    if not checkpoint_ids:
      return flow_fields

    for seg_idx, cp_id in enumerate(checkpoint_ids):
      next_cp = checkpoint_ids[(seg_idx + 1) % len(checkpoint_ids)]
      mask = set(segment_masks.get(seg_idx, set()))
      if not mask:
        flow_fields[seg_idx] = {}
        continue

      # Use only the component reachable from current segment start.
      starts = checkpoint_tiles.get(cp_id, set())
      components = self._components_touching_starts(mask, starts)
      if components:
        components.sort(key=lambda c: len(c), reverse=True)
        mask = components[0]

      goals = self._build_centroid_goal_tiles(next_cp, checkpoint_centroids, checkpoint_tiles, mask, tile_size, grid_w, grid_h)
      if not goals:
        # Keep the target reachable even if corridor clipped checkpoint paint.
        near_goal = self._dilate_tiles(checkpoint_tiles.get(next_cp, set()), 2, grid_w, grid_h)
        goals = set(tile for tile in near_goal if tile in mask)

      flow = self._build_flow_field_for_mask(mask, goals, grid_w, grid_h)
      crossing_tiles = set(tile for tile in mask if tile in blue_tiles)
      flow = self._smooth_flow_on_crossings(flow, crossing_tiles, iterations=1)
      flow_fields[seg_idx] = flow

    return flow_fields

  def _build_centroid_goal_tiles(self, checkpoint_id, checkpoint_centroids, checkpoint_tiles, mask, tile_size, grid_w, grid_h):
    cp = checkpoint_centroids.get(checkpoint_id)
    if cp is None:
      return set()

    cx = int(cp[0]) // max(1, tile_size)
    cy = int(cp[1]) // max(1, tile_size)
    center = (cx, cy)

    if center in mask:
      return {center}

    # Try nearby cells around centroid first.
    for r in (1, 2, 3, 4):
      ring = self._dilate_tiles({center}, r, grid_w, grid_h)
      cand = [tile for tile in ring if tile in mask]
      if cand:
        cand.sort(key=lambda t: (t[0] - cx) * (t[0] - cx) + (t[1] - cy) * (t[1] - cy))
        return {cand[0]}

    # Fallback to checkpoint line paint, nearest to centroid.
    cp_tiles = [tile for tile in checkpoint_tiles.get(checkpoint_id, set()) if tile in mask]
    if cp_tiles:
      cp_tiles.sort(key=lambda t: (t[0] - cx) * (t[0] - cx) + (t[1] - cy) * (t[1] - cy))
      return {cp_tiles[0]}

    # Last-resort fallback: nearest drivable tile in this segment mask.
    # This prevents empty flow fields when checkpoint paint was clipped
    # by segment extraction around overlap-heavy junctions.
    if mask:
      nearest = min(mask, key=lambda t: (t[0] - cx) * (t[0] - cx) + (t[1] - cy) * (t[1] - cy))
      return {nearest}

    return set()

  def _smooth_flow_on_crossings(self, flow, crossing_tiles, iterations=1):
    if not flow or not crossing_tiles or iterations <= 0:
      return flow

    out = dict(flow)
    for _ in range(iterations):
      nxt = dict(out)
      for tile in crossing_tiles:
        sx = 0.0
        sy = 0.0
        w = 0.0
        tx, ty = tile
        for dy in (-1, 0, 1):
          for dx in (-1, 0, 1):
            n = (tx + dx, ty + dy)
            vec = out.get(n)
            if vec is None:
              continue
            if vec[0] == 0.0 and vec[1] == 0.0:
              continue
            weight = 2.0 if (dx == 0 and dy == 0) else 1.0
            sx += vec[0] * weight
            sy += vec[1] * weight
            w += weight

        if w > 0.0:
          nx = sx / w
          ny = sy / w
          nlen = (nx * nx + ny * ny) ** 0.5
          if nlen > 1e-6:
            nxt[tile] = (nx / nlen, ny / nlen)
      out = nxt

    return out

  def _build_flow_field_for_mask(self, drivable_tiles, goals, grid_w, grid_h):
    if not goals:
      return {}

    dist: Dict[Tuple[int, int], float] = {}
    q = []
    for g in goals:
      dist[g] = 0.0
      heapq.heappush(q, (0.0, g))

    neighbors = (
      (1, 0, 1.0),
      (-1, 0, 1.0),
      (0, 1, 1.0),
      (0, -1, 1.0),
      (1, 1, 1.41421356),
      (1, -1, 1.41421356),
      (-1, 1, 1.41421356),
      (-1, -1, 1.41421356),
    )

    while q:
      cd, cur = heapq.heappop(q)
      if cd > dist.get(cur, 10 ** 12):
        continue
      for dx, dy, step in neighbors:
        nxt = (cur[0] + dx, cur[1] + dy)
        if nxt[0] < 0 or nxt[1] < 0 or nxt[0] >= grid_w or nxt[1] >= grid_h:
          continue
        if nxt not in drivable_tiles:
          continue
        nd = cd + step
        if nd + 1e-9 < dist.get(nxt, 10 ** 12):
          dist[nxt] = nd
          heapq.heappush(q, (nd, nxt))

    vectors: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for tile, d in dist.items():
      if d <= 0:
        vectors[tile] = (0.0, 0.0)
        continue
      best = None
      best_d = d
      for dx, dy, _ in neighbors:
        nxt = (tile[0] + dx, tile[1] + dy)
        nd = dist.get(nxt)
        if nd is None:
          continue
        if nd + 1e-9 < best_d:
          best_d = nd
          best = nxt
      if best is None:
        vectors[tile] = (0.0, 0.0)
      else:
        dx = float(best[0] - tile[0])
        dy = float(best[1] - tile[1])
        n = (dx * dx + dy * dy) ** 0.5
        if n <= 1e-6:
          vectors[tile] = (0.0, 0.0)
        else:
          vectors[tile] = (dx / n, dy / n)

    return vectors

  def build_drivable_tiles(self, track_model, underpass_unlocked):
    drivable = set(track_model.road_tiles)
    if not track_model.blue_regions:
      return drivable

    for region in track_model.blue_regions:
      rid = int(region.get("id", -1))
      if rid < 0:
        continue
      unlocked = False
      if rid < len(underpass_unlocked):
        unlocked = bool(underpass_unlocked[rid])
      if not unlocked:
        drivable.difference_update(region.get("tiles", set()))

    return drivable

  def build_flow_field(self, track_model, target_checkpoint_id, drivable_tiles):
    goals = track_model.checkpoint_tiles.get(target_checkpoint_id, set())
    goals = set(tile for tile in goals if tile in drivable_tiles)
    if not goals:
      return {}

    dist: Dict[Tuple[int, int], int] = {}
    q = deque()
    for g in goals:
      dist[g] = 0
      q.append(g)

    while q:
      cur = q.popleft()
      cd = dist[cur]
      for nxt in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]), (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
        if nxt[0] < 0 or nxt[1] < 0 or nxt[0] >= track_model.grid_w or nxt[1] >= track_model.grid_h:
          continue
        if nxt not in drivable_tiles or nxt in dist:
          continue
        dist[nxt] = cd + 1
        q.append(nxt)

    vectors: Dict[Tuple[int, int], Tuple[float, float]] = {}
    for tile, d in dist.items():
      if d <= 0:
        vectors[tile] = (0.0, 0.0)
        continue
      best = None
      best_d = d
      for nxt in ((tile[0] + 1, tile[1]), (tile[0] - 1, tile[1]), (tile[0], tile[1] + 1), (tile[0], tile[1] - 1)):
        nd = dist.get(nxt)
        if nd is None:
          continue
        if nd < best_d:
          best_d = nd
          best = nxt
      if best is None:
        vectors[tile] = (0.0, 0.0)
      else:
        dx = float(best[0] - tile[0])
        dy = float(best[1] - tile[1])
        n = (dx * dx + dy * dy) ** 0.5
        if n <= 1e-6:
          vectors[tile] = (0.0, 0.0)
        else:
          vectors[tile] = (dx / n, dy / n)

    return vectors

  def _bfs_tile_path(self, starts, goals, road_tiles, grid_w, grid_h):
    if not starts or not goals:
      return []
    goal_set = set(goals)

    q = deque()
    prev: Dict[Tuple[int, int], Tuple[int, int]] = {}
    visited = set()

    for s in starts:
      if s in road_tiles:
        q.append(s)
        visited.add(s)
        prev[s] = None

    hit = None
    while q:
      cur = q.popleft()
      if cur in goal_set:
        hit = cur
        break

      for nxt in ((cur[0] + 1, cur[1]), (cur[0] - 1, cur[1]), (cur[0], cur[1] + 1), (cur[0], cur[1] - 1)):
        if nxt[0] < 0 or nxt[1] < 0 or nxt[0] >= grid_w or nxt[1] >= grid_h:
          continue
        if nxt in visited or nxt not in road_tiles:
          continue
        visited.add(nxt)
        prev[nxt] = cur
        q.append(nxt)

    if hit is None:
      return []

    path = []
    cur = hit
    while cur is not None:
      path.append(cur)
      cur = prev[cur]
    path.reverse()
    return path

  def _build_checkpoint_order(self, nb, reverse):
    ids = [16 * i for i in range(1, nb + 1)]
    if reverse == 1:
      ids.reverse()
    return ids

  def get_next_checkpoint_target(self, track_model, last_checkpoint):
    """Given the bot's lastCheckpoint value, return the (x, y) of the
    next checkpoint it needs to drive through.

    Returns None if the checkpoint can't be found.
    """
    nb = track_model.nb_checkpoints
    reverse = track_model.reverse

    if reverse == 0:
      # Normal: 16 -> 32 -> ... -> nb*16 -> 16 (lap)
      next_cp = last_checkpoint + 16
      if next_cp > nb * 16:
        next_cp = 16  # Wrap around to start/finish
    else:
      # Reverse: nb*16 -> (nb-1)*16 -> ... -> 16 -> nb*16 (lap)
      next_cp = last_checkpoint - 16
      if next_cp < 16:
        next_cp = nb * 16  # Wrap around

    return track_model.checkpoint_centroids.get(next_cp, None)

  def get_route_targets(self, track_model, last_checkpoint, count=2):
    """Return the next N checkpoint targets, using road-based waypoints when available.
    
    For each checkpoint, if a planner path exists, sample intermediate waypoints
    along the road. Otherwise fall back to the checkpoint centroid.
    
    Returns list of (checkpoint_id, (x, y)) tuples.
    """
    if count <= 0 or not track_model.checkpoint_ids:
      return []

    ids = track_model.checkpoint_ids
    if last_checkpoint in ids:
      idx = ids.index(last_checkpoint)
    else:
      idx = -1

    targets = []
    for i in range(1, count + 1):
      cp_id = ids[(idx + i) % len(ids)]

      # Use the road path for the segment we are currently traveling through.
      # The first target should come from last_checkpoint -> next_checkpoint,
      # not from the next checkpoint's outgoing segment, or the bot can
      # appear to drive the course in reverse.
      segment_start = last_checkpoint if last_checkpoint in ids else ids[idx]
      if i > 1:
        segment_start = ids[(idx + i - 1) % len(ids)]

      # Try to get road-based waypoints from that checkpoint segment path.
      path = track_model.checkpoint_paths.get(segment_start, [])
      if path and len(path) > 0:
        # Sample a point ahead on the path to guide around obstacles while
        # still following the correct lap direction.
        if i == 1:
          sample_idx = min(max(1, len(path) // 4), len(path) - 1)
        else:
          sample_idx = min(max(1, (len(path) * 2) // 3), len(path) - 1)
        tile = path[sample_idx]
        # Convert tile coords to world coords.
        tile_size = max(1, int(track_model.tile_size))
        waypoint = ((tile[0] + 0.5) * tile_size, (tile[1] + 0.5) * tile_size)
        targets.append((cp_id, waypoint))
      else:
        # Fallback to checkpoint centroid if no path available.
        pos = track_model.checkpoint_centroids.get(cp_id)
        if pos is not None:
          targets.append((cp_id, pos))
    
    return targets

  def get_planner_targets(self, track_model, last_checkpoint, pos, speed, max_speed):
    """Return speed-aware lookahead targets and planner confidence.

    Output keys:
    - near: (x, y) lookahead point
    - far: (x, y) further lookahead point
    - curvature: normalized turn intensity (0..1)
    - confidence: planner confidence (0..1)
    """
    ids = track_model.checkpoint_ids
    if not ids:
      return None

    # Planner path key is current checkpoint -> next checkpoint.
    if last_checkpoint in ids:
      start_cp = last_checkpoint
    else:
      start_cp = ids[0]

    path = track_model.checkpoint_paths.get(start_cp, [])
    if not path:
      return None

    tile_size = max(1, int(track_model.tile_size))
    tx = int(pos[0]) // tile_size
    ty = int(pos[1]) // tile_size
    car_tile = (tx, ty)

    # Find nearest tile index along path.
    nearest_i = 0
    best_d2 = 10 ** 9
    for i, tile in enumerate(path):
      dx = tile[0] - car_tile[0]
      dy = tile[1] - car_tile[1]
      d2 = dx * dx + dy * dy
      if d2 < best_d2:
        best_d2 = d2
        nearest_i = i

    speed_ratio = 0.0
    if max_speed > 1e-6:
      speed_ratio = max(0.0, min(1.0, speed / max_speed))
    near_steps = 4 + int(8 * speed_ratio)
    far_steps = near_steps + 6 + int(10 * speed_ratio)

    near_i = min(len(path) - 1, nearest_i + near_steps)
    far_i = min(len(path) - 1, nearest_i + far_steps)

    near_tile = path[near_i]
    far_tile = path[far_i]

    near = ((near_tile[0] + 0.5) * tile_size, (near_tile[1] + 0.5) * tile_size)
    far = ((far_tile[0] + 0.5) * tile_size, (far_tile[1] + 0.5) * tile_size)

    # Curvature proxy from turn angle between local vectors.
    v1 = (near[0] - pos[0], near[1] - pos[1])
    v2 = (far[0] - near[0], far[1] - near[1])
    n1 = (v1[0] * v1[0] + v1[1] * v1[1]) ** 0.5
    n2 = (v2[0] * v2[0] + v2[1] * v2[1]) ** 0.5
    curvature = 0.0
    if n1 > 1e-6 and n2 > 1e-6:
      dot = (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)
      dot = max(-1.0, min(1.0, dot))
      # Map angle [0..pi] to [0..1]
      import math
      curvature = abs(math.acos(dot)) / math.pi

    # Confidence: on-road + not too far from path centerline.
    confidence = 1.0
    if car_tile not in track_model.road_tiles:
      confidence = 0.2
    elif best_d2 > 16:  # 4+ tiles away from planned segment
      confidence = 0.45
    elif best_d2 > 9:
      confidence = 0.65

    return {
      "near": near,
      "far": far,
      "curvature": curvature,
      "confidence": confidence,
      "distance_to_path_tiles": best_d2 ** 0.5,
    }
