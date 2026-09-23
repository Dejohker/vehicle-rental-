from urllib.parse import urlencode

from django.conf import settings


def payment_chat_url(booking):
    balance = booking.outstanding_balance
    if balance <= 0:
        return None
    number = ''.join(character for character in settings.WHATSAPP_PAYMENT_NUMBER if character in '0123456789')
    if not number:
        return None
    message = (
        'Hello RideFlow, I would like to arrange payment for my car rental.\n\n'
        f'Booking reference: {booking.booking_reference}\n'
        f'Car: {booking.vehicle}\n'
        f'Pickup: {booking.pickup_date:%Y-%m-%d}\n'
        f'Return: {booking.return_date:%Y-%m-%d}\n'
        f'Booking total: NGN {booking.total_amount:,.2f}\n'
        f'Amount outstanding: NGN {balance:,.2f}\n\n'
        'Please confirm availability and send me the payment instructions.'
    )
    return f'https://wa.me/{number}?{urlencode({"text": message})}'
