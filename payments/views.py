from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PaymentForm
from .models import Payment


@staff_member_required
def payment_list(request):
    return render(request, 'payments/payment_list.html', {'payments': Payment.objects.select_related('booking', 'customer')})


@staff_member_required
def payment_create(request):
    form = PaymentForm(request.POST or None, initial={'booking': request.GET.get('booking')})
    if request.method == 'POST' and form.is_valid():
        payment = form.save()
        messages.success(request, 'Payment recorded successfully.')
        return redirect('payments:detail', pk=payment.pk)
    return render(request, 'payments/payment_form.html', {'form': form})


@login_required
def payment_detail(request, pk):
    payments = Payment.objects.select_related('booking', 'customer')
    if not request.user.is_staff:
        payments = payments.filter(customer=request.user)
    return render(request, 'payments/payment_detail.html', {'payment': get_object_or_404(payments, pk=pk)})
