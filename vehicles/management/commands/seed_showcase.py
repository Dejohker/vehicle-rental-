"""Illustrative inventory, not a statement of real fleet availability or market rates."""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from vehicles.models import Vehicle, VehicleCategory


# Brand, model, year, category, illustrative NGN/day, seats.
SHOWCASE_CARS = [
    ('Mercedes-Benz', 'C-Class', 2006, 'Luxury', 65000, 5),
    ('Mercedes-Benz', 'E-Class', 2008, 'Luxury', 80000, 5),
    ('Mercedes-Benz', 'S-Class', 2010, 'Luxury', 130000, 5),
    ('Mercedes-Benz', 'C-Class', 2012, 'Luxury', 95000, 5),
    ('Mercedes-Benz', 'E-Class', 2014, 'Luxury', 120000, 5),
    ('Mercedes-Benz', 'GLE', 2016, 'SUV', 160000, 5),
    ('Mercedes-Benz', 'GLC', 2018, 'SUV', 175000, 5),
    ('Mercedes-Benz', 'G-Class', 2020, 'Luxury', 400000, 5),
    ('Mercedes-Benz', 'S-Class', 2022, 'Luxury', 300000, 5),
    ('Mercedes-Benz', 'AMG GT', 2024, 'Exotic', 550000, 2),
    ('Mercedes-Benz', 'E-Class', 2026, 'Luxury', 250000, 5),
    ('Ferrari', 'F430', 2006, 'Exotic', 450000, 2),
    ('Ferrari', '458 Italia', 2012, 'Exotic', 650000, 2),
    ('Ferrari', '488 GTB', 2017, 'Exotic', 800000, 2),
    ('Ferrari', 'F8 Tributo', 2021, 'Exotic', 950000, 2),
    ('Ferrari', 'Roma', 2023, 'Exotic', 850000, 4),
    ('Rolls-Royce', 'Phantom', 2007, 'Luxury', 550000, 5),
    ('Rolls-Royce', 'Ghost', 2011, 'Luxury', 600000, 5),
    ('Rolls-Royce', 'Wraith', 2015, 'Luxury', 700000, 4),
    ('Rolls-Royce', 'Cullinan', 2020, 'Luxury', 1000000, 5),
    ('Rolls-Royce', 'Ghost', 2024, 'Luxury', 1100000, 5),
    ('Toyota', 'Corolla', 2006, 'Economy', 25000, 5),
    ('Toyota', 'Camry', 2009, 'Sedan', 35000, 5),
    ('Toyota', 'RAV4', 2013, 'SUV', 55000, 5),
    ('Toyota', 'Land Cruiser', 2017, 'SUV', 140000, 7),
    ('Toyota', 'Corolla', 2020, 'Sedan', 50000, 5),
    ('Toyota', 'Camry', 2025, 'Sedan', 100000, 5),
    ('Toyota', 'Corolla', 2026, 'Sedan', 85000, 5),
    ('Honda', 'Civic', 2007, 'Economy', 28000, 5),
    ('Honda', 'Accord', 2010, 'Sedan', 38000, 5),
    ('Honda', 'CR-V', 2014, 'SUV', 60000, 5),
    ('Honda', 'Accord', 2019, 'Sedan', 75000, 5),
    ('Honda', 'Civic', 2023, 'Sedan', 80000, 5),
    ('Honda', 'CR-V', 2026, 'SUV', 120000, 5),
    ('Lexus', 'IS 250', 2008, 'Luxury', 65000, 5),
    ('Lexus', 'RX 350', 2011, 'Luxury', 95000, 5),
    ('Lexus', 'ES 350', 2016, 'Luxury', 110000, 5),
    ('Lexus', 'LX 570', 2020, 'SUV', 220000, 7),
    ('Lexus', 'RX 350', 2025, 'Luxury', 230000, 5),
    ('BMW', '3 Series', 2006, 'Luxury', 65000, 5),
    ('BMW', '5 Series', 2009, 'Luxury', 85000, 5),
    ('BMW', 'X5', 2013, 'SUV', 120000, 5),
    ('BMW', '7 Series', 2018, 'Luxury', 200000, 5),
    ('BMW', 'M4', 2022, 'Exotic', 300000, 4),
    ('BMW', 'X6', 2026, 'Luxury', 320000, 5),
    ('Porsche', '911 Carrera', 2007, 'Exotic', 250000, 4),
    ('Porsche', 'Cayenne', 2012, 'SUV', 180000, 5),
    ('Porsche', 'Panamera', 2016, 'Luxury', 240000, 4),
    ('Porsche', '718 Cayman', 2021, 'Exotic', 320000, 2),
    ('Porsche', 'Macan', 2026, 'SUV', 260000, 5),
    ('Audi', 'A4', 2010, 'Luxury', 70000, 5),
    ('Audi', 'Q7', 2019, 'SUV', 180000, 7),
    ('Bentley', 'Continental GT', 2015, 'Luxury', 500000, 4),
    ('Bentley', 'Bentayga', 2022, 'Luxury', 650000, 5),
    ('Lamborghini', 'Huracan', 2018, 'Exotic', 900000, 2),
    ('Lamborghini', 'Urus', 2023, 'Exotic', 1100000, 5),
    ('Land Rover', 'Range Rover Sport', 2014, 'SUV', 180000, 5),
    ('Land Rover', 'Defender', 2024, 'SUV', 300000, 5),
    ('Nissan', 'Altima', 2017, 'Sedan', 50000, 5),
    ('Ford', 'Mustang', 2020, 'Exotic', 200000, 4),
    ('Hyundai', 'Elantra', 2021, 'Sedan', 60000, 5),
    ('Kia', 'Sportage', 2023, 'SUV', 90000, 5),
    ('Mazda', 'CX-5', 2024, 'SUV', 110000, 5),
]


class Command(BaseCommand):
    help = 'Add the 2006–2026 demo showcase without overwriting existing cars, users or bookings.'

    @transaction.atomic
    def handle(self, *args, **options):
        created_count = 0
        for brand, model, year, category_name, price, seats in SHOWCASE_CARS:
            category, _ = VehicleCategory.objects.get_or_create(name=category_name, defaults={'slug': slugify(category_name)})
            identifier = f'DEMO-{slugify(brand + "-" + model)}-{year}'.upper()
            vehicle, created = Vehicle.objects.get_or_create(registration_number=identifier, defaults={
                'category': category, 'name': f'{brand} {model}', 'brand': brand, 'model': model,
                'year': year, 'description': f'Demo showcase listing for the {year} {brand} {model}. Rental price, deposit and configuration are illustrative; replace with verified fleet details before offering this car to customers.',
                'price_per_day': Decimal(price), 'security_deposit': Decimal(price),
                'transmission': 'AUTOMATIC', 'fuel_type': 'HYBRID' if (brand, model, year) == ('Toyota', 'Camry', 2025) else 'PETROL',
                'number_of_seats': seats,
            })
            created_count += created
        self.stdout.write(self.style.SUCCESS(f'Added {created_count} demo cars. Existing records were preserved. Prices are illustrative.'))
