/* Basic consent mode: no Google code or configuration before an explicit opt-in. */
(() => {
  'use strict';
  const measurementId = 'G-12FDG0Z8JB';
  const storageKey = '3dpi.analyticsConsent.v1';
  const siteRoot = new URL('../', document.currentScript.src);
  const denied = {analytics_storage:'denied', ad_storage:'denied', ad_user_data:'denied', ad_personalization:'denied'};
  let choice = readChoice();
  let started = false;
  window['ga-disable-' + measurementId] = choice !== 'granted';

  function readChoice() {
    try {
      const saved = localStorage.getItem(storageKey);
      return ['granted', 'denied'].includes(saved) ? saved : null;
    } catch { return null; }
  }

  function clearAnalyticsCookies() {
    const paths = new Set(['/', siteRoot.pathname]);
    const segments = location.pathname.split('/');
    for (let index = 1; index < segments.length; index++) paths.add(segments.slice(0, index).join('/') + '/');
    const domains = ['', location.hostname, '.' + location.hostname];
    const parts = location.hostname.split('.');
    for (let index = 1; index < parts.length - 1; index++) domains.push('.' + parts.slice(index).join('.'));
    for (const cookie of document.cookie.split(';')) {
      const name = cookie.split('=')[0].trim();
      if (!/^(?:_ga(?:_|$)|3dpi_ga(?:_|$))/.test(name)) continue;
      for (const path of paths) for (const domain of domains) {
        document.cookie = name + '=; Max-Age=0; path=' + path + (domain ? '; domain=' + domain : '') + '; SameSite=Lax';
      }
    }
  }

  function enableAnalytics() {
    if (started || choice !== 'granted') return;
    started = true;
    window['ga-disable-' + measurementId] = false;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('consent', 'default', denied);
    window.gtag('consent', 'update', {...denied, analytics_storage:'granted'});
    window.gtag('js', new Date());
    window.gtag('config', measurementId, {
      allow_google_signals:false,
      allow_ad_personalization_signals:false,
      cookie_domain:'none',
      cookie_path:siteRoot.pathname,
      cookie_prefix:'3dpi',
      cookie_expires:31536000,
      // Do not forward comparison query strings or fragments as page locations.
      page_location:location.origin + location.pathname
    });
    const script = document.createElement('script');
    script.async = true;
    script.dataset.analyticsLoader = '';
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + measurementId;
    document.head.append(script);
  }

  function stopAnalytics() {
    window['ga-disable-' + measurementId] = true;
    clearAnalyticsCookies();
    if (started) {
      document.querySelector('[data-analytics-loader]')?.remove();
      // Reload instead of using advanced-mode denied pings from a loaded tag.
      // The disabling flag stops collection until the running library is discarded.
      location.reload();
    }
  }

  const banner = document.createElement('section');
  banner.id = 'analytics-consent';
  banner.className = 'analytics-consent';
  banner.setAttribute('aria-labelledby', 'analytics-consent-heading');
  banner.innerHTML = '<div><h2 id="analytics-consent-heading">Optional analytics</h2><p>Allow Google Analytics to help us understand visits? Google code and analytics cookies stay off until you allow them. Your choice does not affect access to this site. <a href="' + siteRoot.href + 'privacy.html">Privacy details</a></p></div><div class="analytics-actions"><button type="button" data-analytics-decline>Decline analytics</button><button type="button" data-analytics-allow>Allow analytics</button></div>';
  banner.hidden = choice !== null;
  document.body.append(banner);

  const dialog = document.createElement('dialog');
  dialog.id = 'analytics-settings';
  dialog.className = 'analytics-settings';
  dialog.setAttribute('aria-labelledby', 'analytics-settings-heading');
  dialog.innerHTML = '<h2 id="analytics-settings-heading">Analytics settings</h2><p data-analytics-status></p><p>You can use every page without analytics. Declining after an earlier grant withdraws consent and reloads this page to stop the loaded Google code. Previously sent data is not deleted. <a href="' + siteRoot.href + 'privacy.html">Privacy details</a></p><div class="analytics-actions"><button type="button" data-analytics-decline>Decline analytics</button><button type="button" data-analytics-allow>Allow analytics</button><button type="button" data-analytics-close>Close settings</button></div>';
  document.body.append(dialog);

  function updateInterface() {
    banner.hidden = choice !== null;
    dialog.querySelector('[data-analytics-status]').textContent = choice === 'granted' ? 'Analytics is currently allowed in this browser.' : 'Analytics is currently off in this browser.';
  }

  function select(value) {
    choice = value;
    try { localStorage.setItem(storageKey, value); } catch { /* This page still honors the choice when storage is blocked. */ }
    dialog.close();
    updateInterface();
    if (value === 'granted') enableAnalytics();
    else stopAnalytics();
  }

  for (const panel of [banner, dialog]) {
    panel.querySelector('[data-analytics-allow]').addEventListener('click', () => select('granted'));
    panel.querySelector('[data-analytics-decline]').addEventListener('click', () => select('denied'));
  }
  dialog.querySelector('[data-analytics-close]').addEventListener('click', () => dialog.close());
  for (const button of document.querySelectorAll('[data-analytics-settings]')) {
    button.hidden = false;
    button.addEventListener('click', () => { updateInterface(); dialog.showModal(); });
  }
  addEventListener('storage', event => {
    if (event.key !== storageKey && event.key !== null) return;
    choice = readChoice();
    updateInterface();
    if (choice === 'granted') enableAnalytics();
    else stopAnalytics();
  });
  updateInterface();
  if (choice === 'granted') enableAnalytics();
  else clearAnalyticsCookies();
})();
