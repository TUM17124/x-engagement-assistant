"""Deterministic application artwork, no external branding assets."""
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parent.parent/"src-tauri/icons"
root.mkdir(parents=True,exist_ok=True)
image=Image.new("RGBA",(256,256),(0,0,0,0))
draw=ImageDraw.Draw(image)
draw.rounded_rectangle((0,0,255,255),radius=60,fill="#111621")
draw.polygon([(57,66),(199,66),(199,169),(128,169),(78,212),(78,169),(57,169)],fill="#b5f578")
draw.line([(105,94),(153,145)],fill="#111621",width=15)
draw.line([(153,94),(105,145)],fill="#111621",width=15)
for size in (32,128,256):
    image.resize((size,size),Image.Resampling.LANCZOS).save(root/f"{size}x{size}.png")
image.save(root/"icon.ico",sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
