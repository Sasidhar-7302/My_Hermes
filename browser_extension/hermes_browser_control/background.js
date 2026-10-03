// Hermes Browser Control - Service Worker (Manifest V3)
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    hermesBrowserControlVersion: "1.0.0",
    installedAt: new Date().toISOString()
  });
});
