from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class VehicleCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'vehicle categories'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Vehicle(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'AVAILABLE', 'Available'
        RESERVED = 'RESERVED', 'Reserved'
        RENTED = 'RENTED', 'Rented'
        MAINTENANCE = 'MAINTENANCE', 'Maintenance'
        DAMAGED = 'DAMAGED', 'Damaged'
        UNAVAILABLE = 'UNAVAILABLE', 'Unavailable'

    class Transmission(models.TextChoices):
        AUTOMATIC = 'AUTOMATIC', 'Automatic'
        MANUAL = 'MANUAL', 'Manual'

    class FuelType(models.TextChoices):
        PETROL = 'PETROL', 'Petrol'
        DIESEL = 'DIESEL', 'Diesel'
        ELECTRIC = 'ELECTRIC', 'Electric'
        HYBRID = 'HYBRID', 'Hybrid'

    category = models.ForeignKey(VehicleCategory, on_delete=models.PROTECT, related_name='vehicles')
    name = models.CharField(max_length=150)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField()
    registration_number = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    price_per_day = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    security_deposit = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    transmission = models.CharField(max_length=20, choices=Transmission.choices)
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices)
    number_of_seats = models.PositiveSmallIntegerField(default=5)
    color = models.CharField(max_length=50, blank=True)
    mileage = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='vehicles/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)
    featured = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-featured', 'brand', 'model')

    def __str__(self):
        return f'{self.year} {self.brand} {self.model}'

    def get_absolute_url(self):
        return reverse('vehicles:detail', args=[self.pk])

    @property
    def is_demo_listing(self):
        return self.registration_number.startswith('DEMO-')

    @property
    def has_ai_image(self):
        return bool(self.image and self.image.name.startswith('vehicles/ai-showcase/'))

    def sync_booking_status(self):
        """Keep operational holds, otherwise derive status from all live rentals."""
        if self.status in {self.Status.MAINTENANCE, self.Status.DAMAGED, self.Status.UNAVAILABLE}:
            return
        if self.bookings.filter(status__in=['ACTIVE', 'OVERDUE']).exists():
            self.status = self.Status.RENTED
        elif self.bookings.filter(status__in=['CONFIRMED', 'READY_FOR_PICKUP']).exists():
            self.status = self.Status.RESERVED
        else:
            self.status = self.Status.AVAILABLE
        self.save(update_fields=['status'])


class SavedVehicle(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_vehicles')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [models.UniqueConstraint(fields=['customer', 'vehicle'], name='unique_customer_saved_vehicle')]

    def __str__(self):
        return f'{self.customer} saved {self.vehicle}'
