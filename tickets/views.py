from django.shortcuts import render, get_object_or_404
from masters.models import Location, Area # 🌟 Added Area import!
from .forms import QRComplaintForm
from .models import TicketLog

def qr_complaint_view(request, token=None):
    location_obj = None
    is_qr = False
    initial_data = {}
    
    # 🌟 This will be the default title if someone visits without scanning a QR code
    site_name = "New Docket Form" 

    if token:
        location_obj = get_object_or_404(Location, qr_token=token, qr_enabled=True)
        initial_data = {
            'area': location_obj.area,              
            'location': location_obj,               
            'specific_area': getattr(location_obj, 'specific_area', None) 
        }
        site_name = location_obj.area.site.name # Grab Site Name from legacy QR
        is_qr = True
        
    elif request.GET.get('area') and request.GET.get('location'):
        area_id = request.GET.get('area')
        area_obj = get_object_or_404(Area, id=area_id)
        
        site_name = area_obj.site.name # 🌟 Grab Site Name from our New Dynamic QR!
        
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
            
            # 🌟 Automatically attach the correct Site based on the Building they selected!
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

    return render(request, 'tickets/complaint_form.html', {
        'form': form, 
        'is_qr': is_qr, 
        'location_obj': location_obj,
        'site_name': site_name # 🌟 Passing the Dynamic Name to your HTML!
    })