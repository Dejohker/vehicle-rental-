from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import Resolver404, resolve, reverse

from .forms import CustomerAuthenticationForm, ProfileForm, RegistrationForm, UserForm
from .models import CustomerProfile


@login_required
def license_image(request, filename):
    profiles = CustomerProfile.objects.all()
    if not request.user.is_staff:
        profiles = profiles.filter(user=request.user)
    profile_obj = get_object_or_404(profiles, driver_license_image=f'licenses/{filename}')
    try:
        document = profile_obj.driver_license_image.open('rb')
    except FileNotFoundError:
        raise Http404('License document not found.')
    response = FileResponse(document, as_attachment=True)
    response['Cache-Control'] = 'private, no-store'
    return response


class CustomerLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomerAuthenticationForm
    redirect_authenticated_user = True


def rental_signup_intent(destination):
    """Only carry a local car/booking selection into a new customer's dashboard."""
    if not destination.startswith('/') or destination.startswith('//'):
        return None
    try:
        match = resolve(destination.split('?', 1)[0])
    except Resolver404:
        return None
    if match.view_name == 'bookings:create':
        return {'vehicle_id': match.kwargs['vehicle_id'], 'action': 'book'}
    if match.view_name == 'vehicles:detail':
        return {'vehicle_id': match.kwargs['pk'], 'action': 'view'}
    return None


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    destination = request.POST.get('next', '') if request.method == 'POST' else request.GET.get('next', '')
    intent = rental_signup_intent(destination)
    next_url = ''
    if intent:
        next_url = reverse('bookings:create' if intent['action'] == 'book' else 'vehicles:detail', args=[intent['vehicle_id']])
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        if intent:
            request.session['signup_rental_intent'] = intent
        messages.success(request, f'Welcome to RideFlow, {user.first_name or user.username}! Your account is ready.')
        return redirect('dashboard:customer')
    return render(request, 'accounts/register.html', {'form': form, 'next': next_url})


@login_required
def profile(request):
    profile_obj, _ = CustomerProfile.objects.get_or_create(user=request.user)
    return render(request, 'accounts/profile.html', {'profile': profile_obj})


@login_required
def edit_profile(request):
    profile_obj, _ = CustomerProfile.objects.get_or_create(user=request.user)
    user_form = UserForm(request.POST or None, instance=request.user)
    profile_form = ProfileForm(request.POST or None, request.FILES or None, instance=profile_obj)
    if request.method == 'POST' and user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')
    return render(request, 'accounts/edit_profile.html', {'user_form': user_form, 'profile_form': profile_form})
