import datetime
import os
from PIL import Image, ImageDraw, ImageFont

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static"
)
TEMPLATES_DIR = os.path.join(STATIC_DIR, "templates")
CERTIFICATES_DIR = os.path.join(STATIC_DIR, "certificates")
FONTS_DIR = os.path.join(STATIC_DIR, "fonts")

os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(CERTIFICATES_DIR, exist_ok=True)
os.makedirs(FONTS_DIR, exist_ok=True)

TEMPLATE_PATH = os.path.join(TEMPLATES_DIR, "certificate_template.png")


def generate_personalized_certificate_png(
    user_full_name: str,
    title: str,
    source_type: str,
    source_id: int,
    user_id: int,
    ceo_name: str = "Haneen",
    president_name: str = "Kariman",
    date_font_style: str = "sacramento",
) -> str:
  """Generates a personalized PNG certificate matching official AIChE style.

  Features an increased font size for the completion subtitle and course name.
  """
  if not os.path.exists(TEMPLATE_PATH):
    raise FileNotFoundError(f"Template PNG not found at {TEMPLATE_PATH}")

  # Open official AIChE certificate template (3579 x 2551)
  base_img = Image.open(TEMPLATE_PATH).convert("RGB")
  draw = ImageDraw.Draw(base_img)

  # Load Font Paths
  sacramento_path = os.path.join(FONTS_DIR, "Sacramento-Regular.ttf")
  lato_path = os.path.join(FONTS_DIR, "Lato-Bold.ttf")

  try:
    # 1. Student Name: Flowing Script with Auto-Shrinking (handles 4-5 names)
    name_font_size = 270
    font_name_path = (
        sacramento_path if os.path.exists(sacramento_path) else "arial.ttf"
    )
    font_name = ImageFont.truetype(font_name_path, name_font_size)

    max_allowed_width = 2800
    text_length = draw.textlength(user_full_name, font=font_name)
    while text_length > max_allowed_width and name_font_size > 100:
      name_font_size -= 10
      font_name = ImageFont.truetype(font_name_path, name_font_size)
      text_length = draw.textlength(user_full_name, font=font_name)

    # 2. Subtitle configuration (Increased size to 75 for better prominence)
    font_sub = ImageFont.truetype(
        lato_path if os.path.exists(lato_path) else "arial.ttf", 75
    )
    font_small = ImageFont.truetype(
        lato_path if os.path.exists(lato_path) else "arial.ttf", 38
    )

    # 3. Signatures & Date Font: Script Handwriting (Sacramento)
    font_sig_path = (
        sacramento_path if os.path.exists(sacramento_path) else "arial.ttf"
    )
    font_sig = ImageFont.truetype(font_sig_path, 130)  # Script size for names
    font_date = ImageFont.truetype(
        font_sig_path, 85
    )  # Script size for date

  except Exception:
    font_name = ImageFont.load_default()
    font_sub = ImageFont.load_default()
    font_date = ImageFont.load_default()
    font_small = ImageFont.load_default()
    font_sig = ImageFont.load_default()

  # Draw Student Name (Centered with auto-adjusted size)
  draw.text(
      (1760, 1170),
      user_full_name,
      fill=(30, 32, 33),
      font=font_name,
      anchor="mm",
  )

  # Draw Subtitle Line (Standard appreciation message)
  subtitle_text = "We appreciate your continuous dedication and consistency."
  draw.text(
      (1760, 1520), subtitle_text, fill=(34, 37, 42), font=font_sub, anchor="mm"
  )

  # Draw CEO & President Names (Script style, positioned close to the lines at Y=2120)
  draw.text(
      (620, 2120), ceo_name, fill=(255, 255, 255), font=font_sig, anchor="mm"
  )
  draw.text(
      (1450, 2120),
      president_name,
      fill=(255, 255, 255),
      font=font_sig,
      anchor="mm",
  )

  # Draw Date Above Line (Script style, smaller size, lowered close to the line at Y=2120)
  issue_date = datetime.datetime.now().strftime("%B %d, %Y")
  draw.text(
      (2310, 2120), issue_date, fill=(255, 255, 255), font=font_date, anchor="mm"
  )

  # Draw Verification Serial ID at Bottom Left
  cert_id_str = (
      f"ID: CERT-AICHE-{source_type[:3].upper()}-{source_id:04d}-{user_id:04d}"
  )
  draw.text(
      (250, 2450), cert_id_str, fill=(148, 163, 184), font=font_small, anchor="lm"
  )

  # Save Output Image
  filename = f"cert_{source_type}_{source_id}_user_{user_id}.png"
  output_path = os.path.join(CERTIFICATES_DIR, filename)
  base_img.save(output_path)

  return f"/static/certificates/{filename}"