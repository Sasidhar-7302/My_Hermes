// Hermes Browser Control - Content Script
(() => {
  try {
    if (window.__HERMES_BROWSER_CONTROL_INJECTED__) {
      return;
    }
    window.__HERMES_BROWSER_CONTROL_INJECTED__ = true;
    const script = document.createElement("script");
    script.src = chrome.runtime.getURL("bridge.js");
    script.async = false;
    script.onload = () => {
      try {
        script.remove();
      } catch (_) {}
    };
    (document.documentElement || document.head || document.body).appendChild(script);
  } catch (_) {}
})();
