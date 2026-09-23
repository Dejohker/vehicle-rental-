from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Payment(models.Model):
    class Method(models.TextChoices):
        BANK_TRANSFER = 'BANK_TRANSFER', 'Bank transfer'
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Card'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        PARTIAL = 'PARTIAL', 'Partial'
        PAID = 'PAID', 'Paid'
        FAILED = 'FAILED', 'Failed'
        REFUNDED = 'REFUNDED', 'Refunded'

    booking = models.ForeignKey('bookings.Booking', on_delete=models.PROTECT, related_name='payments')
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)])
    payment_method = models.CharField(max_length=20, choices=Method.choices)
    transaction_reference = models.CharField(max_length=100, unique=True)
    payment_status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_date = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-payment_date',)

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.booking_id and self.customer_id and self.booking.customer_id != self.customer_id:
            raise ValidationError({'customer': 'Customer must match the booking customer.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.transaction_reference
