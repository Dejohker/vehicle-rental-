from bookings.models import Booking


def customer_cart(request):
    if not request.user.is_authenticated or request.user.is_staff:
        return {'cart_item_count': 0}
    saved_count = request.user.saved_vehicles.count()
    pending_count = request.user.bookings.filter(status=Booking.Status.PENDING).count()
    return {'cart_item_count': saved_count + pending_count}
