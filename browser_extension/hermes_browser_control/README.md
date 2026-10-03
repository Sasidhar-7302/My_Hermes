# Hermes Browser Control (Manifest V3)

A high-performance, non-intrusive Chrome/Edge extension that bridges live, logged-in browser tabs with Hermes Agent.

## Why this is better than standalone Selenium / Playwright:
1. **Zero Bot Detection**: Runs directly inside your primary user profile with existing session cookies, Google logins, GitHub logins, and workspace tabs.
2. **Bypasses Cloudflare / Turnstile**: Does not trigger the automated bot challenge walls common in headless browsers.
3. **Instant DOM Snapshotting**: Gathers all interactive elements (`<a>`, `<button>`, `<input>`, `[role=button]`, `select`) along with bounding client rectangles and text labels in sub-50ms.
4. **Autonomous Gate Detection**: Detects CAPTCHA gates, login redirects, cookie consent dialogs, and onboarding screens.

## Installation in Chrome / Brave / Edge:
1. Open your browser and navigate to `chrome://extensions` (or `edge://extensions`).
2. Toggle on **Developer mode** in the top right corner.
3. Click **Load unpacked**.
4. Select the directory:
   `c:\Users\yepur\Desktop\My_Projects\Hermes agent\app\browser_extension\hermes_browser_control`
5. The extension will appear as **Hermes Browser Control**!
