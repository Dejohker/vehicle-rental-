from django.contrib import admin
from .models import CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'city', 'country', 'created_at')
    search_fields = ('user__username', 'user__email', 'phone_number', 'driver_license_number')
    list_filter = ('country', 'state')
