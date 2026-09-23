from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_reference', 'booking', 'customer', 'amount', 'payment_method', 'payment_status', 'payment_date')
    search_fields = ('transaction_reference', 'booking__booking_reference', 'customer__username')
    list_filter = ('payment_status', 'payment_method', 'payment_date')
