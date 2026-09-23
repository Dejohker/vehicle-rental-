from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking
from vehicles.models import Vehicle, VehicleCategory
from .models import Payment


class RentalPaymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.customer = User.objects.create_user('customer')
        cls.other = User.objects.create_user('other')
        cls.staff = User.objects.create_user('staff', is_staff=True)
        category = VehicleCategory.objects.create(name='Sedan', slug='sedan')
        cls.vehicle = Vehicle.objects.create(
            category=category, name='Corolla', brand='Toyota', model='Corolla', year=2024,
            registration_number='PAY-1', description='Test vehicle', price_per_day=Decimal('100'),
            security_deposit=Decimal('50'), transmission='AUTOMATIC', fuel_type='PETROL',
        )
        cls.today = timezone.localdate()
        cls.booking = Booking.objects.create(customer=cls.customer, vehicle=cls.vehicle,
                                             pickup_date=cls.today, return_date=cls.today + timedelta(days=2))

    def payment_data(self, **overrides):
        values = {'booking': self.booking.pk, 'amount': '100', 'payment_method': 'CASH',
                  'transaction_reference': 'TEST-PAYMENT', 'payment_status': 'PARTIAL',
                  'payment_date': timezone.localtime().strftime('%Y-%m-%dT%H:%M')}
        values.update(overrides)
        return values

    def test_partial_payment_reduces_balance_and_updates_dashboards(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('payments:create'), self.payment_data())
        payment = Payment.objects.get()
        self.assertRedirects(response, reverse('payments:detail', args=[payment.pk]))
        self.assertEqual(payment.customer, self.customer)
        self.assertEqual(self.booking.outstanding_balance, Decimal('150'))
        response = self.client.get(reverse('dashboard:staff'))
        self.assertEqual(response.context['total_revenue'], Decimal('100'))
        self.client.force_login(self.customer)
        response = self.client.get(reverse('dashboard:customer'))
        self.assertEqual(response.context['outstanding_payments'], Decimal('150'))

    def test_pending_failed_and_refunded_payments_do_not_reduce_balance(self):
        for status in [Payment.Status.PENDING, Payment.Status.FAILED, Payment.Status.REFUNDED]:
            Payment.objects.create(booking=self.booking, customer=self.customer, amount=100,
                                   payment_method='CASH', transaction_reference=status, payment_status=status)
        self.assertEqual(self.booking.amount_paid, 0)
        self.assertEqual(self.booking.outstanding_balance, Decimal('250'))

    def test_customer_cannot_record_payments_or_view_another_receipt(self):
        payment = Payment.objects.create(booking=self.booking, customer=self.customer, amount=100,
                                         payment_method='CASH', transaction_reference='PRIVATE', payment_status='PAID')
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('payments:detail', args=[payment.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('payments:create'), self.payment_data()).status_code, 302)
        self.assertEqual(Payment.objects.count(), 1)

    def test_invalid_amount_and_duplicate_reference_show_form_errors(self):
        self.client.force_login(self.staff)
        for amount in ['-1', '0']:
            response = self.client.post(reverse('payments:create'), self.payment_data(amount=amount))
            self.assertIn('amount', response.context['form'].errors)
        self.client.post(reverse('payments:create'), self.payment_data())
        response = self.client.post(reverse('payments:create'), self.payment_data())
        self.assertIn('transaction_reference', response.context['form'].errors)
        self.assertEqual(Payment.objects.count(), 1)

    def test_payment_cannot_be_assigned_to_wrong_customer(self):
        with self.assertRaises(ValidationError):
            Payment.objects.create(booking=self.booking, customer=self.other, amount=100,
                                   payment_method='CASH', transaction_reference='WRONG-CUSTOMER')

    def test_complete_rental_workflow_through_staff_pages(self):
        self.client.force_login(self.staff)
        manage_url = reverse('bookings:manage_detail', args=[self.booking.booking_reference])
        for status in ['CONFIRMED', 'READY_FOR_PICKUP', 'ACTIVE']:
            self.assertRedirects(self.client.post(manage_url, {'status': status}), manage_url)
        response = self.client.post(reverse('payments:create'), self.payment_data(amount='250', payment_status='PAID'))
        self.assertEqual(response.status_code, 302)
        response = self.client.post(reverse('bookings:return', args=[self.booking.booking_reference]), {
            'actual_return_date': self.today.isoformat(), 'condition_notes': 'Clean return',
            'late_fee': '0', 'damage_charge': '0', 'additional_charge': '20',
        })
        self.assertRedirects(response, manage_url)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.outstanding_balance, Decimal('20'))
        self.client.post(reverse('payments:create'), self.payment_data(amount='20', payment_status='PAID', transaction_reference='RETURN-FEE'))
        self.assertRedirects(self.client.post(manage_url, {'status': 'COMPLETED'}), manage_url)
        self.booking.refresh_from_db()
        self.vehicle.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.COMPLETED)
        self.assertEqual(self.booking.outstanding_balance, 0)
        self.assertEqual(self.vehicle.status, Vehicle.Status.AVAILABLE)
        self.client.force_login(self.customer)
        response = self.client.get(reverse('bookings:detail', args=[self.booking.booking_reference]))
        self.assertContains(response, 'RETURN-FEE')
        self.assertContains(response, 'Clean return')
