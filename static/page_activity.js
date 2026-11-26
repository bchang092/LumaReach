(() => {
  const widget = document.querySelector('.page-pulse');
  const {page, endpoint, token} = widget.dataset;
  const buttons = widget.querySelectorAll('button');
  const status = widget.querySelector('[role=status]');
  widget.hidden = false;

  function send(event, count = 1) {
    return fetch(endpoint, {
      method: 'POST', credentials: 'same-origin', keepalive: true,
      referrerPolicy: 'no-referrer', headers: {'X-CSRFToken': token},
      body: new URLSearchParams({page, event, count})
    });
  }

  // Only send counters. The target, label, URL, and field values stay in the browser.
  const automatic = navigator.doNotTrack !== '1' && !navigator.globalPrivacyControl;
  if (automatic) {
    let clicks = 0, timer;
    function flush() {
      clearTimeout(timer);
      if (clicks) send('clicks', clicks).catch(() => {});
      clicks = 0;
    }
    send('views').catch(() => {});
    document.addEventListener('click', event => {
      if (!event.isTrusted || widget.contains(event.target)) return;
      if (++clicks === 1) timer = setTimeout(flush, 2000);
      if (clicks === 100) flush();
    }, true);
    document.addEventListener('visibilitychange', () => { if (document.hidden) flush(); });
    window.addEventListener('pagehide', flush);
  }

  buttons.forEach(button => button.addEventListener('click', async () => {
    buttons.forEach(b => b.disabled = true);
    try {
      const response = await send(button.dataset.vote);
      if (!response.ok) throw new Error();
      buttons.forEach(b => b.hidden = true);
      widget.firstElementChild.hidden = true;
      status.textContent = 'Thank you for your feedback.';
    } catch {
      buttons.forEach(b => b.disabled = false);
      status.textContent = 'Couldn’t save your vote. Please try again.';
    }
  }));
})();
