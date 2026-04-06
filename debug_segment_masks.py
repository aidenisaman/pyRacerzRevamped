import argparse
import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from modules.track import Track
from modules.ai_track_model import TrackModelCache


def _fill_tile(surface, tile, tile_size, color):
  tx, ty = tile
  x0 = tx * tile_size
  y0 = ty * tile_size
  rect = pygame.Rect(x0, y0, tile_size, tile_size)
  surface.fill(color, rect)


def _render_from_model(track_obj, model, segment_n, out_dir, with_flow=False):
  width = track_obj.trackF.get_width()
  height = track_obj.trackF.get_height()
  tile_size = max(1, int(model.tile_size))

  mask = model.segment_masks.get(segment_n, set())
  blue_tiles = model.blue_tiles
  checkpoint_union = set()
  for cp_tiles in model.checkpoint_tiles.values():
    checkpoint_union.update(cp_tiles)

  # Render white=drivable, black=wall.
  debug_img = pygame.Surface((width, height))
  debug_img.fill((0, 0, 0))
  for tile in mask:
    # Default drivable road.
    color = (255, 255, 255)
    # Highlight tiles where overlay paint is part of the drivable continuity.
    if tile in checkpoint_union:
      color = (255, 140, 140)
    if tile in blue_tiles:
      color = (140, 140, 255)
    _fill_tile(debug_img, tile, tile_size, color)

  # Highlight checkpoints: red=start CP, blue=end CP.
  start_cp = model.checkpoint_ids[segment_n]
  end_cp = model.checkpoint_ids[(segment_n + 1) % len(model.checkpoint_ids)]

  for tile in model.checkpoint_tiles.get(start_cp, set()):
    _fill_tile(debug_img, tile, tile_size, (255, 0, 0))

  for tile in model.checkpoint_tiles.get(end_cp, set()):
    _fill_tile(debug_img, tile, tile_size, (0, 100, 255))

  if with_flow:
    flow = model.segment_flow_fields.get(segment_n, {})
    # Sparse vector field overlay for readability.
    step = max(2, 8 // max(1, tile_size))
    for tile, vec in flow.items():
      if tile[0] % step != 0 or tile[1] % step != 0:
        continue
      if vec[0] == 0.0 and vec[1] == 0.0:
        continue
      cx = int((tile[0] + 0.5) * tile_size)
      cy = int((tile[1] + 0.5) * tile_size)
      ex = int(cx + vec[0] * tile_size * 2.5)
      ey = int(cy + vec[1] * tile_size * 2.5)
      pygame.draw.line(debug_img, (0, 255, 0), (cx, cy), (ex, ey), 1)

  os.makedirs(out_dir, exist_ok=True)
  out_path = os.path.join(out_dir, "%s_segment_%02d.png" % (track_obj.name, segment_n))
  pygame.image.save(debug_img, out_path)
  return out_path


def render_debug_segment_mask(track_name, segment_n, out_dir="debug_masks", with_flow=False):
  pygame.init()
  pygame.display.set_mode((1, 1))

  track_obj = Track(track_name)
  model = TrackModelCache().get_for_track(track_obj)

  if segment_n < 0 or segment_n >= len(model.checkpoint_ids):
    raise ValueError("segment_n out of range for track '%s': 0..%d" % (track_name, len(model.checkpoint_ids) - 1))

  return _render_from_model(track_obj, model, segment_n, out_dir, with_flow=with_flow)


def render_all_segments(track_name, out_dir="debug_masks", with_flow=False):
  pygame.init()
  pygame.display.set_mode((1, 1))

  track_obj = Track(track_name)
  model = TrackModelCache().get_for_track(track_obj)

  outputs = []
  for segment_n in range(len(model.checkpoint_ids)):
    outputs.append(_render_from_model(track_obj, model, segment_n, out_dir=out_dir, with_flow=with_flow))
  return outputs


def main():
  parser = argparse.ArgumentParser(description="Render AI segment masks for visual debugging.")
  parser.add_argument("--track", default="city", help="Track name (e.g., city, desert, forest)")
  parser.add_argument("--segment", type=int, default=None, help="Single segment index to render")
  parser.add_argument("--out", default="debug_masks", help="Output directory")
  parser.add_argument("--flow", action="store_true", help="Overlay sparse flow vectors")
  args = parser.parse_args()

  if args.segment is None:
    outputs = render_all_segments(args.track, out_dir=args.out, with_flow=args.flow)
    for p in outputs:
      print(p)
  else:
    out_path = render_debug_segment_mask(args.track, args.segment, out_dir=args.out, with_flow=args.flow)
    print(out_path)


if __name__ == "__main__":
  main()
