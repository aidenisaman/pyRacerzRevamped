from PIL import Image
import sys

# Usage: python check_red_channel.py <imagefile> <x> <y1> <y2>
# Example: python check_red_channel.py desertf.png 100 0 400

def check_red_line(image_path, x, y1, y2):
    img = Image.open(image_path).convert('RGBA')
    print(f"Checking red values at x={x}, y={y1} to y={y2} in {image_path}:")
    for y in range(y1, y2):
        r, g, b, a = img.getpixel((x, y))
        print(f"Pixel at ({x},{y}): R={r} G={g} B={b} A={a}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python check_red_channel.py <imagefile> <x> <y1> <y2>")
        sys.exit(1)
    imagefile = sys.argv[1]
    x = int(sys.argv[2])
    y1 = int(sys.argv[3])
    y2 = int(sys.argv[4])
    check_red_line(imagefile, x, y1, y2)
