from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from vehicles.models import Vehicle
from .forms import BookingForm, StatusForm, VehicleReturnForm
from .models import Booking
from .whatsapp import payment_chat_url


@login_required
def booking_create(request, vehicle_id):
    vehicle = get_object_or_404(Vehicle, pk=vehicle_id, active=True)
    form = BookingForm(request.POST or None, vehicle=vehicle, customer=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                form.instance.vehicle = Vehicle.objects.select_for_update().get(pk=vehicle.pk)
                booking = form.save()
        except ValidationError as exc:
            form.add_error(None, exc.messages)
        else:
            request.session[f'whatsapp_checkout_{booking.booking_reference}'] = True
            messages.success(request, 'Booking created successfully.')
            return redirect('bookings:success', reference=booking.booking_reference)
    return render(request, 'bookings/booking_form.html', {'form': form, 'vehicle': vehicle})


@login_required
def booking_list(request):
    bookings = request.user.bookings.select_related('vehicle')
    return render(request, 'bookings/booking_list.html', {'bookings': bookings})


@login_required
def booking_detail(request, reference):
    queryset = Booking.objects.select_related('vehicle', 'customer')
    if not request.user.is_staff:
        queryset = queryset.filter(customer=request.user)
    booking = get_object_or_404(queryset, booking_reference=reference)
    return render(request, 'bookings/booking_detail.html', {
        'booking': booking,
        'whatsapp_payment_url': payment_chat_url(booking) if booking.customer_id == request.user.pk else None,
    })


@login_required
@never_cache
def booking_success(request, reference):
    booking = get_object_or_404(Booking.objects.select_related('vehicle'), booking_reference=reference, customer=request.user)
    whatsapp_url = payment_chat_url(booking)
    new_checkout = request.session.pop(f'whatsapp_checkout_{reference}', False)
    return render(request, 'bookings/booking_success.html', {
        'booking': booking, 'whatsapp_payment_url': whatsapp_url,
        'auto_redirect': bool(new_checkout and whatsapp_url and booking.status == Booking.Status.PENDING),
    })


@login_required
def booking_cancel(request, reference):
    booking = get_object_or_404(Booking, booking_reference=reference, customer=request.user)
    if request.method == 'POST':
        try:
            booking.transition_to(Booking.Status.CANCELLED)
            messages.success(request, 'Booking cancelled successfully.')
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
    return redirect('bookings:detail', reference=reference)


@staff_member_required
def manage(request):
    bookings = Booking.objects.select_related('vehicle', 'customer')
    if request.GET.get('status'):
        bookings = bookings.filter(status=request.GET['status'])
    return render(request, 'bookings/manage.html', {'bookings': bookings, 'statuses': Booking.Status.choices})


@staff_member_required
def manage_detail(request, reference):
    booking = get_object_or_404(Booking.objects.select_related('vehicle', 'customer'), booking_reference=reference)
    form = StatusForm(request.POST or None, booking=booking)
    if request.method == 'POST' and form.is_valid():
        try:
            booking.transition_to(form.cleaned_data['status'])
            messages.success(request, 'Booking status updated successfully.')
            return redirect('bookings:manage_detail', reference=reference)
        except ValidationError as exc:
            form.add_error('status', exc)
    return render(request, 'bookings/manage_detail.html', {'booking': booking, 'form': form})


@staff_member_required
def process_return(request, reference):
    booking = get_object_or_404(Booking, booking_reference=reference, status__in=[Booking.Status.ACTIVE, Booking.Status.OVERDUE])
    form = VehicleReturnForm(request.POST or None, booking=booking)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                Vehicle.objects.select_for_update().get(pk=booking.vehicle_id)
                booking = Booking.objects.select_for_update().get(pk=booking.pk)
                if booking.status not in {Booking.Status.ACTIVE, Booking.Status.OVERDUE}:
                    raise ValidationError('This rental has already been returned or is no longer active.')
                vehicle_return = form.save(commit=False)
                vehicle_return.booking = booking
                vehicle_return.processed_by = request.user
                vehicle_return.full_clean()
                vehicle_return.save()
                booking.transition_to(Booking.Status.RETURNED)
        except ValidationError as exc:
            form.add_error(None, exc.messages)
        else:
            messages.success(request, 'Vehicle return processed successfully.')
            return redirect('bookings:manage_detail', reference=reference)
    return render(request, 'bookings/return_form.html', {'booking': booking, 'form': form})
