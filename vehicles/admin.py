from django.contrib import admin
from .models import Vehicle, VehicleCategory


@admin.register(VehicleCategory)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    list_filter = ('active',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'brand', 'model', 'category', 'price_per_day', 'status', 'active', 'featured')
    search_fields = ('registration_number', 'brand', 'model', 'name')
    list_filter = ('status', 'active', 'featured', 'category', 'transmission', 'fuel_type')
