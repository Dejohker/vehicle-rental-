from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from vehicles.models import Vehicle, VehicleCategory
from .models import Booking, VehicleReturn
from payments.models import Payment


class BookingTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user('customer', password='pass12345')
        self.other = User.objects.create_user('other', password='pass12345')
        category = VehicleCategory.objects.create(name='Sedan', slug='sedan')
        self.vehicle = Vehicle.objects.create(category=category, name='Corolla', brand='Toyota', model='Corolla', year=2024, registration_number='LAG-001', description='Test', price_per_day=Decimal('45000'), security_deposit=Decimal('50000'), transmission='AUTOMATIC', fuel_type='PETROL')
        self.pickup = timezone.localdate() + timedelta(days=5)

    def make_booking(self, **kwargs):
        values = {'customer': self.customer, 'vehicle': self.vehicle, 'pickup_date': self.pickup, 'return_date': self.pickup + timedelta(days=5)}
        values.update(kwargs)
        return Booking.objects.create(**values)

    def test_price_is_calculated_on_backend(self):
        booking = self.make_booking()
        self.assertEqual(booking.number_of_days, 5)
        self.assertEqual(booking.rental_amount, Decimal('225000'))
        self.assertEqual(booking.total_amount, Decimal('275000'))

    def test_invalid_dates_rejected(self):
        with self.assertRaises(ValidationError):
            self.make_booking(return_date=self.pickup)

    def test_overlapping_booking_rejected(self):
        self.make_booking()
        with self.assertRaises(ValidationError):
            self.make_booking(customer=self.other, pickup_date=self.pickup + timedelta(days=2), return_date=self.pickup + timedelta(days=7))

    def test_non_overlapping_booking_allowed(self):
        self.make_booking()
        booking = self.make_booking(customer=self.other, pickup_date=self.pickup + timedelta(days=5), return_date=self.pickup + timedelta(days=7))
        self.assertIsNotNone(booking.pk)

    def test_customer_cannot_view_another_booking(self):
        booking = self.make_booking()
        self.client.force_login(self.other)
        response = self.client.get(reverse('bookings:detail', args=[booking.booking_reference]))
        self.assertEqual(response.status_code, 404)

    def test_staff_permission(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse('bookings:manage'))
        self.assertEqual(response.status_code, 302)

    def test_booking_creation_view(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('bookings:create', args=[self.vehicle.pk]), {
            'pickup_date': self.pickup.isoformat(),
            'return_date': (self.pickup + timedelta(days=3)).isoformat(),
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Booking.objects.count(), 1)


class WhatsAppCheckoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user('whatsapp-renter')
        cls.other = User.objects.create_user('other-renter')
        category = VehicleCategory.objects.create(name='Sedan', slug='sedan')
        cls.vehicle = Vehicle.objects.create(category=category, name='Corolla', brand='Toyota', model='Corolla',
                                             year=2024, registration_number='CHAT-1', description='Test car',
                                             price_per_day=Decimal('100'), security_deposit=Decimal('50'),
                                             transmission='AUTOMATIC', fuel_type='PETROL')

    def checkout(self):
        self.client.force_login(self.customer)
        today = timezone.localdate()
        response = self.client.post(reverse('bookings:create', args=[self.vehicle.pk]), {
            'pickup_date': today.isoformat(), 'return_date': (today + timedelta(days=2)).isoformat(),
        }, follow=True)
        return response, Booking.objects.get()

    def test_checkout_automatically_opens_correct_whatsapp_with_server_amount(self):
        response, booking = self.checkout()
        self.assertTrue(response.context['auto_redirect'])
        self.assertContains(response, 'js/whatsapp-checkout.js')
        self.assertNotContains(response, 'id="ride-preloader"')
        url = urlsplit(response.context['whatsapp_payment_url'])
        self.assertEqual(url.scheme, 'https')
        self.assertEqual(url.netloc, 'wa.me')
        self.assertEqual(url.path, '/2347081724880')
        message = parse_qs(url.query)['text'][0]
        for value in [booking.booking_reference, str(self.vehicle), booking.pickup_date.isoformat(), booking.return_date.isoformat(), 'NGN 250.00']:
            self.assertIn(value, message)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertFalse(Payment.objects.exists())

    def test_refresh_does_not_repeat_redirect_and_payment_link_remains(self):
        _, booking = self.checkout()
        response = self.client.get(reverse('bookings:success', args=[booking.booking_reference]))
        self.assertFalse(response.context['auto_redirect'])
        self.assertNotContains(response, 'js/whatsapp-checkout.js')
        self.assertContains(response, 'Pay via WhatsApp')
        self.assertIn('no-store', response['Cache-Control'])
        response = self.client.get(reverse('bookings:detail', args=[booking.booking_reference]))
        self.assertContains(response, 'Pay via WhatsApp')

    def test_other_customer_cannot_obtain_payment_details(self):
        _, booking = self.checkout()
        self.client.force_login(self.other)
        for route in ['bookings:success', 'bookings:detail']:
            self.assertEqual(self.client.get(reverse(route, args=[booking.booking_reference])).status_code, 404)

    def test_paid_and_cancelled_bookings_do_not_request_payment(self):
        _, booking = self.checkout()
        Payment.objects.create(booking=booking, customer=self.customer, amount=booking.total_amount,
                               payment_method='CASH', transaction_reference='CHAT-PAID', payment_status='PAID')
        response = self.client.get(reverse('bookings:success', args=[booking.booking_reference]))
        self.assertFalse(response.context['auto_redirect'])
        self.assertIsNone(response.context['whatsapp_payment_url'])
        booking.transition_to(Booking.Status.CANCELLED)
        self.assertNotContains(self.client.get(reverse('bookings:detail', args=[booking.booking_reference])), 'Pay via WhatsApp')

    def test_partial_payment_link_uses_remaining_balance(self):
        _, booking = self.checkout()
        Payment.objects.create(booking=booking, customer=self.customer, amount=Decimal('75'),
                               payment_method='CASH', transaction_reference='CHAT-PARTIAL', payment_status='PARTIAL')
        response = self.client.get(reverse('bookings:detail', args=[booking.booking_reference]))
        message = parse_qs(urlsplit(response.context['whatsapp_payment_url']).query)['text'][0]
        self.assertIn('Amount outstanding: NGN 175.00', message)

    def test_invalid_booking_does_not_launch_whatsapp(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('bookings:create', args=[self.vehicle.pk]), {
            'pickup_date': timezone.localdate().isoformat(), 'return_date': timezone.localdate().isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Booking.objects.exists())
        self.assertNotContains(response, 'js/whatsapp-checkout.js')


class BookingWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user('renter')
        cls.staff = User.objects.create_user('staff', is_staff=True)
        category = VehicleCategory.objects.create(name='Economy', slug='economy')
        cls.vehicle = Vehicle.objects.create(
            category=category, name='Demo car', brand='Toyota', model='Corolla',
            year=2024, registration_number='FLOW-1', description='Test vehicle',
            price_per_day=Decimal('100'), security_deposit=Decimal('50'),
            transmission='AUTOMATIC', fuel_type='PETROL',
        )
        cls.today = timezone.localdate()

    def make_booking(self, days_ahead=0):
        pickup = self.today + timedelta(days=days_ahead)
        return Booking.objects.create(
            customer=self.customer, vehicle=self.vehicle,
            pickup_date=pickup, return_date=pickup + timedelta(days=2),
        )

    def activate(self, booking):
        for status in [Booking.Status.CONFIRMED, Booking.Status.READY_FOR_PICKUP, Booking.Status.ACTIVE]:
            booking.transition_to(status)

    def return_data(self, **overrides):
        values = {
            'actual_return_date': self.today.isoformat(), 'condition_notes': 'Inspected',
            'late_fee': '0', 'damage_charge': '0', 'additional_charge': '0',
        }
        values.update(overrides)
        return values

    def test_old_booking_can_progress_without_repricing(self):
        booking = self.make_booking()
        Vehicle.objects.filter(pk=self.vehicle.pk).update(price_per_day=500, security_deposit=200)
        with patch('bookings.models.timezone.localdate', return_value=self.today + timedelta(days=3)):
            self.activate(booking)
        self.assertEqual(booking.total_amount, Decimal('250'))
        booking.refresh_from_db()
        self.assertEqual(booking.total_amount, Decimal('250'))
        self.assertEqual(booking.status, Booking.Status.ACTIVE)

    def test_cancelling_one_booking_preserves_other_rental_status(self):
        active = self.make_booking()
        future = self.make_booking(days_ahead=3)
        self.activate(active)
        future.transition_to(Booking.Status.CANCELLED)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.RENTED)
        self.assertEqual(future.outstanding_balance, 0)

    def test_return_preserves_another_confirmed_reservation(self):
        booking = self.make_booking()
        future = self.make_booking(days_ahead=3)
        self.activate(booking)
        future.transition_to(Booking.Status.CONFIRMED)
        self.client.force_login(self.staff)
        response = self.client.post(reverse('bookings:return', args=[booking.booking_reference]), self.return_data())
        self.assertEqual(response.status_code, 302)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.RESERVED)

    def test_two_bookings_cannot_be_physically_active_together(self):
        first = self.make_booking()
        second = self.make_booking(days_ahead=3)
        self.activate(first)
        second.transition_to(Booking.Status.CONFIRMED)
        second.transition_to(Booking.Status.READY_FOR_PICKUP)
        with self.assertRaisesMessage(ValidationError, 'still on another rental'):
            second.transition_to(Booking.Status.ACTIVE)

    def test_stale_instance_cannot_overwrite_cancelled_booking(self):
        booking = self.make_booking()
        stale = Booking.objects.get(pk=booking.pk)
        booking.transition_to(Booking.Status.CANCELLED)
        with self.assertRaises(ValidationError):
            stale.transition_to(Booking.Status.CONFIRMED)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)

    def test_return_requires_condition_record(self):
        booking = self.make_booking()
        self.activate(booking)
        with self.assertRaisesMessage(ValidationError, 'Process return'):
            booking.transition_to(Booking.Status.RETURNED)

    def test_return_charges_and_damage_reach_booking_and_fleet(self):
        booking = self.make_booking()
        self.activate(booking)
        self.client.force_login(self.staff)
        response = self.client.post(reverse('bookings:return', args=[booking.booking_reference]), self.return_data(
            damage_reported='on', damage_charge='25', additional_charge='10',
        ))
        self.assertRedirects(response, reverse('bookings:manage_detail', args=[booking.booking_reference]))
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.RETURNED)
        self.assertEqual(booking.outstanding_balance, Decimal('285'))
        booking.transition_to(Booking.Status.COMPLETED)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.DAMAGED)
        self.assertContains(self.client.get(reverse('bookings:detail', args=[booking.booking_reference])), 'Return summary')

    def test_invalid_return_dates_do_not_create_a_return(self):
        booking = self.make_booking()
        self.activate(booking)
        self.client.force_login(self.staff)
        for date in [self.today - timedelta(days=1), self.today + timedelta(days=1)]:
            with self.subTest(date=date):
                response = self.client.post(reverse('bookings:return', args=[booking.booking_reference]), self.return_data(actual_return_date=date.isoformat()))
                self.assertEqual(response.status_code, 200)
                self.assertIn('actual_return_date', response.context['form'].errors)
        self.assertFalse(VehicleReturn.objects.exists())
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.ACTIVE)

    def test_return_failure_rolls_back_condition_record(self):
        booking = self.make_booking()
        self.activate(booking)
        self.client.force_login(self.staff)
        with patch.object(Booking, 'transition_to', side_effect=ValidationError('Transition failed')):
            response = self.client.post(reverse('bookings:return', args=[booking.booking_reference]), self.return_data())
        self.assertContains(response, 'Transition failed')
        self.assertFalse(VehicleReturn.objects.exists())
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.ACTIVE)

    def test_unavailable_vehicle_shows_form_error(self):
        self.vehicle.status = Vehicle.Status.MAINTENANCE
        self.vehicle.save()
        self.client.force_login(self.customer)
        response = self.client.post(reverse('bookings:create', args=[self.vehicle.pk]), {
            'pickup_date': self.today.isoformat(),
            'return_date': (self.today + timedelta(days=1)).isoformat(),
        })
        self.assertContains(response, 'This vehicle is not available for booking.')
        self.assertFalse(Booking.objects.exists())

    def test_cancel_still_works_when_vehicle_is_under_maintenance(self):
        booking = self.make_booking()
        Vehicle.objects.filter(pk=self.vehicle.pk).update(status=Vehicle.Status.MAINTENANCE)
        booking.transition_to(Booking.Status.CANCELLED)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.status, Vehicle.Status.MAINTENANCE)

    def test_schedule_and_status_cannot_bypass_workflow(self):
        booking = self.make_booking()
        booking.pickup_date += timedelta(days=1)
        with self.assertRaises(ValidationError):
            booking.save()
        booking.refresh_from_db()
        booking.status = Booking.Status.COMPLETED
        with self.assertRaises(ValidationError):
            booking.save()

    def test_customer_cannot_process_return_or_cancel_another_booking(self):
        booking = self.make_booking()
        self.activate(booking)
        other = User.objects.create_user('another-renter')
        self.client.force_login(other)
        self.assertEqual(self.client.post(reverse('bookings:return', args=[booking.booking_reference]), self.return_data()).status_code, 302)
        self.assertEqual(self.client.post(reverse('bookings:cancel', args=[booking.booking_reference])).status_code, 404)
        self.assertFalse(VehicleReturn.objects.exists())
