(() => {
  const loader = document.getElementById('ride-preloader');
  if (!loader) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (reducedMotion.matches) return;
  // Keep repeat navigation and form validation quick: one intro per tab session.
  const sessionKey = 'rideflow-intro-seen';
  try {
    if (sessionStorage.getItem(sessionKey)) return;
    sessionStorage.setItem(sessionKey, '1');
  } catch {
    // Storage can be unavailable in restricted browsing; the intro still exits.
  }
  const started = performance.now();
  let leaving = false;
  let exitTimer;
  const dismiss = () => {
    if (leaving) return;
    leaving = true;
    clearTimeout(exitTimer);
    loader.classList.add('is-leaving');
    // Do not strand keyboard focus on a button that is about to disappear.
    if (loader.contains(document.activeElement)) document.activeElement.blur();
    window.setTimeout(() => { loader.hidden = true; }, 320);
  };
  loader.querySelector('[data-skip-preloader]').addEventListener('click', dismiss);
  loader.addEventListener('keydown', event => {
    if (event.key === 'Escape') dismiss();
  });
  reducedMotion.addEventListener('change', event => { if (event.matches) dismiss(); });
  window.addEventListener('pageshow', event => { if (event.persisted) dismiss(); });
  loader.hidden = false;
  // Never block the page waiting for third-party styles, scripts, or images.
  exitTimer = window.setTimeout(dismiss, 6700);
  const ready = () => {
    if (leaving) return;
    clearTimeout(exitTimer);
    exitTimer = window.setTimeout(dismiss, Math.max(0, 6700 - (performance.now() - started)));
  };
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', ready, { once: true });
  } else {
    ready();
  }
})();
