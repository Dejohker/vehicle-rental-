from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from bookings.models import Booking
from payments.models import Payment
from vehicles.models import SavedVehicle, Vehicle, VehicleCategory


class CustomerDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user('renter')
        cls.other = User.objects.create_user('other-renter')
        cls.staff = User.objects.create_user('staff', is_staff=True)
        category = VehicleCategory.objects.create(name='Sedan', slug='sedan')
        cls.vehicle = Vehicle.objects.create(category=category, name='Corolla', brand='Toyota', model='Corolla',
                                             year=2024, registration_number='DASH-1', description='Test car',
                                             price_per_day=100, transmission='AUTOMATIC', fuel_type='PETROL')
        today = timezone.localdate()
        cls.booking = Booking.objects.create(customer=cls.customer, vehicle=cls.vehicle,
                                             pickup_date=today, return_date=today + timedelta(days=2))
        SavedVehicle.objects.create(customer=cls.customer, vehicle=cls.vehicle)

    def test_dashboard_contains_only_current_customers_data(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse('dashboard:customer'))
        self.assertEqual(response.context['total_bookings'], 0)
        self.assertEqual(response.context['saved_count'], 0)
        self.assertIsNone(response.context['featured_booking'])
        self.assertNotContains(response, self.booking.booking_reference)
        self.assertContains(response, 'Your first journey starts here.')
        self.assertContains(response, 'Found a car you like?')
        self.client.force_login(self.customer)
        response = self.client.get(reverse('dashboard:customer'))
        self.assertEqual(response.context['total_bookings'], 1)
        self.assertEqual(response.context['saved_count'], 1)
        self.assertEqual(response.context['featured_booking'], self.booking)
        self.assertContains(response, 'Cars you like')

    def test_customer_navigation_and_permissions_exclude_staff_management(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse('dashboard:customer'))
        for name in ['vehicles:manage', 'bookings:manage', 'payments:list', 'dashboard:customers', 'dashboard:staff']:
            url = reverse(name)
            self.assertNotContains(response, f'href="{url}"')
            self.assertEqual(self.client.get(url).status_code, 302)
        for name in ['vehicles:list', 'vehicles:saved', 'bookings:list', 'accounts:profile']:
            self.assertContains(response, f'href="{reverse(name)}"')

    def test_staff_redirected_to_separate_dashboard(self):
        self.client.force_login(self.staff)
        self.assertRedirects(self.client.get(reverse('dashboard:customer')), reverse('dashboard:staff'))

    def test_anonymous_user_cannot_view_dashboard(self):
        self.assertEqual(self.client.get(reverse('dashboard:customer')).status_code, 302)

    def test_cart_shows_saved_cars_pending_bookings_and_badge(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse('dashboard:cart'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['cart_item_count'], 2)
        self.assertEqual(len(response.context['saved_cars']), 1)
        self.assertEqual(len(response.context['pending_orders']), 1)
        self.assertContains(response, self.booking.booking_reference)
        self.assertContains(response, 'Continue payment on WhatsApp')
        self.assertContains(response, 'https://wa.me/2347081724880')
        self.assertContains(response, 'aria-label="Cart, 2 items"')
        catalogue = self.client.get(reverse('vehicles:list'))
        self.assertEqual(catalogue.context['cart_item_count'], 2)
        self.assertContains(catalogue, f'href="{reverse("dashboard:cart")}"')

    def test_cart_does_not_show_another_customers_items(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse('dashboard:cart'))
        self.assertEqual(response.context['cart_item_count'], 0)
        self.assertContains(response, 'Your cart is empty')
        self.assertNotContains(response, self.booking.booking_reference)
        self.assertEqual(response.context['saved_cars'], [])
        self.assertEqual(response.context['pending_orders'], [])

    def test_cart_has_dates_and_checkout_without_self_link_button(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse('dashboard:cart'))
        self.assertContains(response, 'name="pickup_date"')
        self.assertContains(response, 'name="return_date"')
        self.assertContains(response, 'Continue to payment')
        self.assertContains(response, f'action="{reverse("bookings:create", args=[self.vehicle.pk])}"')
        self.assertContains(response, 'Estimated total:')
        self.assertNotContains(response, 'View in cart →')

    def test_cart_checkout_calculates_days_and_opens_payment_flow(self):
        self.client.force_login(self.customer)
        start = timezone.localdate() + timedelta(days=10)
        response = self.client.post(reverse('bookings:create', args=[self.vehicle.pk]), {
            'pickup_date': start.isoformat(), 'return_date': (start + timedelta(days=3)).isoformat(),
            'total_amount': '1', 'customer': self.other.pk,
        })
        booking = Booking.objects.exclude(pk=self.booking.pk).get()
        self.assertEqual(booking.customer, self.customer)
        self.assertEqual(booking.number_of_days, 3)
        self.assertEqual(booking.total_amount, 300)
        self.assertRedirects(response, reverse('bookings:success', args=[booking.booking_reference]), fetch_redirect_response=False)
        success = self.client.get(response.url)
        self.assertTrue(success.context['auto_redirect'])
        self.assertContains(success, 'https://wa.me/2347081724880')

    def test_invalid_cart_dates_do_not_create_booking(self):
        self.client.force_login(self.customer)
        start = timezone.localdate() + timedelta(days=10)
        response = self.client.post(reverse('bookings:create', args=[self.vehicle.pk]), {
            'pickup_date': start.isoformat(), 'return_date': start.isoformat(),
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(Booking.objects.count(), 1)

    def test_unsave_from_cart_returns_to_cart_and_updates_count(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('vehicles:unsave', args=[self.vehicle.pk]), {'next': reverse('dashboard:cart')}, follow=True)
        self.assertTemplateUsed(response, 'dashboard/cart.html')
        self.assertEqual(response.context['cart_item_count'], 1)
        self.assertEqual(response.context['saved_cars'], [])
        self.assertEqual(len(response.context['pending_orders']), 1)

    def test_confirmed_and_cancelled_bookings_leave_pending_cart(self):
        self.client.force_login(self.customer)
        for status in [Booking.Status.CONFIRMED, Booking.Status.CANCELLED]:
            self.booking.transition_to(status)
            response = self.client.get(reverse('dashboard:cart'))
            self.assertEqual(response.context['cart_item_count'], 1)
            self.assertEqual(response.context['pending_orders'], [])
            self.assertNotContains(response, self.booking.booking_reference)

    def test_paid_pending_booking_does_not_request_another_payment(self):
        Payment.objects.create(booking=self.booking, customer=self.customer, amount=self.booking.total_amount,
                               payment_method='CASH', transaction_reference='CART-PAID', payment_status='PAID')
        self.client.force_login(self.customer)
        response = self.client.get(reverse('dashboard:cart'))
        self.assertEqual(response.context['cart_item_count'], 2)
        self.assertContains(response, 'No payment outstanding')
        self.assertNotContains(response, 'https://wa.me/')
        self.assertNotContains(response, 'js/whatsapp-checkout.js')

    def test_cart_requires_customer_session(self):
        self.assertEqual(self.client.get(reverse('dashboard:cart')).status_code, 302)
        self.client.force_login(self.staff)
        self.assertRedirects(self.client.get(reverse('dashboard:cart')), reverse('dashboard:staff'))
