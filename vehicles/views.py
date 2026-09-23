from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import VehicleFilterForm, VehicleForm
from .models import SavedVehicle, Vehicle
from .utils import saved_vehicle_ids


def saved_return_url(request):
    destination = request.POST.get('next', '')
    if destination and url_has_allowed_host_and_scheme(destination, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return destination
    return reverse('vehicles:saved')


@login_required
def saved_vehicles(request):
    saved = request.user.saved_vehicles.select_related('vehicle__category')
    page = Paginator(saved, 9).get_page(request.GET.get('page'))
    return render(request, 'vehicles/saved.html', {'page_obj': page, 'saved_vehicle_ids': saved_vehicle_ids(request.user)})


@login_required
@require_POST
def save_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, active=True)
    _, created = SavedVehicle.objects.get_or_create(customer=request.user, vehicle=vehicle)
    if created:
        messages.success(request, f'{vehicle} added to your saved cars.')
    return redirect(saved_return_url(request))


@login_required
@require_POST
def add_to_cart(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk, active=True)
    _, created = SavedVehicle.objects.get_or_create(customer=request.user, vehicle=vehicle)
    messages.success(request, f'{vehicle} added to your cart. Choose dates when you are ready to book.' if created else 'This car is already in your cart.')
    return redirect('dashboard:cart')


@login_required
@require_POST
def unsave_vehicle(request, pk):
    removed, _ = request.user.saved_vehicles.filter(vehicle_id=pk).delete()
    if removed:
        messages.success(request, 'Car removed from your saved cars.')
    return redirect(saved_return_url(request))


def catalogue_context(request, per_page=9):
    vehicles = Vehicle.objects.filter(active=True).select_related('category')
    form = VehicleFilterForm(request.GET)
    valid = form.is_valid()
    data = form.cleaned_data
    q = data.get('q')
    if q:
        vehicles = vehicles.filter(Q(name__icontains=q) | Q(brand__icontains=q) | Q(model__icontains=q))
    filters = {'category': 'category', 'brand': 'brand', 'year__gte': 'year_min', 'year__lte': 'year_max', 'transmission': 'transmission', 'fuel_type': 'fuel_type', 'number_of_seats__gte': 'seats', 'price_per_day__gte': 'min_price', 'price_per_day__lte': 'max_price'}
    for lookup, parameter in filters.items():
        if data.get(parameter) not in (None, ''):
            vehicles = vehicles.filter(**{lookup: data[parameter]})
    if data.get('availability'):
        vehicles = vehicles.filter(status=Vehicle.Status.AVAILABLE)
    if not valid:
        vehicles = vehicles.none()
    ordering = {'price_low': ('price_per_day', 'pk'), 'price_high': ('-price_per_day', 'pk'), 'newest': ('-year', 'pk'), 'oldest': ('year', 'pk')}
    vehicles = vehicles.order_by(*ordering.get(data.get('sort'), ('-featured', 'brand', 'model', '-year', 'pk')))
    page = Paginator(vehicles, per_page).get_page(request.GET.get('page'))
    return {'page_obj': page, 'filter_form': form, 'saved_vehicle_ids': saved_vehicle_ids(request.user)}


def vehicle_list(request):
    return render(request, 'vehicles/vehicle_list.html', catalogue_context(request))


def showcase(request):
    context = catalogue_context(request, per_page=12)
    context['brand_choices'] = Vehicle.objects.filter(active=True).order_by('brand').values('brand').annotate(total=Count('pk'))
    context['catalogue_count'] = Vehicle.objects.filter(active=True).count()
    return render(request, 'vehicles/showcase.html', context)


def vehicle_detail(request, pk):
    return render(request, 'vehicles/vehicle_detail.html', {
        'vehicle': get_object_or_404(Vehicle.objects.select_related('category'), pk=pk, active=True),
        'saved_vehicle_ids': saved_vehicle_ids(request.user),
    })


@staff_member_required
def manage(request):
    return render(request, 'vehicles/manage.html', {'vehicles': Vehicle.objects.select_related('category')})


@staff_member_required
def vehicle_edit(request, pk=None):
    vehicle = get_object_or_404(Vehicle, pk=pk) if pk else None
    form = VehicleForm(request.POST or None, request.FILES or None, instance=vehicle)
    if request.method == 'POST' and form.is_valid():
        saved = form.save()
        messages.success(request, f'Vehicle {"updated" if vehicle else "added"} successfully.')
        return redirect(saved.get_absolute_url() if saved.active else 'vehicles:manage')
    return render(request, 'vehicles/vehicle_form.html', {'form': form, 'vehicle': vehicle})


@staff_member_required
def vehicle_deactivate(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == 'POST':
        vehicle.active = False
        vehicle.save(update_fields=['active'])
        messages.success(request, 'Vehicle deactivated successfully.')
    return redirect('vehicles:manage')
