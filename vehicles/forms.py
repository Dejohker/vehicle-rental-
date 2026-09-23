from django import forms

from .models import Vehicle, VehicleCategory


class VehicleFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=150, label='Keyword')
    brand = forms.ChoiceField(required=False, choices=[('', 'All brands')])
    year_min = forms.IntegerField(required=False, min_value=2006, max_value=2026, label='Year from')
    year_max = forms.IntegerField(required=False, min_value=2006, max_value=2026, label='Year to')
    sort = forms.ChoiceField(required=False, choices=[('', 'Featured first'), ('price_low', 'Price: low to high'), ('price_high', 'Price: high to low'), ('newest', 'Newest year'), ('oldest', 'Oldest year')], label='Sort by')
    category = forms.ModelChoiceField(queryset=VehicleCategory.objects.filter(active=True), required=False, empty_label='All categories')
    transmission = forms.ChoiceField(choices=[('', 'All transmissions'), *Vehicle.Transmission.choices], required=False)
    fuel_type = forms.ChoiceField(choices=[('', 'All fuels'), *Vehicle.FuelType.choices], required=False)
    seats = forms.IntegerField(min_value=1, max_value=100, required=False, label='Minimum seats')
    min_price = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False, label='Minimum daily price')
    max_price = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, required=False, label='Maximum daily price')
    availability = forms.BooleanField(required=False, label='Available now')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].choices = [('', 'All brands')] + [(brand, brand) for brand in Vehicle.objects.filter(active=True).order_by('brand').values_list('brand', flat=True).distinct()]
        for field in self.fields.values():
            field.widget.attrs['class'] = (
                'form-check-input' if isinstance(field.widget, forms.CheckboxInput)
                else 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            )

    def clean(self):
        data = super().clean()
        minimum, maximum = data.get('min_price'), data.get('max_price')
        if minimum is not None and maximum is not None and minimum > maximum:
            self.add_error('max_price', 'Maximum price must be at least the minimum price.')
        start, end = data.get('year_min'), data.get('year_max')
        if start is not None and end is not None and start > end:
            self.add_error('year_max', 'End year must be at least the start year.')
        return data


class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = '__all__'
        widgets = {'description': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control')
