from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from masters.models import Location, Area
from .forms import QRComplaintForm
from .models import TicketLog, Ticket
from accounts.models import EmergencyContact  # 👈 Added the import here!


# --- QR / MANUAL COMPLAINT VIEW ---
def qr_complaint_view(request, token=None):
    location_obj = None
    is_qr = False
    initial_data = {}
    site_name = "New Docket Form"

    if token:
        location_obj = get_object_or_404(Location, qr_token=token, qr_enabled=True)
        initial_data = {
            'area': location_obj.area,
            'location': location_obj,
            'specific_area': getattr(location_obj, 'specific_area', None)
        }
        site_name = location_obj.area.site.name
        is_qr = True

    elif request.GET.get('area') and request.GET.get('location'):
        area_id = request.GET.get('area')
        area_obj = get_object_or_404(Area, id=area_id)

        site_name = area_obj.site.name

        initial_data = {
            'area': area_id,
            'location': request.GET.get('location'),
            'specific_area': request.GET.get('room'),
        }
        is_qr = True

    if request.method == 'POST':
        form = QRComplaintForm(request.POST, request.FILES, initial=initial_data, is_qr=is_qr)

        if form.is_valid():
            ticket = form.save(commit=False)

            if ticket.area:
                ticket.site = ticket.area.site

            ticket.source = 'QR' if is_qr else 'Manual'
            ticket.save()

            TicketLog.objects.create(
                ticket=ticket,
                status='Open',
                remarks='Ticket Created via Docket Form'
            )

            return render(request, 'tickets/success.html', {'location': ticket.location})
    else:
        form = QRComplaintForm(initial=initial_data, is_qr=is_qr)

    # 👇 Fetch the emergency number from the database 👇
    emergency_contact = EmergencyContact.objects.first()

    return render(request, 'tickets/complaint_form.html', {
        'form': form,
        'is_qr': is_qr,
        'location_obj': location_obj,
        'site_name': site_name,
        'emergency_contact': emergency_contact  # 👈 Passed it to your HTML here!
    })


# --- CLEAN NOTIFICATION CHECKER ---
def check_new_tickets(request):
    last_check_str = request.GET.get("last_check")

    if not last_check_str:
        return JsonResponse({
            "new": False,
            "timestamp": timezone.now().isoformat()
        })

    last_check = parse_datetime(last_check_str)

    if not last_check:
        return JsonResponse({
            "new": False,
            "timestamp": timezone.now().isoformat()
        })

    # Ensure timezone aware
    if timezone.is_naive(last_check):
        last_check = timezone.make_aware(last_check)

    latest_ticket = Ticket.objects.filter(
        created_at__gt=last_check
    ).order_by("-created_at").first()

    if latest_ticket:
        return JsonResponse({
            "new": True,
            "latest_id": latest_ticket.id,
            "timestamp": timezone.now().isoformat()
        })

    return JsonResponse({
        "new": False,
        "timestamp": timezone.now().isoformat()
    })


# --- EMERGENCY VIEW ---
def emergency_view(request):
    contact = EmergencyContact.objects.first()

    return render(request, "tickets/emergency.html", {
        "contact": contact
    })