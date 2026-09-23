from django.test import Client, TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
from io import StringIO
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
from PIL import Image

from bookings.models import Booking
from payments.models import Payment
from .models import SavedVehicle, Vehicle, VehicleCategory


class ShowcaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_showcase', stdout=StringIO())
        cls.customer = User.objects.create_user('showcase-renter')

    def test_seed_covers_years_and_brands_and_preserves_edits(self):
        self.assertEqual(set(Vehicle.objects.values_list('year', flat=True)), set(range(2006, 2027)))
        brands = set(Vehicle.objects.values_list('brand', flat=True))
        self.assertTrue({'Mercedes-Benz', 'Ferrari', 'Rolls-Royce', 'Honda', 'Lexus', 'Toyota', 'BMW', 'Porsche'} <= brands)
        count = Vehicle.objects.count()
        car = Vehicle.objects.first()
        car.price_per_day = 12345
        car.save()
        call_command('seed_showcase', stdout=StringIO())
        car.refresh_from_db()
        self.assertEqual(Vehicle.objects.count(), count)
        self.assertEqual(car.price_per_day, 12345)
        for car in Vehicle.objects.all():
            car.full_clean()

    def test_generated_images_attach_idempotently_without_replacing_uploads(self):
        cars = list(Vehicle.objects.order_by('pk')[:2])
        cars[1].image = 'vehicles/customer-photo.jpg'
        cars[1].save(update_fields=['image'])
        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            folder = Path(media_root) / 'vehicles/ai-showcase'
            folder.mkdir(parents=True)
            for car in cars:
                Image.new('RGB', (12, 8)).save(folder / f'{car.registration_number.lower()}.png')
            for _ in range(2):
                call_command('attach_showcase_images', stdout=StringIO())
            cars[0].refresh_from_db()
            cars[1].refresh_from_db()
            self.assertTrue(cars[0].has_ai_image)
            self.assertFalse(cars[1].has_ai_image)
            self.assertEqual(cars[1].image.name, 'vehicles/customer-photo.jpg')
            response = self.client.get(cars[0].get_absolute_url())
            self.assertContains(response, 'AI-generated illustration')
            self.assertContains(response, cars[0].image.url)

    def test_public_showcase_filters_and_sorting(self):
        response = self.client.get(reverse('vehicles:showcase'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add to cart')
        self.assertEqual(len(response.context['page_obj']), 12)
        response = self.client.get(reverse('vehicles:showcase'), {'brand': 'Toyota', 'year_min': 2010, 'year_max': 2026, 'sort': 'price_low'})
        cars = list(response.context['page_obj'])
        self.assertTrue(cars)
        self.assertTrue(all(car.brand == 'Toyota' and 2010 <= car.year <= 2026 for car in cars))
        self.assertEqual([car.price_per_day for car in cars], sorted(car.price_per_day for car in cars))

    def test_invalid_year_ranges_and_inactive_inventory(self):
        response = self.client.get(reverse('vehicles:showcase'), {'year_min': 2026, 'year_max': 2006})
        self.assertTrue(response.context['filter_form'].errors)
        self.assertEqual(response.context['page_obj'].paginator.count, 0)
        car = Vehicle.objects.first()
        car.active = False
        car.save()
        response = self.client.get(reverse('vehicles:showcase'))
        self.assertEqual(response.context['catalogue_count'], Vehicle.objects.count() - 1)
        self.client.force_login(self.customer)
        self.assertEqual(self.client.post(reverse('vehicles:add_to_cart', args=[car.pk])).status_code, 404)

    def test_cart_is_authenticated_idempotent_and_does_not_book(self):
        car = Vehicle.objects.first()
        url = reverse('vehicles:add_to_cart', args=[car.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(SavedVehicle.objects.exists())
        self.client.force_login(self.customer)
        self.assertEqual(self.client.get(url).status_code, 405)
        secure_client = Client(enforce_csrf_checks=True)
        secure_client.force_login(self.customer)
        self.assertEqual(secure_client.post(url).status_code, 403)
        for _ in range(2):
            self.assertRedirects(self.client.post(url, {'customer': 9999}), reverse('dashboard:cart'))
        self.assertEqual(SavedVehicle.objects.count(), 1)
        self.assertEqual(SavedVehicle.objects.get().customer, self.customer)
        self.assertFalse(Booking.objects.exists())


class VehicleTests(TestCase):
    def test_vehicle_creation(self):
        category = VehicleCategory.objects.create(name='SUV', slug='suv')
        vehicle = Vehicle.objects.create(category=category, name='RAV4', brand='Toyota', model='RAV4', year=2024, registration_number='ABC-1', description='Test', price_per_day=50000, security_deposit=20000, transmission='AUTOMATIC', fuel_type='PETROL')
        self.assertEqual(str(vehicle), '2024 Toyota RAV4')

    def test_bad_filters_show_validation_errors(self):
        for field, value in [('category', 'bad'), ('seats', 'bad'), ('min_price', 'bad'), ('max_price', 'NaN'), ('max_price', 'Infinity'), ('max_price', '-1')]:
            with self.subTest(field=field, value=value):
                response = self.client.get(reverse('vehicles:list'), {field: value})
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['filter_form'].errors)

    def test_pagination_keeps_filters(self):
        category = VehicleCategory.objects.create(name='Sedan', slug='sedan')
        for index in range(10):
            Vehicle.objects.create(category=category, name='Corolla', brand='Toyota', model='Corolla', year=2024,
                                   registration_number=f'PAGE-{index}', description='Test', price_per_day=100,
                                   transmission='AUTOMATIC', fuel_type='PETROL')
        response = self.client.get(reverse('vehicles:list'), {'q': 'Toyota', 'max_price': '150'})
        self.assertContains(response, '?q=Toyota&amp;max_price=150&amp;page=2')

    def test_seed_can_run_again_on_another_day_without_duplicates(self):
        call_command('seed_data', stdout=StringIO())
        original_counts = (Vehicle.objects.count(), Booking.objects.count(), Payment.objects.count())
        tomorrow = timezone.localdate() + timedelta(days=1)
        with patch('vehicles.management.commands.seed_data.timezone.localdate', return_value=tomorrow):
            call_command('seed_data', stdout=StringIO())
        self.assertEqual((Vehicle.objects.count(), Booking.objects.count(), Payment.objects.count()), original_counts)
        self.assertEqual(original_counts, (15, 10, 4))


class SavedCarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user('renter')
        cls.other = User.objects.create_user('other-renter')
        category = VehicleCategory.objects.create(name='Sedan', slug='sedan')
        cls.vehicle = Vehicle.objects.create(category=category, name='Corolla', brand='Toyota', model='Corolla',
                                             year=2024, registration_number='SAVE-1', description='Test car',
                                             price_per_day=100, transmission='AUTOMATIC', fuel_type='PETROL')

    def test_visitors_can_browse_but_cannot_save_without_login(self):
        self.assertEqual(self.client.get(reverse('vehicles:list')).status_code, 200)
        self.assertEqual(self.client.get(self.vehicle.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.post(reverse('vehicles:save', args=[self.vehicle.pk])).status_code, 302)
        self.assertEqual(self.client.get(reverse('vehicles:saved')).status_code, 302)
        self.assertFalse(SavedVehicle.objects.exists())

    def test_save_is_private_idempotent_and_not_a_booking(self):
        self.client.force_login(self.customer)
        for _ in range(2):
            response = self.client.post(reverse('vehicles:save', args=[self.vehicle.pk]), {'customer': self.other.pk})
            self.assertRedirects(response, reverse('vehicles:saved'))
        self.assertEqual(SavedVehicle.objects.count(), 1)
        self.assertEqual(SavedVehicle.objects.get().customer, self.customer)
        self.assertFalse(Booking.objects.exists())
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.AVAILABLE)
        self.assertContains(self.client.get(reverse('vehicles:saved')), str(self.vehicle))
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse('vehicles:saved')), str(self.vehicle))

    def test_unsave_only_removes_current_customers_favourite(self):
        SavedVehicle.objects.create(customer=self.customer, vehicle=self.vehicle)
        SavedVehicle.objects.create(customer=self.other, vehicle=self.vehicle)
        self.client.force_login(self.customer)
        self.client.post(reverse('vehicles:unsave', args=[self.vehicle.pk]))
        self.assertFalse(self.customer.saved_vehicles.exists())
        self.assertTrue(self.other.saved_vehicles.exists())

    def test_save_and_unsave_require_post_and_csrf(self):
        self.client.force_login(self.customer)
        secure_client = Client(enforce_csrf_checks=True)
        secure_client.force_login(self.customer)
        for name in ['vehicles:save', 'vehicles:unsave']:
            url = reverse(name, args=[self.vehicle.pk])
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(secure_client.post(url).status_code, 403)
        self.assertFalse(SavedVehicle.objects.exists())

    def test_unlisted_saved_car_can_still_be_removed(self):
        SavedVehicle.objects.create(customer=self.customer, vehicle=self.vehicle)
        self.vehicle.active = False
        self.vehicle.save(update_fields=['active'])
        self.client.force_login(self.customer)
        response = self.client.get(reverse('vehicles:saved'))
        self.assertContains(response, 'This car is no longer listed')
        self.assertEqual(self.client.post(reverse('vehicles:save', args=[self.vehicle.pk])).status_code, 404)
        self.client.post(reverse('vehicles:unsave', args=[self.vehicle.pk]))
        self.assertFalse(self.customer.saved_vehicles.exists())

    def test_save_redirect_stays_on_site_and_preserves_filters(self):
        self.client.force_login(self.customer)
        url = reverse('vehicles:save', args=[self.vehicle.pk])
        response = self.client.post(url, {'next': 'https://example.com/elsewhere'})
        self.assertRedirects(response, reverse('vehicles:saved'))
        destination = reverse('vehicles:list') + '?q=Toyota'
        response = self.client.post(url, {'next': destination})
        self.assertRedirects(response, destination)
