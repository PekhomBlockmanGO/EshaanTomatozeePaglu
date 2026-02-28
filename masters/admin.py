from django.contrib import admin
from django.utils.html import mark_safe
from .models import Site, Area, Location, SpecificArea # 🌟 Imported SpecificArea!

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'state', 'active')

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'site')
    list_filter = ('site',)

# 🌟 NEW: Registered SpecificArea so it shows up under the MASTERS menu!
admin.site.register(SpecificArea)

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    # 🌟 Added 'specific_area' so you can see it in your Locations table!
    list_display = ('name', 'area', 'get_site', 'floor', 'specific_area', 'qr_enabled', 'qr_preview')
    
    # 🌟 Added it to the filters so you can sort by Area!
    list_filter = ('area', 'specific_area', 'qr_enabled') 
    search_fields = ('name', 'qr_token')
    readonly_fields = ('qr_preview',)

    def get_site(self, obj):
        if obj.area and obj.area.site:
            return obj.area.site.name
        return "-"
    get_site.short_description = 'Building'

    def qr_preview(self, obj):
        if obj.qr_image:
            return mark_safe(f'<a href="{obj.qr_image.url}" target="_blank"><img src="{obj.qr_image.url}" width="50" height="50" style="border-radius: 5px;"/></a>')
        return "-"
    qr_preview.short_description = 'QR Code'