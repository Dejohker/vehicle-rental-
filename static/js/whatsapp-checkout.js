(() => {
  const link = document.getElementById('whatsapp-payment-link');
  if (!link) return;
  const key = `rideflow-whatsapp-${link.dataset.bookingReference}`;
  try {
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, '1');
  } catch {
    // The server also limits automatic redirects to the first checkout visit.
  }
  const timer = window.setTimeout(() => {
    // Same-tab navigation avoids popup blockers; the visible link is the fallback.
    window.location.assign(link.href);
  }, 600);
  link.addEventListener('click', () => window.clearTimeout(timer), { once: true });
  window.addEventListener('pagehide', () => window.clearTimeout(timer), { once: true });
})();
