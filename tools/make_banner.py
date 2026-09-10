# -*- coding: utf-8 -*-
"""Store banner for scalebox_accounting.

Keeps the look of the original - off-white ground, teal rule, dark navy
document mark - and changes what it says: the old one led with "AT Full
Accounting" and "Enterprise accounting features", both of which the module
moved away from before publishing.

Needs Pillow, which is not installed on the authoring machine; run it in the
Odoo environment instead:

    /opt/.venv19/bin/python make_banner.py /path/to/banner.png
"""
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 2400, 800                  # supersampled; halved on save
OUT = (1200, 400)

GROUND = (248, 249, 250)
TEAL = (26, 137, 118)
NAVY = (26, 42, 61)
GREY = (90, 100, 110)
WHITE = (255, 255, 255)
LINE = (205, 213, 220)


def font(size, bold=False):
    for name in ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf',
                 '/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf'
                 % ('-Bold' if bold else '')):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


img = Image.new('RGB', (W, H), GROUND)
d = ImageDraw.Draw(img)

# The teal rule along the top, as on the original.
d.rectangle([0, 0, W, 14], fill=TEAL)

x = W * 0.06
d.text((x, H * 0.24), 'Full Accounting', font=font(112, bold=True), fill=NAVY)
d.text((x, H * 0.46), 'Financial reports, assets and deferrals for Odoo 19 Community',
       font=font(46), fill=GREY)

# Feature pills.
pill_font = font(38)
px = x
for label in ('Financial Reports', 'Assets', 'Deferrals', 'Follow-ups'):
    box = d.textbbox((0, 0), label, font=pill_font)
    w = box[2] - box[0]
    d.rounded_rectangle([px, H * 0.63, px + w + 60, H * 0.63 + 76],
                        radius=38, outline=TEAL, width=3)
    d.text((px + 30, H * 0.63 + 20), label, font=pill_font, fill=TEAL)
    px += w + 60 + 28

# The document mark on the right: a rounded navy tile holding a sheet with
# ruled lines and a small bar chart.
mx, my, ms = W * 0.80, H * 0.28, H * 0.44
d.rounded_rectangle([mx, my, mx + ms, my + ms], radius=ms * 0.18, fill=NAVY)
sheet = [mx + ms * 0.16, my + ms * 0.14, mx + ms * 0.84, my + ms * 0.86]
d.rectangle(sheet, fill=WHITE)
for i in range(4):
    ly = sheet[1] + ms * (0.12 + i * 0.10)
    d.rectangle([sheet[0] + ms * 0.08, ly, sheet[2] - ms * 0.12, ly + ms * 0.035],
                fill=LINE)
base = sheet[3] - ms * 0.12
for i, height in enumerate((0.12, 0.20, 0.28)):
    bx = sheet[0] + ms * (0.10 + i * 0.16)
    d.rectangle([bx, base - ms * height, bx + ms * 0.10, base], fill=TEAL)
d.rectangle([sheet[0] + ms * 0.08, base + ms * 0.02,
             sheet[2] - ms * 0.10, base + ms * 0.05], fill=NAVY)

out = sys.argv[1] if len(sys.argv) > 1 else 'banner.png'
img.resize(OUT, Image.LANCZOS).save(out, 'PNG')
print('wrote', out)
