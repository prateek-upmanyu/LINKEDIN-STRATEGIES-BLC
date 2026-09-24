import os
import textwrap
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")
TEMPLATE_PATH = os.path.join(BASE_DIR, "template.jpg")

def get_font(size, bold=True):
    font_filename = "segoeuib.ttf" if bold else "segoeui.ttf"
    bundled_font = os.path.join(FONTS_DIR, font_filename)
    if os.path.exists(bundled_font):
        try:
            return ImageFont.truetype(bundled_font, size)
        except Exception:
            pass
            
    system_cands = [
        "C:\\Windows\\Fonts\\segoeuib.ttf" if bold else "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    ]
    for cand in system_cands:
        if os.path.exists(cand):
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                pass
                
    return ImageFont.load_default()

def render_strategy_card(tag_text, title_text, body_text, takeaway_text, output_path):
    if not os.path.exists(TEMPLATE_PATH):
        raise FileNotFoundError(f"Template image not found at {TEMPLATE_PATH}")
        
    img = Image.open(TEMPLATE_PATH).convert("RGBA")
    draw = ImageDraw.Draw(img)
    W, H = img.size

    font_tag = get_font(16, bold=True)
    font_title = get_font(28, bold=True)
    font_body = get_font(20, bold=False)
    font_take = get_font(17, bold=True)

    # 1. Draw Top Tag / Badge
    tbbox = draw.textbbox((0, 0), tag_text, font=font_tag)
    tw = tbbox[2] - tbbox[0]
    draw.text(((W - tw) // 2, 280), tag_text, font=font_tag, fill=(147, 197, 253))

    # 2. Draw Title
    tlines = textwrap.wrap(title_text, width=28)
    ty = 330
    for line in tlines:
        bbox = draw.textbbox((0, 0), line, font=font_title)
        w = bbox[2] - bbox[0]
        draw.text(((W - w) // 2, ty), line, font=font_title, fill=(255, 255, 255))
        ty += 38

    # 3. Draw Body
    blines = textwrap.wrap(body_text, width=34)
    by = ty + 25
    for line in blines:
        bbox = draw.textbbox((0, 0), line, font=font_body)
        w = bbox[2] - bbox[0]
        draw.text(((W - w) // 2, by), line, font=font_body, fill=(226, 232, 240))
        by += 30

    # 4. Draw Key Takeaway
    klines = textwrap.wrap(takeaway_text, width=34)
    ky = by + 30
    for line in klines:
        bbox = draw.textbbox((0, 0), line, font=font_take)
        w = bbox[2] - bbox[0]
        draw.text(((W - w) // 2, ky), line, font=font_take, fill=(191, 219, 254))
        ky += 26

    img.convert("RGB").save(output_path, "JPEG", quality=95)
    return output_path
