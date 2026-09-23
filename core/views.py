from django.contrib import messages
from django.shortcuts import redirect, render

from vehicles.models import Vehicle, VehicleCategory
from vehicles.utils import saved_vehicle_ids
from .forms import ContactForm


def home(request):
    return render(request, 'core/home.html', {'featured_vehicles': Vehicle.objects.filter(active=True, featured=True).select_related('category')[:6], 'categories': VehicleCategory.objects.filter(active=True)[:6], 'saved_vehicle_ids': saved_vehicle_ids(request.user)})


def about(request):
    return render(request, 'core/about.html')


def contact(request):
    form = ContactForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Thank you. Your message has been received.')
        return redirect('core:contact')
    return render(request, 'core/contact.html', {'form': form})


def permission_denied(request, exception):
    return render(request, '403.html', status=403)


def page_not_found(request, exception):
    return render(request, '404.html', status=404)


def server_error(request):
    return render(request, '500.html', status=500)
