// Hermes Browser Control - DOM Bridge
(() => {
  if (window.__HERMES_BROWSER_CONTROL__) {
    return;
  }

  const normalizeText = (value) => String(value || "").replace(/\s+/g, " ").trim();

  const isVisible = (element) => {
    if (!element) return false;
    const style = window.getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity || "1") === 0) {
      return false;
    }
    const rect = element.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) return false;
    return rect.bottom >= 0 && rect.top <= window.innerHeight;
  };

  const collectInteractive = (maxElements = 80) => {
    const selector = [
      "a[href]",
      "button",
      "input",
      "textarea",
      "select",
      "[role='button']",
      "[role='link']",
      "[contenteditable='true']"
    ].join(",");
    const nodes = Array.from(document.querySelectorAll(selector));
    const elements = [];
    for (const node of nodes) {
      if (!isVisible(node)) continue;
      const rect = node.getBoundingClientRect();
      const label = normalizeText(
        node.innerText ||
          node.textContent ||
          node.getAttribute("aria-label") ||
          node.getAttribute("placeholder") ||
          node.getAttribute("name")
      );
      elements.push({
        ref: node.id ? `#${node.id}` : `${node.tagName.toLowerCase()}:${elements.length + 1}`,
        tag: node.tagName.toLowerCase(),
        role: node.getAttribute("role") || "",
        text: label,
        x: Math.round(rect.left),
        y: Math.round(rect.top),
        width: Math.round(rect.width),
        height: Math.round(rect.height)
      });
      if (elements.length >= Math.max(10, Number(maxElements || 80))) break;
    }
    return { elements, interactive_count: elements.length };
  };

  const readVisibleText = (maxLength = 3000) => {
    const nodes = Array.from(document.body ? document.body.querySelectorAll("*") : []);
    const parts = [];
    const seen = new Set();
    for (const node of nodes) {
      if (!isVisible(node)) continue;
      const text = normalizeText(node.innerText || node.textContent || "");
      if (!text || text.length < 2 || seen.has(text)) continue;
      seen.add(text);
      parts.push(text);
      if (parts.join("\n").length >= Math.max(400, Number(maxLength || 3000))) break;
    }
    return parts.join("\n").slice(0, Math.max(400, Number(maxLength || 3000)));
  };

  const pageState = () => {
    const url = String(window.location.href || "");
    const title = String(document.title || "");
    const bodyText = normalizeText(document.body ? document.body.innerText || "" : "").toLowerCase();
    if (/captcha|verify you are human/.test(bodyText)) return "captcha";
    if (/sign in|log in|continue with google/.test(bodyText) || /login|signin|auth/.test(url)) return "login_required";
    if (/getting started|onboarding|plans that grow with you/.test(bodyText)) return "onboarding_gate";
    if (/allow all|accept all|cookie/.test(bodyText)) return "consent_modal";
    return "ready";
  };

  window.__HERMES_BROWSER_CONTROL__ = {
    version: "1.0.0",
    collectSnapshot({ maxElements = 80 } = {}) {
      return {
        url: String(window.location.href || ""),
        title: String(document.title || ""),
        page_state: pageState(),
        listing: collectInteractive(maxElements)
      };
    },
    readVisibleText(maxLength = 3000) {
      return readVisibleText(maxLength);
    }
  };
})();
