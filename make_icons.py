from PIL import Image, ImageOps
from pathlib import Path

src = Path("static/img/s.png")
out = Path("static/icons")
out.mkdir(parents=True, exist_ok=True)

img = Image.open(src).convert("RGBA")

# fundo preto (remove transparência)
bg = Image.new("RGBA", img.size, (0, 0, 0, 255))
bg.alpha_composite(img)
img = bg.convert("RGB")

def save(size, name):
    im = ImageOps.contain(img, (size, size), method=Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (0, 0, 0))
    x = (size - im.size[0]) // 2
    y = (size - im.size[1]) // 2
    canvas.paste(im, (x, y))
    canvas.save(out / name, format="PNG", optimize=True)

save(180, "apple-touch-icon.png")
save(192, "icon-192.png")
save(512, "icon-512.png")

print("OK: ícones recriados (sem transparência) em static/icons/")