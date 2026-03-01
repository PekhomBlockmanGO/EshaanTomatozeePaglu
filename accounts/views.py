import qrcode
from qrcode.constants import ERROR_CORRECT_H 
from PIL import Image, ImageDraw
import requests # 🌟 NEW: To download your logo!
import base64
from io import BytesIO
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from tickets.models import Ticket, TicketLog 
from masters.models import Site, Area, Location, SpecificArea 

@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser: role = "Admin"
    elif user.groups.filter(name__iexact="Manager").exists(): role = "Manager"
    else: role = "Client"

    tickets = Ticket.objects.all()
    return render(request, "accounts/dashboard.html", {"tickets": tickets, "role": role})

@login_required
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    user = request.user

    if not (user.is_superuser or user.groups.filter(name__iexact="Manager").exists()):
        messages.error(request, "You do not have permission.")
        return redirect("accounts:dashboard")

    if request.method == "POST":
        new_status = request.POST.get("status")
        new_remarks = request.POST.get("remarks", "").strip()
        STATUS_FLOW = ["Open", "Attended", "In Progress", "Delayed", "Closed"]

        if new_status not in STATUS_FLOW:
            return redirect("accounts:dashboard")

        current_index = STATUS_FLOW.index(ticket.status)
        new_index = STATUS_FLOW.index(new_status)
        old_status = ticket.status

        if user.is_superuser:
            ticket.status = new_status
        elif user.groups.filter(name__iexact="Manager").exists():
            if new_index >= current_index: ticket.status = new_status
            else: return redirect("accounts:dashboard")

        if new_status == "Delayed" and new_remarks:
            ticket.remarks = new_remarks

        ticket.save()

        if old_status != new_status:
            TicketLog.objects.create(
                ticket=ticket, status=new_status,
                remarks=new_remarks if new_status == "Delayed" else f"Status updated by {user.username}"
            )

    return redirect("accounts:dashboard")

@login_required
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.user.is_superuser and request.method == "POST":
        ticket.delete()
    return redirect("accounts:dashboard")

@login_required
def audit_logs(request):
    user = request.user
    if not (user.is_superuser or user.groups.filter(name__iexact="Manager").exists()):
        return redirect("accounts:dashboard")
    
    logs = TicketLog.objects.select_related('ticket').order_by('-timestamp')
    return render(request, "accounts/audit_logs.html", {"logs": logs})

@login_required
def manage_masters(request):
    if not request.user.is_superuser:
        messages.error(request, "Only Admins can manage locations.")
        return redirect("accounts:dashboard")

    qr_data, qr_site_name, qr_location_name, qr_room_name = None, "", "", ""

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "add_site":
            name = request.POST.get("site_name")
            if name: Site.objects.create(name=name)
            return redirect("accounts:manage_masters")

        elif form_type == "add_area":
            name = request.POST.get("area_name")
            site_id = request.POST.get("site_id")
            if name and site_id: Area.objects.create(name=name, site_id=site_id)
            return redirect("accounts:manage_masters")

        elif form_type == "add_location":
            name = request.POST.get("location_name")
            area_id = request.POST.get("area_id")
            if name and area_id: Location.objects.create(name=name, area_id=area_id)
            return redirect("accounts:manage_masters")

        elif form_type == "add_specific_area":
            name = request.POST.get("specific_area_name")
            if name: SpecificArea.objects.create(name=name)
            return redirect("accounts:manage_masters")

        # 🌟 THE CUSTOM LOGO QR GENERATOR 🌟
        elif form_type == "generate_qr":
            site_id = request.POST.get("qr_site")
            area_id = request.POST.get("qr_area")
            location_id = request.POST.get("qr_location")
            room_id = request.POST.get("qr_room")

            if site_id and area_id and location_id and room_id:
                site = Site.objects.get(id=site_id)
                area = Area.objects.get(id=area_id)
                location = Location.objects.get(id=location_id)
                room = SpecificArea.objects.get(id=room_id)

                qr_site_name, qr_location_name, qr_room_name = site.name, location.name, room.name

                base_url = request.build_absolute_uri('/report/') 
                qr_url = f"{base_url}?area={area.id}&location={location.id}&room={room.id}"

                # 1. Create a High Error-Correction QR Code
                qr = qrcode.QRCode(version=4, error_correction=ERROR_CORRECT_H, box_size=10, border=4)
                qr.add_data(qr_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="#20306F", back_color="white").convert('RGBA')

                # 2. Fetch the actual logo from the URL
                logo_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSsOxFqQOfjBCzhQOpRW-3m7REbVWQFOiz2iQ&s"
                try:
                    response = requests.get(logo_url)
                    logo = Image.open(BytesIO(response.content)).convert("RGBA")
                    
                    # Resize logo to 25% of QR code so it doesn't break readability
                    img_w, img_h = img.size
                    logo_size = int(img_w * 0.25)
                    
                    # Use LANCZOS for high-quality resizing (previously ANTIALIAS)
                    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS)
                    
                    # Create a white background box slightly larger than the logo for contrast
                    bg_size = int(logo_size + (logo_size * 0.1)) # 10% padding
                    white_bg = Image.new("RGBA", (bg_size, bg_size), "white")
                    
                    # Calculate center position for logo on the white bg
                    logo_pos_in_bg = ((bg_size - logo_size) // 2, (bg_size - logo_size) // 2)
                    white_bg.paste(logo, logo_pos_in_bg, logo) # Use logo as mask to keep transparent background clean

                    # 3. Paste the whole block directly into the center of the QR code!
                    pos = ((img_w - bg_size) // 2, (img_h - bg_size) // 2)
                    img.paste(white_bg, pos)
                except Exception as e:
                    print(f"Failed to fetch or embed logo: {e}")
                    # If it fails, it just skips drawing the logo and outputs a normal QR code

                # Save it
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                qr_data = base64.b64encode(buffer.getvalue()).decode()

    return render(request, "accounts/manage_masters.html", {
        "sites": Site.objects.all(),
        "areas": Area.objects.all(),
        "locations": Location.objects.all(),
        "specific_areas": SpecificArea.objects.all(),
        "qr_data": qr_data,
        "qr_site_name": qr_site_name,
        "qr_location_name": qr_location_name,
        "qr_room_name": qr_room_name,
    })