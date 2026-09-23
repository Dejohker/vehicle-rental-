from django.contrib import admin
from .models import Booking, VehicleReturn


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_reference', 'customer', 'vehicle', 'pickup_date', 'return_date', 'total_amount', 'status')
    search_fields = ('booking_reference', 'customer__username', 'vehicle__registration_number')
    list_filter = ('status', 'pickup_date', 'return_date')
    readonly_fields = ('number_of_days', 'rental_amount', 'security_deposit', 'total_amount', 'status')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('customer', 'vehicle', 'pickup_date', 'return_date')
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VehicleReturn)
class VehicleReturnAdmin(admin.ModelAdmin):
    list_display = ('booking', 'expected_return_date', 'actual_return_date', 'damage_reported', 'processed_by')
    list_filter = ('damage_reported', 'actual_return_date')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
