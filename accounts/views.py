from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from tickets.models import Ticket

@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser:
        role = "Admin"
    elif user.groups.filter(name__iexact="Manager").exists():
        role = "Manager"
    else:
        role = "Client"

    tickets = Ticket.objects.all()

    return render(request, "accounts/dashboard.html", {
        "tickets": tickets,
        "role": role
    })

@login_required
def update_ticket_status(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    user = request.user

    if not (user.is_superuser or user.groups.filter(name__iexact="Manager").exists()):
        messages.error(request, "You do not have permission.")
        return redirect("accounts:dashboard") # 🌟 Fixed Redirect

    if request.method == "POST":
        new_status = request.POST.get("status")
        new_remarks = request.POST.get("remarks", "").strip()

        STATUS_FLOW = ["Open", "Attended", "In Progress", "Delayed", "Closed"]

        if new_status not in STATUS_FLOW:
            messages.error(request, "Invalid status.")
            return redirect("accounts:dashboard") # 🌟 Fixed Redirect

        current_index = STATUS_FLOW.index(ticket.status)
        new_index = STATUS_FLOW.index(new_status)

        if user.is_superuser:
            ticket.status = new_status
        elif user.groups.filter(name__iexact="Manager").exists():
            if new_index >= current_index:
                ticket.status = new_status
            else:
                messages.error(request, "Manager cannot move status backward.")
                return redirect("accounts:dashboard") # 🌟 Fixed Redirect

        if new_status == "Delayed" and new_remarks:
            ticket.remarks = new_remarks

        ticket.save()

    return redirect("accounts:dashboard") # 🌟 Fixed Redirect

@login_required
def delete_ticket(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if not request.user.is_superuser:
        messages.error(request, "Only Admin can delete tickets.")
        return redirect("accounts:dashboard") # 🌟 Fixed Redirect

    if request.method == "POST":
        ticket.delete()

    return redirect("accounts:dashboard") # 🌟 Fixed Redirect