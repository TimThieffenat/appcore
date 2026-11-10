"""Generates the app's icon and the Google Play listing images (a starting point
to customise: theme gradient, the app's initial). From the app's folder:

    pip install pillow
    python tools/make_icon.py

Writes:
- icon.png                           512 × 512, transparent rounded corners (app, APK)
- store/play_icon_512.png            512 × 512, full square (Google Play rounds it itself)
- store/feature_graphic_1024x500.png Google Play listing banner
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SIZE = 512
SS = 4                        # supersampling for smooth edges
TOP_LEFT = (0x4C, 0xBF, 0xB3)       # turquoise (light theme, style.py)
BOTTOM_RIGHT = (0xF0, 0x8F, 0xB0)   # pink


def _name() -> str:
    import runpy
    return runpy.run_path(str(ROOT / "app_info.py"))["NAME"]


def gradient(w: int, h: int) -> Image.Image:
    img = Image.new("RGB", (w, h))
    px = img.load()
    for y in range(h):
        for x in range(w):
            t = (x / w + y / h) / 2
            px[x, y] = tuple(int(a + (b - a) * t) for a, b in zip(TOP_LEFT, BOTTOM_RIGHT))
    return img


def font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def icon(rounded: bool) -> Image.Image:
    big = SIZE * SS
    img = gradient(SIZE, SIZE).resize((big, big)).convert("RGBA")
    draw = ImageDraw.Draw(img)
    letter = _name()[:1].upper()
    f = font(int(big * 0.55))
    box = draw.textbbox((0, 0), letter, font=f)
    draw.text(((big - box[2] - box[0]) / 2, (big - box[3] - box[1]) / 2), letter,
              font=f, fill="white")
    if rounded:
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, big, big), radius=int(big * 0.22), fill=255)
        img.putalpha(mask)
    return img.resize((SIZE, SIZE), Image.LANCZOS)


def banner() -> Image.Image:
    img = gradient(1024, 500).convert("RGBA")
    draw = ImageDraw.Draw(img)
    f = font(96)
    text = _name()
    box = draw.textbbox((0, 0), text, font=f)
    draw.text(((1024 - box[2] - box[0]) / 2, (500 - box[3] - box[1]) / 2), text,
              font=f, fill="white")
    return img


def main() -> None:
    (ROOT / "store").mkdir(exist_ok=True)
    icon(True).save(ROOT / "icon.png")
    icon(False).convert("RGB").save(ROOT / "store" / "play_icon_512.png")
    banner().convert("RGB").save(ROOT / "store" / "feature_graphic_1024x500.png")
    print("icon.png, store/play_icon_512.png, store/feature_graphic_1024x500.png")


if __name__ == "__main__":
    main()
