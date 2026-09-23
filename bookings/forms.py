from django import forms
from django.utils import timezone

from .models import Booking, VehicleReturn


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ('pickup_date', 'return_date')
        widgets = {'pickup_date': forms.DateInput(attrs={'type': 'date'}), 'return_date': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, vehicle=None, customer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.vehicle = vehicle
        self.instance.customer = customer
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['min'] = timezone.localdate().isoformat()


class StatusForm(forms.Form):
    status = forms.ChoiceField()

    def __init__(self, *args, booking, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = Booking.TRANSITIONS.get(booking.status, set()) - {Booking.Status.RETURNED}
        self.fields['status'].choices = [(value, label) for value, label in Booking.Status.choices if value in allowed]
        self.fields['status'].widget.attrs['class'] = 'form-select'


class VehicleReturnForm(forms.ModelForm):
    class Meta:
        model = VehicleReturn
        fields = ('actual_return_date', 'condition_notes', 'damage_reported', 'damage_charge', 'late_fee', 'additional_charge')
        widgets = {'actual_return_date': forms.DateInput(attrs={'type': 'date'}), 'condition_notes': forms.Textarea(attrs={'rows': 3})}

    def __init__(self, *args, booking, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.booking = booking
        self.instance.expected_return_date = booking.return_date
        self.fields['actual_return_date'].initial = timezone.localdate()
        self.fields['actual_return_date'].widget.attrs.update({
            'min': booking.pickup_date.isoformat(), 'max': timezone.localdate().isoformat(),
        })
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-control'
