const { invoke } = window.__TAURI__.core;
const root = document.getElementById('root');
let activeView = 'newtab';

async function request(req) {
  return invoke('engine_request', { request: req });
}
function dataUrl(mime, body) {
  return `data:${mime};charset=utf-8,${encodeURIComponent(body)}`;
}
async function show(url = 'sreon://newtab') {
  activeView = url;
  const page = await request({ op: 'page', url });
  if (!page || page.status >= 400) throw new Error(page?.body || 'Page unavailable');
  const css = await request({ op: 'page', url: 'sreon://assets/sreon.css' });
  const js = await request({ op: 'page', url: 'sreon://assets/sreon.js' });
  const studioCss = await request({ op: 'page', url: 'sreon://assets/studio.css' });
  const studioJs = await request({ op: 'page', url: 'sreon://assets/studio.js' });
  const html = page.body
    .replaceAll('sreon://assets/sreon.css', dataUrl('text/css', css.body))
    .replaceAll('sreon://assets/studio.css', dataUrl('text/css', studioCss.body))
    .replaceAll('sreon://assets/sreon.js', dataUrl('text/javascript', js.body))
    .replaceAll('sreon://assets/studio.js', dataUrl('text/javascript', studioJs.body));
  const frame = document.createElement('iframe');
  frame.setAttribute('allow', 'clipboard-read; clipboard-write; fullscreen');
  frame.srcdoc = html;
  root.replaceChildren(frame);
}
window.sreonHost = {
  async call(op, view, data) {
    const r = await request({ op, view, data });
    for (const a of (r.host || [])) {
      if (a.do === 'open' && a.url?.startsWith('sreon://')) await show(a.url);
      else if (a.do === 'open' && a.url) window.open(a.url, '_blank');
    }
    return r;
  }
};
(async () => {
  try {
    await request({ op: 'boot', dark: true });
    await request({ op: 'ready' });
    await show();
  } catch (e) {
    root.innerHTML = `<div id="error"><h2>Sreon could not start</h2><p>${String(e.message || e)}</p><p>Check that the SPRFST engine is installed with the application.</p></div>`;
  }
})();
