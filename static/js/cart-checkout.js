document.querySelectorAll('.cart-checkout').forEach((form) => {
  const pickup = form.elements.pickup_date;
  const returned = form.elements.return_date;
  const money = new Intl.NumberFormat('en-NG', { style: 'currency', currency: 'NGN' });
  const update = () => {
    const days = Math.round((returned.valueAsNumber - pickup.valueAsNumber) / 86400000);
    const valid = Number.isFinite(days) && days > 0;
    returned.setCustomValidity(returned.value && pickup.value && !valid ? 'Return date must be after pickup date.' : '');
    form.querySelector('[data-days]').textContent = valid ? days : 'Choose valid dates';
    const rental = days * Number(form.dataset.rate);
    form.querySelector('[data-rental]').textContent = valid ? money.format(rental) : '—';
    form.querySelector('[data-total]').textContent = valid ? money.format(rental + Number(form.dataset.deposit)) : '—';
  };
  pickup.addEventListener('input', update);
  returned.addEventListener('input', update);
});
