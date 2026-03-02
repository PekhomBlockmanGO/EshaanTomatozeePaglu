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


# 🔹 Manage Masters (RESTORED)
@login_required
def manage_masters(request):
    role = get_user_role(request.user)

    if role != "Admin":
        messages.error(request, "Admins only.")
        return redirect("accounts:dashboard")

    return render(request, "accounts/manage_masters.html", {
        "role": role,
        "sites": Site.objects.all(),
        "areas": Area.objects.all(),
        "locations": Location.objects.all(),
        "specific_areas": SpecificArea.objects.all(),
        "users": User.objects.all(),
        "groups": Group.objects.all(),
    })


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

from .models import EmergencyContact

def emergency_view(request):
    contact = EmergencyContact.objects.first()
    return render(request, "accounts/emergency.html", {
        "contact": contact
    })

# 🔹 Dashboard (FIXED + Notification Ready)
@login_required
def dashboard(request):
    role = get_user_role(request.user)
    tickets = Ticket.objects.all()

    return render(request, "accounts/dashboard.html", {
        "tickets": tickets,
        "role": role,
        "server_time": timezone.now().isoformat(),  # 🔥 Important for notifications
    })