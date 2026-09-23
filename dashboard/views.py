from decimal import Decimal

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import redirect, render
from django.utils import timezone

from bookings.models import Booking
from bookings.whatsapp import payment_chat_url
from payments.models import Payment
from vehicles.models import Vehicle
from vehicles.utils import saved_vehicle_ids


@login_required
def index(request):
    return redirect('dashboard:staff' if request.user.is_staff else 'dashboard:customer')


@login_required
def customer(request):
    if request.user.is_staff:
        return redirect('dashboard:staff')
    bookings = request.user.bookings.select_related('vehicle', 'vehicle_return')
    upcoming_statuses = [Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.READY_FOR_PICKUP]
    current_rental = bookings.filter(status__in=[Booking.Status.ACTIVE, Booking.Status.OVERDUE]).order_by('return_date').first()
    upcoming = bookings.filter(status__in=upcoming_statuses, pickup_date__gte=timezone.localdate())
    next_booking = upcoming.order_by('pickup_date').first()
    saved = request.user.saved_vehicles.select_related('vehicle__category')
    intent = request.session.pop('signup_rental_intent', None)
    selected_vehicle = Vehicle.objects.filter(pk=intent['vehicle_id'], active=True).first() if intent else None
    context = {
        'total_bookings': bookings.count(),
        'active_rentals': bookings.filter(status__in=[Booking.Status.ACTIVE, Booking.Status.OVERDUE]).count(),
        'upcoming_bookings': upcoming.count(),
        'completed_rentals': bookings.filter(status=Booking.Status.COMPLETED).count(),
        'outstanding_payments': sum((booking.outstanding_balance for booking in bookings), Decimal('0')),
        'recent_bookings': bookings[:6],
        'featured_booking': current_rental or next_booking,
        'current_rental': current_rental,
        'saved_count': saved.count(),
        'saved_cars': saved[:3],
        'saved_vehicle_ids': saved_vehicle_ids(request.user),
        'selected_vehicle': selected_vehicle,
        'selected_action': intent['action'] if intent else None,
    }
    return render(request, 'dashboard/customer_dashboard.html', context)


@staff_member_required
def staff(request):
    context = {
        'total_vehicles': Vehicle.objects.count(), 'available_vehicles': Vehicle.objects.filter(status=Vehicle.Status.AVAILABLE, active=True).count(),
        'rented_vehicles': Vehicle.objects.filter(status=Vehicle.Status.RENTED).count(), 'reserved_vehicles': Vehicle.objects.filter(status=Vehicle.Status.RESERVED).count(),
        'maintenance_vehicles': Vehicle.objects.filter(status=Vehicle.Status.MAINTENANCE).count(), 'total_customers': User.objects.filter(is_staff=False).count(),
        'pending_bookings': Booking.objects.filter(status=Booking.Status.PENDING).count(), 'active_rentals': Booking.objects.filter(status__in=[Booking.Status.ACTIVE, Booking.Status.OVERDUE]).count(),
        'completed_rentals': Booking.objects.filter(status=Booking.Status.COMPLETED).count(),
        'total_revenue': Payment.objects.filter(payment_status__in=[Payment.Status.PAID, Payment.Status.PARTIAL]).aggregate(total=Sum('amount'))['total'] or 0,
        'recent_bookings': Booking.objects.select_related('customer', 'vehicle')[:6], 'recent_payments': Payment.objects.select_related('customer')[:6],
        'attention_vehicles': Vehicle.objects.filter(status__in=[Vehicle.Status.MAINTENANCE, Vehicle.Status.DAMAGED]),
    }
    return render(request, 'dashboard/staff_dashboard.html', context)


@login_required
def cart(request):
    if request.user.is_staff:
        return redirect('dashboard:staff')
    saved = list(request.user.saved_vehicles.select_related('vehicle__category'))
    pending = request.user.bookings.filter(status=Booking.Status.PENDING).select_related('vehicle', 'vehicle_return')
    pending_orders = [
        {'booking': booking, 'whatsapp_url': payment_chat_url(booking), 'balance': booking.outstanding_balance}
        for booking in pending
    ]
    return render(request, 'dashboard/cart.html', {
        'saved_cars': saved, 'saved_vehicle_ids': {item.vehicle_id for item in saved},
        'pending_orders': pending_orders,
        'cart_checkout': True, 'today': timezone.localdate().isoformat(),
    })


@staff_member_required
def customers(request):
    return render(request, 'dashboard/customers.html', {'customers': User.objects.filter(is_staff=False).select_related('profile')})
