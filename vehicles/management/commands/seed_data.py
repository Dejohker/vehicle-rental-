from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from bookings.models import Booking
from payments.models import Payment
from vehicles.models import Vehicle, VehicleCategory


class Command(BaseCommand):
    help = 'Create repeatable sample categories, vehicles, customers, bookings and payments.'

    @transaction.atomic
    def handle(self, *args, **options):
        category_names = ['Economy', 'Sedan', 'SUV', 'Luxury', 'Van']
        categories = {}
        for name in category_names:
            categories[name], _ = VehicleCategory.objects.get_or_create(name=name, defaults={'slug': slugify(name), 'description': f'{name} vehicles for comfortable travel.'})
        fleet = [
            ('Toyota', 'Corolla', 'Sedan', 45000), ('Honda', 'Civic', 'Sedan', 48000), ('Toyota', 'RAV4', 'SUV', 70000),
            ('Lexus', 'RX 350', 'Luxury', 120000), ('Kia', 'Picanto', 'Economy', 32000), ('Hyundai', 'Accent', 'Economy', 35000),
            ('Ford', 'Explorer', 'SUV', 95000), ('Mercedes-Benz', 'E-Class', 'Luxury', 150000), ('Toyota', 'Hiace', 'Van', 110000),
            ('Honda', 'CR-V', 'SUV', 78000), ('Nissan', 'Altima', 'Sedan', 50000), ('BMW', 'X5', 'Luxury', 165000),
            ('Suzuki', 'Swift', 'Economy', 33000), ('Kia', 'Carnival', 'Van', 105000), ('Mazda', 'CX-5', 'SUV', 80000),
        ]
        vehicles = []
        for index, (brand, model, category, price) in enumerate(fleet, 1):
            vehicle, _ = Vehicle.objects.get_or_create(registration_number=f'LAG-{index:03d}-VR', defaults={
                'category': categories[category], 'name': f'{brand} {model}', 'brand': brand, 'model': model, 'year': 2021 + index % 5,
                'description': f'A clean, reliable {brand} {model} maintained for safe and comfortable trips.', 'price_per_day': Decimal(price),
                'security_deposit': Decimal('50000'), 'transmission': 'AUTOMATIC', 'fuel_type': 'PETROL',
                'number_of_seats': 7 if category in {'SUV', 'Van'} else 5, 'color': 'Black', 'featured': index <= 6,
            })
            image_name = slugify(f'{brand}-{model}')
            image_path = f'vehicles/{image_name}.png'
            if not vehicle.image and vehicle.image.storage.exists(image_path):
                vehicle.image = image_path
                vehicle.save(update_fields=['image'])
            vehicles.append(vehicle)
        customers = []
        for index in range(1, 6):
            user, created = User.objects.get_or_create(username=f'customer{index}', defaults={'first_name': f'Customer', 'last_name': str(index), 'email': f'customer{index}@example.com'})
            if created:
                user.set_password('DemoPass123!')
                user.save()
            user.profile.phone_number = f'0800000000{index}'
            user.profile.save()
            customers.append(user)
        today = timezone.localdate()
        for index in range(10):
            pickup = today + timedelta(days=2 + index * 5)
            legacy_payment = Payment.objects.filter(transaction_reference=f'SEED-TXN-{index + 1:03d}').first() if index < 4 else None
            if legacy_payment:
                continue
            booking, created = Booking.objects.get_or_create(booking_reference=f'VR-DEMO-{index + 1:03d}', defaults={
                'customer': customers[index % 5], 'vehicle': vehicles[index],
                'pickup_date': pickup, 'return_date': pickup + timedelta(days=3),
            })
            if created and index < 4:
                Payment.objects.create(booking=booking, customer=booking.customer, amount=booking.total_amount, payment_method='BANK_TRANSFER', transaction_reference=f'SEED-TXN-{index + 1:03d}', payment_status='PAID')
        self.stdout.write(self.style.SUCCESS('Sample data created. Customer password: DemoPass123!'))
