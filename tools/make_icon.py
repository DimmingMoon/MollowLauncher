"""Генератор иконки MollowLauncher: python tools/make_icon.py  (нужен Pillow)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

S = 1024
OUT = Path(__file__).resolve().parent.parent / "assets"


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def pt(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bg = Image.new("RGBA", (S, S))
    d = ImageDraw.Draw(bg)
    for y in range(S):
        d.line([(0, y), (S, y)], fill=lerp(hexc("#1b2b22"), hexc("#0a100d"), y / S) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=230, fill=255)
    img.paste(bg, (0, 0), mask)
    ImageDraw.Draw(img).rounded_rectangle([6, 6, S - 7, S - 7], radius=226, outline=hexc("#2f4538") + (255,), width=6)

    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([200, 300, 824, 924], fill=hexc("#20C878") + (115,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(70)))

    cx, cy, R = 500, 600, 320
    dx, dy = R * 0.866, R * 0.5
    T, TR, C, TL = (cx, cy - R), (cx + dx, cy - dy), (cx, cy), (cx - dx, cy - dy)
    BL, B, BR = (cx - dx, cy + dy), (cx, cy + R), (cx + dx, cy + dy)
    shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([250, 880, 750, 950], fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img, shadow.filter(ImageFilter.GaussianBlur(24)))

    cube = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    cd = ImageDraw.Draw(cube)
    cd.polygon([T, TR, C, TL], fill=hexc("#4CE9A3"))
    cd.polygon([TL, C, B, BL], fill=hexc("#20C878"))
    cd.polygon([TR, C, B, BR], fill=hexc("#0F8F55"))

    def quad(u0, v0, u1, v1):
        def p(u, v):
            return pt(pt(T, TL, v), pt(TR, C, v), u)
        return [p(u0, v0), p(u1, v0), p(u1, v1), p(u0, v1)]

    for u, v, col in [(0.12, 0.12, "#7BF2BE"), (0.62, 0.20, "#3DDB92"), (0.36, 0.58, "#7BF2BE"), (0.70, 0.66, "#38D08A")]:
        cd.polygon(quad(u, v, u + 0.22, v + 0.22), fill=hexc(col))
    for a, b in [(TL, C), (C, TR), (T, TL), (T, TR)]:
        cd.line([a, b], fill=hexc("#A8FFD6"), width=7)
    cd.line([C, B], fill=hexc("#0B6B3F"), width=7)
    img = Image.alpha_composite(img, cube)

    moon = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(moon)
    mx, my, mr = 800, 210, 96
    md.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=255)
    md.ellipse([mx - mr + 50, my - mr - 22, mx + mr + 50, my + mr - 22], fill=0)
    mglow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    mglow.paste(Image.new("RGBA", (S, S), hexc("#9BFFD0") + (200,)), (0, 0), moon)
    img = Image.alpha_composite(img, mglow.filter(ImageFilter.GaussianBlur(22)))
    img.paste(Image.new("RGBA", (S, S), hexc("#F4FFF9") + (255,)), (0, 0), moon)

    final = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    final.paste(img, (0, 0), mask)
    OUT.mkdir(exist_ok=True)
    final.resize((512, 512), Image.LANCZOS).save(OUT / "icon.png")
    final.save(OUT / "icon.ico", sizes=[(s, s) for s in (256, 128, 64, 48, 32, 24, 16)])


def wizard():
    """Картинки для мастера установщика: боковая (164x314) и малая (55x55)."""
    from PIL import ImageFont
    k = 3
    W, H = 164 * k, 314 * k
    big = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(big)
    for y in range(H):
        d.line([(0, y), (W, y)], fill=lerp(hexc("#1b2b22"), hexc("#0a100d"), y / H))
    icon = Image.open(OUT / "icon.png").convert("RGBA").resize((120 * k, 120 * k), Image.LANCZOS)
    big.paste(icon, ((W - 120 * k) // 2, 52 * k), icon)
    try:
        f1, f2 = ImageFont.load_default(size=26 * k), ImageFont.load_default(size=13 * k)
    except TypeError:
        f1 = f2 = ImageFont.load_default()
    for text, font, y, col in (("Mollow", f1, 188 * k, "#F1F5F2"), ("Launcher", f1, 214 * k, "#20C878"),
                               ("Minecraft launcher", f2, 258 * k, "#91A398")):
        w = d.textlength(text, font=font)
        d.text(((W - w) / 2, y), text, font=font, fill=col)
    d.rectangle([W // 2 - 20 * k, 250 * k, W // 2 + 20 * k, 250 * k + 2 * k], fill=hexc("#20C878"))
    big.resize((164, 314), Image.LANCZOS).save(OUT / "wizard_big.bmp")
    small = Image.new("RGB", (55 * k, 55 * k), hexc("#101411"))
    ic = Image.open(OUT / "icon.png").convert("RGBA").resize((55 * k, 55 * k), Image.LANCZOS)
    small.paste(ic, (0, 0), ic)
    small.resize((55, 55), Image.LANCZOS).save(OUT / "wizard_small.bmp")


if __name__ == "__main__":
    main()
    wizard()
