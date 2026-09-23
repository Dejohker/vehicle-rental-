from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from tempfile import TemporaryDirectory

from .forms import UserForm
from vehicles.models import Vehicle, VehicleCategory


class RegistrationTests(TestCase):
    def test_registration_creates_customer_profile(self):
        response = self.client.post(reverse('accounts:register'), {'first_name': 'Ada', 'last_name': 'Okafor', 'username': 'ada', 'email': 'ada@example.com', 'phone_number': '08012345678', 'password1': 'SafePass123!', 'password2': 'SafePass123!'})
        self.assertRedirects(response, reverse('dashboard:customer'))
        self.assertTrue(User.objects.get(username='ada').profile)
        self.assertEqual(int(self.client.session['_auth_user_id']), User.objects.get(username='ada').pk)

    def test_login(self):
        User.objects.create_user('ada', password='SafePass123!')
        response = self.client.post(reverse('accounts:login'), {'username': 'ada', 'password': 'SafePass123!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:index'))

    def test_profile_cannot_take_another_users_email(self):
        user = User.objects.create_user('first', email='first@example.com')
        User.objects.create_user('second', email='second@example.com')
        form = UserForm({'email': 'SECOND@example.com'}, instance=user)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_license_download_requires_owner_or_staff(self):
        owner = User.objects.create_user('owner')
        other = User.objects.create_user('other')
        staff = User.objects.create_user('staff', is_staff=True)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            owner.profile.driver_license_image.save('license.png', ContentFile(b'private document'))
            url = owner.profile.driver_license_image.url
            self.assertEqual(self.client.get(url).status_code, 302)
            self.client.force_login(other)
            self.assertEqual(self.client.get(url).status_code, 404)
            for alternate in [url.replace('/media/', '/media//'), url.replace('/media/', '/media/profiles/../')]:
                self.assertEqual(self.client.get(alternate).status_code, 404)
            for user in [owner, staff]:
                self.client.force_login(user)
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(b''.join(response.streaming_content), b'private document')
                self.assertEqual(response['Cache-Control'], 'private, no-store')
                response.close()


class SignupLoginFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.existing = User.objects.create_user('ExistingRenter', email='existing@example.com', password='RiverRoad!8274')
        category = VehicleCategory.objects.create(name='Sedan', slug='sedan')
        cls.vehicle = Vehicle.objects.create(category=category, name='Corolla', brand='Toyota', model='Corolla',
                                             year=2024, registration_number='SIGNUP-1', description='Test car',
                                             price_per_day=100, transmission='AUTOMATIC', fuel_type='PETROL')

    def signup_data(self, **overrides):
        values = {
            'first_name': 'Ada', 'last_name': 'Okafor', 'username': 'NewRenter',
            'email': 'ada@example.com', 'phone_number': '08012345678',
            'password1': 'TravelRoad!8274', 'password2': 'TravelRoad!8274',
        }
        values.update(overrides)
        return values

    def test_signup_credentials_work_on_login(self):
        response = self.client.post(reverse('accounts:register'), self.signup_data())
        self.assertRedirects(response, reverse('dashboard:customer'))
        user = User.objects.get(username='NewRenter')
        self.assertNotEqual(user.password, 'TravelRoad!8274')
        self.assertTrue(user.check_password('TravelRoad!8274'))
        self.assertEqual(user.profile.phone_number, '08012345678')
        self.client.post(reverse('accounts:logout'))
        response = self.client.post(reverse('accounts:login'), {'username': 'NewRenter', 'password': 'TravelRoad!8274'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/customer_dashboard.html')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_login_accepts_username_capitalization_and_outer_spaces(self):
        response = self.client.post(reverse('accounts:login'), {'username': '  EXISTINGRENTER  ', 'password': 'RiverRoad!8274'})
        self.assertRedirects(response, reverse('dashboard:index'), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.existing.pk)

    def test_wrong_password_and_unknown_username_are_rejected(self):
        for username, password in [('ExistingRenter', 'wrong'), ('missing', 'RiverRoad!8274'), ('ExistingRenter', 'riverroad!8274')]:
            with self.subTest(username=username, password_case=password == 'riverroad!8274'):
                response = self.client.post(reverse('accounts:login'), {'username': username, 'password': password})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].non_field_errors())
                self.assertNotIn('_auth_user_id', self.client.session)
                self.assertNotContains(response, f'value="{password}"')

    def test_signup_rejects_duplicate_username_and_email(self):
        for values, field in [({'username': 'existingrenter'}, 'username'), ({'email': 'EXISTING@example.com'}, 'email')]:
            with self.subTest(field=field):
                response = self.client.post(reverse('accounts:register'), self.signup_data(**values))
                self.assertEqual(response.status_code, 200)
                self.assertIn(field, response.context['form'].errors)
                self.assertEqual(User.objects.count(), 1)

    def test_signup_rejects_mismatched_and_weak_passwords(self):
        for values in [{'password2': 'DifferentRoad!8274'}, {'password1': '123', 'password2': '123'}]:
            with self.subTest(mismatch=values.get('password1') != '123'):
                response = self.client.post(reverse('accounts:register'), self.signup_data(**values))
                self.assertEqual(response.status_code, 200)
                self.assertIn('password2', response.context['form'].errors)
                self.assertEqual(User.objects.count(), 1)

    def test_empty_signup_shows_required_errors(self):
        response = self.client.post(reverse('accounts:register'), {})
        self.assertEqual(response.status_code, 200)
        self.assertIn('username', response.context['form'].errors)
        self.assertIn('password1', response.context['form'].errors)

    def test_signup_requires_first_and_last_names(self):
        for field in ['first_name', 'last_name']:
            for value in ['', '   ']:
                with self.subTest(field=field, value=value):
                    response = self.client.post(reverse('accounts:register'), self.signup_data(**{field: value}))
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(field, response.context['form'].errors)
                    self.assertFalse(User.objects.filter(username='NewRenter').exists())
        response = self.client.get(reverse('accounts:register'))
        self.assertContains(response, 'First name <span class="auth-optional">(required)</span>', html=True)
        self.assertContains(response, 'Last name <span class="auth-optional">(required)</span>', html=True)

    def test_signup_signs_in_customer_and_opens_dashboard(self):
        response = self.client.post(reverse('accounts:register'), self.signup_data(), follow=True)
        self.assertTemplateUsed(response, 'dashboard/customer_dashboard.html')
        self.assertEqual(response.context['user'].username, 'NewRenter')
        self.assertFalse(response.context['user'].is_staff)
        self.assertContains(response, 'Your first journey starts here.')
        self.assertNotContains(response, 'value="TravelRoad!8274"')

    def test_signup_preserves_selected_car_on_dashboard(self):
        next_url = reverse('bookings:create', args=[self.vehicle.pk])
        response = self.client.post(reverse('accounts:register'), self.signup_data(next=next_url), follow=True)
        self.assertTemplateUsed(response, 'dashboard/customer_dashboard.html')
        self.assertContains(response, 'Continue booking')
        self.assertEqual(response.context['selected_vehicle'], self.vehicle)
        self.assertEqual(response.context['selected_action'], 'book')

    def test_signup_cannot_grant_staff_access_or_redirect_externally(self):
        response = self.client.post(reverse('accounts:register'), self.signup_data(
            is_staff='true', is_superuser='true', next='https://example.com/untrusted',
        ), follow=True)
        self.assertTemplateUsed(response, 'dashboard/customer_dashboard.html')
        user = User.objects.get(username='NewRenter')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertNotContains(response, 'https://example.com/untrusted')

    def test_inactive_account_cannot_login(self):
        self.existing.is_active = False
        self.existing.save(update_fields=['is_active'])
        response = self.client.post(reverse('accounts:login'), {'username': 'existingrenter', 'password': 'RiverRoad!8274'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_rejects_external_redirect(self):
        response = self.client.post(reverse('accounts:login'), {'username': 'ExistingRenter', 'password': 'RiverRoad!8274', 'next': 'https://example.com/untrusted'})
        self.assertRedirects(response, reverse('dashboard:index'), fetch_redirect_response=False)

    def test_login_preserves_local_destination(self):
        response = self.client.post(reverse('accounts:login'), {'username': 'ExistingRenter', 'password': 'RiverRoad!8274', 'next': reverse('accounts:profile')})
        self.assertRedirects(response, reverse('accounts:profile'))


class SeparateLoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = User.objects.create_user('TeamMember', password='StaffRoad!8274', is_staff=True)
        cls.customer = User.objects.create_user('Customer', password='CustomerRoad!8274')

    def test_admin_login_has_distinct_page_without_signup_form(self):
        response = self.client.get(reverse('admin:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/admin_login.html')
        self.assertContains(response, 'RIDEFLOW OPERATIONS')
        self.assertContains(response, 'Customer sign-in')
        self.assertNotContains(response, 'name="password2"')
        self.assertNotContains(response, f'href="{reverse("accounts:register")}"')
        response = self.client.get(reverse('accounts:login'))
        self.assertTemplateUsed(response, 'accounts/login.html')
        self.assertContains(response, 'Staff / admin sign-in')

    def test_staff_login_accepts_valid_staff_credentials_and_destination(self):
        response = self.client.post(reverse('admin:login'), {
            'username': 'teammember', 'password': 'StaffRoad!8274', 'next': reverse('dashboard:staff'),
        })
        self.assertRedirects(response, reverse('dashboard:staff'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.staff.pk)

    def test_customer_cannot_sign_in_through_admin_page(self):
        response = self.client.post(reverse('admin:login'), {'username': 'Customer', 'password': 'CustomerRoad!8274'})
        self.assertContains(response, 'This sign-in is for staff and administrators.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_staff_is_directed_away_from_customer_login(self):
        response = self.client.post(reverse('accounts:login'), {'username': 'TeamMember', 'password': 'StaffRoad!8274'})
        self.assertContains(response, 'Please use the staff / admin sign-in page')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_invalid_and_inactive_staff_credentials_are_rejected(self):
        response = self.client.post(reverse('admin:login'), {'username': 'TeamMember', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.staff.is_active = False
        self.staff.save(update_fields=['is_active'])
        response = self.client.post(reverse('admin:login'), {'username': 'TeamMember', 'password': 'StaffRoad!8274'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_staff_login_rejects_external_destination(self):
        response = self.client.post(reverse('admin:login'), {
            'username': 'TeamMember', 'password': 'StaffRoad!8274', 'next': 'https://example.com/untrusted',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('dashboard:index'))

    def test_protected_staff_page_uses_admin_login(self):
        response = self.client.get(reverse('vehicles:manage'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('admin:login') + '?next='))
