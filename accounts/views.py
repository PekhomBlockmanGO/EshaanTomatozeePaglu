import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image
import base64
from io import BytesIO

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.db.models import Count

from tickets.models import Ticket, TicketLog
from masters.models import Site, Area, Location, SpecificArea
from .models import EmergencyContact


# 🔹 Centralized Role Helper
def get_user_role(user):
    if user.is_superuser:
        return "Admin"
    elif user.groups.filter(name__iexact="Manager").exists():
        return "Manager"
    return "Client"


# 🔹 Daily Insights
@login_required
def daily_insights(request):
    role = get_user_role(request.user)

    today = timezone.localdate()
    today_tickets = Ticket.objects.filter(created_at__date=today)
    total_today = today_tickets.count()

    category_data = (
        today_tickets
        .values("category")
        .annotate(count=Count("id"))
        .order_by("category")
    )

    status_data = (
        today_tickets
        .values("status")
        .annotate(count=Count("id"))
    )

    status_percentages = {}
    for item in status_data:
        if total_today > 0:
            status_percentages[item["status"]] = round((item["count"] / total_today) * 100, 1)
        else:
            status_percentages[item["status"]] = 0

    context = {
        "role": role,
        "page_title": "Daily Insights",
        "total_today": total_today,
        "category_labels": [c["category"] for c in category_data],
        "category_counts": [c["count"] for c in category_data],
        "status_labels": list(status_percentages.keys()),
        "status_percentages": list(status_percentages.values()),
    }

    return render(request, "accounts/daily_insights.html", context)


# 🔹 Operational Analytics
@login_required
def operational_analytics(request):
    role = get_user_role(request.user)

    all_tickets = Ticket.objects.all()
    total_tickets = all_tickets.count()

    category_data = (
        all_tickets
        .values("category")
        .annotate(count=Count("id"))
        .order_by("category")
    )

    status_data = (
        all_tickets
        .values("status")
        .annotate(count=Count("id"))
    )

    status_percentages = {}
    for item in status_data:
        if total_tickets > 0:
            status_percentages[item["status"]] = round((item["count"] / total_tickets) * 100, 1)
        else:
            status_percentages[item["status"]] = 0

    context = {
        "role": role,
        "page_title": "Operational Analytics",
        "total_tickets": total_tickets,
        "category_labels": [c["category"] for c in category_data],
        "category_counts": [c["count"] for c in category_data],
        "status_labels": list(status_percentages.keys()),
        "status_percentages": list(status_percentages.values()),
    }

    return render(request, "accounts/operational_analytics.html", context)


# 🔹 Update Ticket Status
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
            if new_index >= current_index:
                ticket.status = new_status
            else:
                return redirect("accounts:dashboard")

        if new_status == "Delayed" and new_remarks:
            ticket.remarks = new_remarks

        ticket.save()

        if old_status != new_status:
            TicketLog.objects.create(
                ticket=ticket,
                status=new_status,
                remarks=new_remarks if new_status == "Delayed"
                else f"Status updated by {user.username}"
            )

    return redirect("accounts:dashboard")


# 🔹 Delete Ticket
@login_required
def delete_ticket(request, ticket_id):
    if request.user.is_superuser and request.method == "POST":
        ticket = get_object_or_404(Ticket, id=ticket_id)
        ticket.delete()
    return redirect("accounts:dashboard")


# 🔥 Audit Logs with Resolution Time
@login_required
def audit_logs(request):
    role = get_user_role(request.user)

    if role not in ["Admin", "Manager"]:
        return redirect("accounts:dashboard")

    logs = TicketLog.objects.select_related('ticket').order_by('-timestamp')

    for log in logs:
        log.time_taken_hours = None
        if log.status == "Closed" and log.ticket.created_at:
            diff = log.timestamp - log.ticket.created_at
            log.time_taken_hours = round(diff.total_seconds() / 3600, 2)

    return render(request, "accounts/audit_logs.html", {
        "logs": logs,
        "role": role
    })


# 🔹 Manage Masters
@login_required
def manage_masters(request):
    role = get_user_role(request.user)

    if role != "Admin":
        messages.error(request, "Admins only.")
        return redirect("accounts:dashboard")

    context = {
        "role": role,
        "sites": Site.objects.all(),
        "areas": Area.objects.all(),
        "locations": Location.objects.all(),
        "specific_areas": SpecificArea.objects.all(),
        "users": User.objects.all(),
        "groups": Group.objects.all(),
        "emergency_contact": EmergencyContact.objects.first(), 
    }

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "add_site":
            site_name = request.POST.get("site_name")
            if site_name:
                Site.objects.create(name=site_name)

        elif form_type == "add_area":
            site_id = request.POST.get("site_id")
            area_name = request.POST.get("area_name")
            if site_id and area_name:
                site = get_object_or_404(Site, id=site_id)
                Area.objects.create(site=site, name=area_name)

        elif form_type == "add_location":
            area_id = request.POST.get("area_id")
            location_name = request.POST.get("location_name")
            if area_id and location_name:
                area = get_object_or_404(Area, id=area_id)
                Location.objects.create(area=area, name=location_name)

        elif form_type == "add_specific_area":
            specific_area_name = request.POST.get("specific_area_name")
            if specific_area_name:
                SpecificArea.objects.create(name=specific_area_name)

        elif form_type == "generate_qr":
            qr_site = request.POST.get("qr_site")
            qr_area = request.POST.get("qr_area")
            qr_location = request.POST.get("qr_location")
            qr_room = request.POST.get("qr_room")

            if qr_site and qr_area and qr_location and qr_room:
                site = get_object_or_404(Site, id=qr_site)
                area = get_object_or_404(Area, id=qr_area)
                location = get_object_or_404(Location, id=qr_location)
                room = get_object_or_404(SpecificArea, id=qr_room)

                qr_text = f"Site: {site.name}\nBuilding: {area.name}\nFloor: {location.name}\nRoom: {room.name}"
                
                qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_H, box_size=10, border=4)
                qr.add_data(qr_text)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")
                
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                qr_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                
                context["qr_data"] = qr_base64
                context["qr_site_name"] = site.name
                context["qr_location_name"] = location.name
                context["qr_room_name"] = room.name
                
                return render(request, "accounts/manage_masters.html", context)

        elif form_type == "create_user":
            username = request.POST.get("username")
            email = request.POST.get("email")
            password = request.POST.get("password")
            is_superuser = request.POST.get("is_superuser") == "on"
            group_ids = request.POST.getlist("groups")

            if username and password:
                if not User.objects.filter(username=username).exists():
                    user = User.objects.create_user(username=username, email=email, password=password)
                    user.is_superuser = is_superuser
                    user.is_staff = is_superuser 
                    user.save()
                    if group_ids:
                        user.groups.set(group_ids)

        elif form_type == "delete_user":
            user_id = request.POST.get("user_id")
            if user_id:
                User.objects.filter(id=user_id).delete()

        elif form_type == "create_group":
            group_name = request.POST.get("group_name")
            if group_name:
                Group.objects.get_or_create(name=group_name)

        elif form_type == "delete_group":
            group_id = request.POST.get("group_id")
            if group_id:
                Group.objects.filter(id=group_id).delete()

        # --- STRICT 10-DIGIT EMERGENCY NUMBER LOGIC ---
        elif form_type == "update_emergency":
            phone_number = request.POST.get("phone_number", "").strip()
            
            # Check if it's exactly 10 characters and all numbers!
            if phone_number.isdigit() and len(phone_number) == 10:
                contact, created = EmergencyContact.objects.get_or_create(id=1)
                contact.phone_number = phone_number
                contact.save()
                context["emergency_contact"] = contact 
                messages.success(request, "Emergency number saved!")
            else:
                messages.error(request, "Error: Phone number must be exactly 10 digits.")

        # Update context data again
        context["sites"] = Site.objects.all()
        context["areas"] = Area.objects.all()
        context["locations"] = Location.objects.all()
        context["specific_areas"] = SpecificArea.objects.all()
        context["users"] = User.objects.all()
        context["groups"] = Group.objects.all()

    return render(request, "accounts/manage_masters.html", context)


# 🔹 Manage Users
@login_required
def manage_users(request):
    if not request.user.is_superuser:
        messages.error(request, "Admins only.")
        return redirect("accounts:dashboard")

    return render(request, "accounts/manage_users.html", {
        "users": User.objects.all(),
        "groups": Group.objects.all(),
    })


# 🔹 Manage Groups
@login_required
def manage_groups(request):
    if not request.user.is_superuser:
        messages.error(request, "Admins only.")
        return redirect("accounts:dashboard")

    return render(request, "accounts/manage_groups.html", {
        "groups": Group.objects.all(),
    })


def emergency_view(request):
    contact = EmergencyContact.objects.first()
    return render(request, "accounts/emergency.html", {
        "contact": contact
    })

# 🔹 Dashboard
@login_required
def dashboard(request):
    role = get_user_role(request.user)
    tickets = Ticket.objects.all()

    return render(request, "accounts/dashboard.html", {
        "tickets": tickets,
        "role": role,
        "server_time": timezone.now().isoformat(),  
    })