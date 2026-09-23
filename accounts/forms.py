from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import CustomerProfile


class BootstrapMixin:
    def apply_bootstrap(self):
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')


class RentalAuthenticationForm(BootstrapMixin, AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'The username and password do not match. Use your username (not your email) and check your password.',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
        self.fields['username'].widget.attrs.update({
            'autocomplete': 'username', 'autocapitalize': 'none', 'spellcheck': 'false',
            'placeholder': 'Enter your username',
        })
        self.fields['username'].help_text = 'Use the username you chose when you registered.'
        self.fields['password'].widget.attrs['placeholder'] = 'Enter your password'

    def clean_username(self):
        username = self.cleaned_data['username']
        matches = list(User.objects.filter(username__iexact=username).values_list('username', flat=True)[:2])
        # Match signup's case-insensitive uniqueness rule. Older ambiguous accounts
        # still need their exact username, so we never choose an arbitrary user.
        return matches[0] if len(matches) == 1 else username


class CustomerAuthenticationForm(RentalAuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_staff:
            raise forms.ValidationError('Please use the staff / admin sign-in page for this account.', code='staff_account')


class StaffAuthenticationForm(RentalAuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = 'Enter the username for your staff or administrator account.'

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not user.is_staff:
            raise forms.ValidationError('This sign-in is for staff and administrators. Use customer sign-in to manage your rentals.', code='customer_account')


class RegistrationForm(BootstrapMixin, UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=30)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'phone_number', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
        attributes = {
            'first_name': {'autocomplete': 'given-name', 'placeholder': 'First name'},
            'last_name': {'autocomplete': 'family-name', 'placeholder': 'Last name'},
            'username': {'autocomplete': 'username', 'autocapitalize': 'none', 'spellcheck': 'false', 'placeholder': 'Choose a username'},
            'email': {'autocomplete': 'email', 'placeholder': 'you@example.com'},
            'phone_number': {'autocomplete': 'tel', 'inputmode': 'tel', 'placeholder': 'e.g. 08012345678'},
            'password1': {'autocomplete': 'new-password', 'placeholder': 'Create a password'},
            'password2': {'autocomplete': 'new-password', 'placeholder': 'Re-enter your password'},
        }
        for name, attrs in attributes.items():
            self.fields[name].widget.attrs.update(attrs)
        self.fields['email'].label = 'Email address'
        self.fields['password2'].label = 'Confirm password'
        self.fields['username'].help_text = 'Use letters, numbers or @/./+/-/_. You will sign in with this username.'
        self.fields['password2'].help_text = 'Enter the same password again. Passwords are case-sensitive.'

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
            CustomerProfile.objects.update_or_create(user=user, defaults={'phone_number': self.cleaned_data['phone_number']})
        return user


class UserForm(BootstrapMixin, forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class ProfileForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = CustomerProfile
        exclude = ('user', 'created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap()
