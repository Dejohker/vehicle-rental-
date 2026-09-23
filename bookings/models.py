import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


def booking_reference():
    return f'VR-{timezone.now():%Y}-{uuid.uuid4().hex[:6].upper()}'


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        READY_FOR_PICKUP = 'READY_FOR_PICKUP', 'Ready for pickup'
        ACTIVE = 'ACTIVE', 'Active'
        RETURNED = 'RETURNED', 'Returned'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REJECTED = 'REJECTED', 'Rejected'
        OVERDUE = 'OVERDUE', 'Overdue'

    ACTIVE_STATUSES = [Status.PENDING, Status.CONFIRMED, Status.READY_FOR_PICKUP, Status.ACTIVE, Status.OVERDUE]
    TRANSITIONS = {
        Status.PENDING: {Status.CONFIRMED, Status.REJECTED, Status.CANCELLED},
        Status.CONFIRMED: {Status.READY_FOR_PICKUP, Status.CANCELLED},
        Status.READY_FOR_PICKUP: {Status.ACTIVE, Status.CANCELLED},
        Status.ACTIVE: {Status.RETURNED, Status.OVERDUE},
        Status.OVERDUE: {Status.RETURNED},
        Status.RETURNED: {Status.COMPLETED},
    }

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='bookings')
    vehicle = models.ForeignKey('vehicles.Vehicle', on_delete=models.PROTECT, related_name='bookings')
    booking_reference = models.CharField(max_length=30, unique=True, default=booking_reference, editable=False)
    pickup_date = models.DateField()
    return_date = models.DateField()
    number_of_days = models.PositiveIntegerField(editable=False)
    rental_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    security_deposit = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)
        indexes = [models.Index(fields=['vehicle', 'pickup_date', 'return_date', 'status'])]

    def __str__(self):
        return self.booking_reference

    @property
    def amount_paid(self):
        return self.payments.filter(payment_status__in=['PAID', 'PARTIAL']).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    @property
    def extra_charges(self):
        try:
            return self.vehicle_return.final_extra_charge
        except VehicleReturn.DoesNotExist:
            return Decimal('0')

    @property
    def amount_due(self):
        if self.status in {self.Status.CANCELLED, self.Status.REJECTED}:
            return Decimal('0')
        return self.total_amount + self.extra_charges

    @property
    def outstanding_balance(self):
        return max(self.amount_due - self.amount_paid, Decimal('0'))

    def clean(self):
        errors = {}
        original = None if self._state.adding else Booking.objects.get(pk=self.pk)
        if original:
            snapshot_fields = ('customer_id', 'vehicle_id', 'pickup_date', 'return_date',
                               'number_of_days', 'rental_amount', 'security_deposit', 'total_amount')
            if any(getattr(self, field) != getattr(original, field) for field in snapshot_fields):
                errors['__all__'] = 'Booked dates, customer, vehicle and agreed prices cannot be changed. Cancel and create a new booking.'
            if self.status != original.status and not getattr(self, '_transitioning', False):
                errors['status'] = 'Use the booking management workflow to change status.'
        elif self.status != self.Status.PENDING:
            errors['status'] = 'New bookings must start as pending.'
        if self._state.adding and self.pickup_date and self.pickup_date < timezone.localdate():
            errors['pickup_date'] = 'Pickup date cannot be in the past.'
        if self.pickup_date and self.return_date and self.return_date <= self.pickup_date:
            errors['return_date'] = 'Return date must be after pickup date.'
        if self._state.adding and self.vehicle_id:
            if not self.vehicle.active or self.vehicle.status in {'MAINTENANCE', 'DAMAGED', 'UNAVAILABLE'}:
                errors['__all__'] = 'This vehicle is not available for booking.'
            if self.pickup_date and self.return_date:
                overlap = Booking.objects.filter(
                    vehicle_id=self.vehicle_id, status__in=self.ACTIVE_STATUSES,
                    pickup_date__lt=self.return_date, return_date__gt=self.pickup_date,
                ).exclude(pk=self.pk).exists()
                if overlap:
                    errors['return_date'] = 'Vehicle is unavailable for the selected dates.'
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self._state.adding and self.pickup_date and self.return_date and self.vehicle_id:
            self.number_of_days = (self.return_date - self.pickup_date).days
            self.security_deposit = self.vehicle.security_deposit
            self.rental_amount = self.vehicle.price_per_day * self.number_of_days
            self.total_amount = self.rental_amount + self.security_deposit
        self.full_clean()
        super().save(*args, **kwargs)

    def transition_to(self, new_status):
        from vehicles.models import Vehicle

        with transaction.atomic():
            vehicle = Vehicle.objects.select_for_update().get(pk=self.vehicle_id)
            current = Booking.objects.select_for_update().get(pk=self.pk)
            if new_status not in self.TRANSITIONS.get(current.status, set()):
                raise ValidationError(f'Cannot change booking from {current.get_status_display()} to {dict(self.Status.choices).get(new_status, new_status)}.')
            if new_status in {self.Status.CONFIRMED, self.Status.READY_FOR_PICKUP, self.Status.ACTIVE}:
                if not vehicle.active or vehicle.status in {Vehicle.Status.MAINTENANCE, Vehicle.Status.DAMAGED, Vehicle.Status.UNAVAILABLE}:
                    raise ValidationError('This vehicle is not available for pickup or confirmation.')
            if new_status == self.Status.ACTIVE and vehicle.bookings.filter(
                status__in=[self.Status.ACTIVE, self.Status.OVERDUE],
            ).exclude(pk=self.pk).exists():
                raise ValidationError('This vehicle is still on another rental. Process its return first.')
            if new_status == self.Status.RETURNED and not VehicleReturn.objects.filter(booking=current).exists():
                raise ValidationError('Use Process return to record the vehicle condition and charges first.')
            current.status = new_status
            current._transitioning = True
            current.save(update_fields=['status', 'updated_at'])
            if new_status == self.Status.RETURNED and current.vehicle_return.damage_reported:
                vehicle.status = Vehicle.Status.DAMAGED
                vehicle.save(update_fields=['status'])
            vehicle.sync_booking_status()
        self.refresh_from_db()


class VehicleReturn(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name='vehicle_return')
    expected_return_date = models.DateField()
    actual_return_date = models.DateField()
    condition_notes = models.TextField(blank=True)
    damage_reported = models.BooleanField(default=False)
    damage_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    late_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    additional_charge = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='processed_returns')
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        errors = {}
        if self.actual_return_date:
            if self.booking_id and self.actual_return_date < self.booking.pickup_date:
                errors['actual_return_date'] = 'Actual return cannot be before pickup.'
            elif self.actual_return_date > timezone.localdate():
                errors['actual_return_date'] = 'Actual return cannot be in the future.'
        if self.damage_charge and not self.damage_reported:
            errors['damage_reported'] = 'Mark damage reported when recording a damage charge.'
        if errors:
            raise ValidationError(errors)

    @property
    def late_days(self):
        return max((self.actual_return_date - self.expected_return_date).days, 0)

    @property
    def final_extra_charge(self):
        return self.late_fee + self.damage_charge + self.additional_charge

    def __str__(self):
        return f'Return for {self.booking}'
