import secrets
import qrcode
from io import BytesIO
from django.core.files import File
from django.db import models
from PIL import Image, ImageOps, ImageDraw, ImageFont  # 🌟 Added ImageFont to write text!

# 🌟 THE SAFETY SHIELD
try:
    from qrcode.image.styledproxy import StyledPilImage
    from qrcode.image.styles.moduledrawers import RoundedModuleDrawer
    from qrcode.image.styles.colormasks import SolidFillColorMask
    STYLING_AVAILABLE = True
except ImportError:
    STYLING_AVAILABLE = False

def generate_qr_token():
    return secrets.token_urlsafe(8)

class Site(models.Model):
    name = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    active = models.BooleanField(default=True)
    def __str__(self): return self.name

class Area(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='areas')
    name = models.CharField(max_length=100)
    def __str__(self): return f"{self.name} - {self.site.name}"

class SpecificArea(models.Model):
    name = models.CharField(max_length=100)
    def __str__(self): return self.name

class Location(models.Model):
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='locations')
    specific_area = models.ForeignKey(SpecificArea, on_delete=models.SET_NULL, blank=True, null=True)
    name = models.CharField(max_length=100)
    floor = models.CharField(max_length=50, blank=True, null=True)
    qr_token = models.CharField(max_length=50, unique=True, default=generate_qr_token)
    qr_enabled = models.BooleanField(default=True)
    qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self): return self.name

    def save(self, *args, **kwargs):
        if not self.qr_image:
            # 🌟 Update this IP whenever you change Wi-Fi networks!
            qr_url = f"http://192.168.68.127:8000/q/{self.qr_token}/"
            
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_Q, box_size=12, border=2)
            qr.add_data(qr_url)
            qr.make(fit=True)

            # 🌟 1. GENERATE THE QR CODE IMAGE 🌟
            if STYLING_AVAILABLE:
                img = qr.make_image(
                    image_factory=StyledPilImage,
                    module_drawer=RoundedModuleDrawer(),
                    color_mask=SolidFillColorMask(back_color=(255, 255, 255), front_color=(0, 0, 0))
                )
                img_gray = img.convert("L")
                alpha_mask = ImageOps.invert(img_gray)
                
                width, height = img_gray.size
                final_img = Image.new("RGBA", (width, height))
                draw_grad = ImageDraw.Draw(final_img)
                
                r1, g1, b1 = 20, 30, 80
                r2, g2, b2 = 180, 0, 30
                for x in range(width):
                    r = int(r1 + (r2 - r1) * x / width)
                    g = int(g1 + (g2 - g1) * x / width)
                    b = int(b1 + (b2 - b1) * x / width)
                    draw_grad.line([(x, 0), (x, height)], fill=(r, g, b, 255))
                
                final_img.putalpha(alpha_mask)
            else:
                final_img = qr.make_image(fill_color="#141E50", back_color="transparent").convert("RGBA")

            # 🌟 2. ADDING THE TEXT BELOW 🌟
            qr_w, qr_h = final_img.size
            text_padding = 100 # Extra space at the bottom for the text
            
            # Create a solid white canvas to paste everything onto
            canvas = Image.new("RGBA", (qr_w, qr_h + text_padding), (255, 255, 255, 255))
            
            # Paste the QR code at the top (using itself as the transparency mask)
            canvas.paste(final_img, (0, 0), final_img)

            # Prepare the text
            site_text = self.area.site.name if self.area and self.area.site else "Shyam Metalics"
            loc_text = self.name
            if self.specific_area:
                loc_text = f"{self.name}, {self.specific_area.name}"

            # Try to load Windows Arial font, fallback to default if missing
            try:
                font_title = ImageFont.truetype("arial.ttf", 30)
                font_sub = ImageFont.truetype("arial.ttf", 22)
            except IOError:
                font_title = ImageFont.load_default()
                font_sub = ImageFont.load_default()

            draw_text = ImageDraw.Draw(canvas)

            # Helper function to center text horizontally
            def get_text_x(text, font):
                try:
                    bbox = draw_text.textbbox((0, 0), text, font=font)
                    return (qr_w - (bbox[2] - bbox[0])) // 2
                except AttributeError:
                    w, h = draw_text.textsize(text, font=font)
                    return (qr_w - w) // 2

            # Draw Site Name (Brand Blue)
            draw_text.text((get_text_x(site_text, font_title), qr_h + 10), site_text, fill=(32, 48, 111, 255), font=font_title)
            
            # Draw Location & Area (Slate Grey)
            draw_text.text((get_text_x(loc_text, font_sub), qr_h + 50), loc_text, fill=(100, 116, 139, 255), font=font_sub)

            # 🌟 SAVING 🌟
            buffer = BytesIO()
            canvas.save(buffer, format="PNG")
            file_name = f"qr_{self.name.replace(' ', '_')}_{self.qr_token}.png"
            self.qr_image.save(file_name, File(buffer), save=False)

        super().save(*args, **kwargs)