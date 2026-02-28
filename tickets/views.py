from django.shortcuts import render, get_object_or_404
from masters.models import Location
from .forms import QRComplaintForm

def qr_complaint_view(request, token=None):
    location_obj = None
    is_qr = False
    initial_data = {}

    if token:
        location_obj = get_object_or_404(Location, qr_token=token, qr_enabled=True)
        initial_data = {
            'area': location_obj.area,              
            'location': location_obj,               
            'specific_area': location_obj.specific_area 
        }
        is_qr = True

    if request.method == 'POST':
        form = QRComplaintForm(request.POST, request.FILES, initial=initial_data, is_qr=is_qr)
        if form.is_valid():
            ticket = form.save(commit=False)
            
            # 🌟 THE FIX: Ensure the Site is ALWAYS filled!
            if is_qr:
                ticket.site = location_obj.area.site 
                ticket.area = location_obj.area
                ticket.location = location_obj
                ticket.specific_area = location_obj.specific_area
                ticket.source = 'QR'
            else:
                # For manual entry, trace the Site from the selected Location!
                ticket.site = ticket.location.area.site
                ticket.source = 'Manual'
                
            ticket.save()
            return render(request, 'tickets/success.html', {'location': ticket.location})
    else:
        form = QRComplaintForm(initial=initial_data, is_qr=is_qr)

    return render(request, 'tickets/complaint_form.html', {
        'form': form, 
        'is_qr': is_qr, 
        'location_obj': location_obj
    })