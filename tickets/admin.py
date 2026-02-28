from django.contrib import admin
from .models import Ticket

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    # 🌟 Replaced 'floor' with 'area' to match your new system!
    list_display = ('id', 'location', 'area', 'specific_area', 'category', 'priority', 'status', 'created_at')
    list_filter = ('status', 'priority', 'category', 'site')
    search_fields = ('description', 'reporter_phone')