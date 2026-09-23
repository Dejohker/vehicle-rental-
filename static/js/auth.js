document.querySelectorAll('[data-password-toggle]').forEach(button => {
  const input = document.getElementById(button.getAttribute('aria-controls'));
  if (!input) return;
  const showLabel = button.getAttribute('aria-label');
  button.hidden = false;
  button.addEventListener('click', () => {
    const visible = input.type === 'password';
    input.type = visible ? 'text' : 'password';
    button.textContent = visible ? 'Hide' : 'Show';
    button.setAttribute('aria-pressed', String(visible));
    button.setAttribute('aria-label', visible ? showLabel.replace('Show ', 'Hide ') : showLabel);
  });
  const warning = document.querySelector(`[data-caps-warning="${input.id}"]`);
  if (!warning) return;
  const updateCapsLock = event => {
    warning.hidden = !event.getModifierState?.('CapsLock');
  };
  input.addEventListener('keydown', updateCapsLock);
  input.addEventListener('keyup', updateCapsLock);
  input.addEventListener('blur', () => { warning.hidden = true; });
});
