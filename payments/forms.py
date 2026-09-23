from django import forms
from .models import Payment


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ('booking', 'amount', 'payment_method', 'transaction_reference', 'payment_status', 'payment_date')
        widgets = {'payment_date': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
        self.fields['payment_status'].help_text = 'Paid and Partial both record money received. Pending, Failed and Refunded do not reduce the balance.'

    def save(self, commit=True):
        payment = super().save(commit=False)
        payment.customer = payment.booking.customer
        if commit:
            payment.full_clean()
            payment.save()
        return payment
