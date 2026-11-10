/**
 * UI components and DOM construction helpers.
 * Every dynamic string is rendered via textContent/createTextNode, never innerHTML.
 */

const AVATAR_PALETTE = [
  { bg: "#CDE8EC", text: "#0A4F5A" },
  { bg: "#FBE3C2", text: "#7A4A06" },
  { bg: "#DDE6FB", text: "#26407A" },
  { bg: "#F6D9E3", text: "#7A2646" },
  { bg: "#DDF0D8", text: "#285C1E" },
  { bg: "#E8DDF7", text: "#4A2C7A" },
  { bg: "#F9ECC2", text: "#6B5200" },
  { bg: "#D8EEE8", text: "#145A4B" },
];

/**
 * Build DOM elements safely. Children that are strings/numbers become Text nodes.
 */
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);

  for (const [key, val] of Object.entries(attrs || {})) {
    if (val === null || val === undefined) continue;

    if (key.startsWith("on") && typeof val === "function") {
      const eventName = key.slice(2).toLowerCase();
      node.addEventListener(eventName, val);
    } else if (key === "className" || key === "class") {
      node.className = val;
    } else if (key === "style" && typeof val === "object") {
      Object.assign(node.style, val);
    } else if (typeof val === "boolean") {
      if (val) {
        node.setAttribute(key, "");
      }
    } else {
      node.setAttribute(key, val);
    }
  }

  function appendChildSafe(child) {
    if (child === null || child === undefined || child === false) return;
    if (Array.isArray(child)) {
      child.forEach(appendChildSafe);
    } else if (child instanceof Node) {
      node.appendChild(child);
    } else {
      node.appendChild(document.createTextNode(String(child)));
    }
  }

  children.forEach(appendChildSafe);
  return node;
}

/**
 * Extract person's initials: first letters of first two words, uppercase.
 */
export function getInitials(name) {
  if (!name) return "?";
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return "?";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

/**
 * Deterministic avatar component.
 */
export function avatar(user, size = 40) {
  const userId = user && typeof user.id === "number" ? user.id : 0;
  const name = (user && user.name) || "User";
  const color = AVATAR_PALETTE[Math.abs(userId) % AVATAR_PALETTE.length];
  const initials = getInitials(name);

  return el(
    "span",
    {
      className: `avatar avatar-${size}`,
      style: {
        backgroundColor: color.bg,
        color: color.text,
      },
      title: name,
      "aria-label": name,
    },
    initials
  );
}

/**
 * Avatar stack component with max limit.
 */
export function avatarStack(users, size = 32, max = 4) {
  const displayUsers = (users || []).slice(0, max);
  const remaining = (users || []).length - max;

  const stack = el("div", { className: "avatar-stack" });
  for (const u of displayUsers) {
    stack.appendChild(avatar(u, size));
  }
  if (remaining > 0) {
    stack.appendChild(
      el("span", { className: "avatar-stack-more" }, `+${remaining}`)
    );
  }
  return stack;
}

/**
 * Toast notifications. Max 3 stacked. Auto-dismiss after 4s (errors 6s).
 */
export function toast(message, options = {}) {
  const container = document.getElementById("toasts");
  if (!container) return;

  // Max 3 toasts
  while (container.children.length >= 3) {
    container.removeChild(container.firstChild);
  }

  const isError = options.type === "error";
  const duration = isError ? 6000 : 4000;

  let timeoutId;
  const dismiss = () => {
    clearTimeout(timeoutId);
    if (toastEl.parentNode) {
      toastEl.parentNode.removeChild(toastEl);
    }
  };

  const children = [el("span", {}, message)];

  if (options.action) {
    const actionBtn = el(
      "button",
      {
        type: "button",
        className: "toast-undo-btn",
        onClick: async (e) => {
          e.preventDefault();
          dismiss();
          if (typeof options.action.onClick === "function") {
            await options.action.onClick();
          }
        },
      },
      options.action.label || "Undo"
    );
    children.push(actionBtn);
  }

  const toastEl = el(
    "div",
    {
      className: `toast ${isError ? "toast-error" : ""}`,
      role: "status",
      "aria-live": "polite",
    },
    ...children
  );

  container.appendChild(toastEl);
  timeoutId = setTimeout(dismiss, duration);
}

/**
 * Native dialog wrapper.
 * Returns a close function.
 */
export function openDialog(contentNode, { title, onUnsavedCheck = null } = {}) {
  const previouslyFocused = document.activeElement;

  const dialogEl = el("dialog", {
    "aria-labelledby": "dialog-title",
  });

  const close = () => {
    dialogEl.close();
    if (dialogEl.parentNode) {
      dialogEl.parentNode.removeChild(dialogEl);
    }
    if (previouslyFocused && typeof previouslyFocused.focus === "function") {
      previouslyFocused.focus();
    }
  };

  const closeBtn = el(
    "button",
    {
      type: "button",
      className: "dialog-close-btn",
      "aria-label": "Close dialog",
      onClick: close,
    },
    "✕"
  );

  const header = el(
    "div",
    { className: "dialog-header" },
    el("h2", { id: "dialog-title", className: "dialog-title" }, title),
    closeBtn
  );

  const card = el("div", { className: "dialog-card" }, header, contentNode);
  dialogEl.appendChild(card);

  // Backdrop click handling
  dialogEl.addEventListener("click", (e) => {
    const rect = card.getBoundingClientRect();
    const clickedInside =
      e.clientX >= rect.left &&
      e.clientX <= rect.right &&
      e.clientY >= rect.top &&
      e.clientY <= rect.bottom;

    if (!clickedInside) {
      if (onUnsavedCheck && onUnsavedCheck()) {
        // Unsaved changes, ignore backdrop click
        return;
      }
      close();
    }
  });

  // Esc key close handling
  dialogEl.addEventListener("cancel", (e) => {
    e.preventDefault();
    if (onUnsavedCheck && onUnsavedCheck()) {
      return;
    }
    close();
  });

  document.body.appendChild(dialogEl);
  dialogEl.showModal();

  return close;
}

/**
 * Custom confirm dialog. Never uses window.confirm. Returns Promise<boolean>.
 */
export function confirmDialog({ title, body, confirmLabel = "Delete" }) {
  return new Promise((resolve) => {
    let close;

    const content = el(
      "div",
      {},
      el("p", { style: { color: "var(--slate)", marginBottom: "var(--s4)" } }, body),
      el(
        "div",
        { className: "dialog-actions" },
        el(
          "button",
          {
            type: "button",
            className: "btn",
            onClick: () => {
              close();
              resolve(false);
            },
          },
          "Keep it"
        ),
        el(
          "button",
          {
            type: "button",
            className: "btn btn-danger",
            onClick: () => {
              close();
              resolve(true);
            },
          },
          confirmLabel
        )
      )
    );

    close = openDialog(content, { title });
  });
}

/**
 * Parse YYYY-MM-DD as local date without timezone shifts.
 */
export function parseLocalDate(dateStr) {
  if (!dateStr) return new Date();
  const parts = dateStr.split("T")[0].split("-");
  return new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
}

/**
 * Format date for display: "2 Nov".
 */
export function formatDate(dateStr) {
  const dt = parseLocalDate(dateStr);
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short" }).format(dt);
}

/**
 * Format month header: "November 2026".
 */
export function formatMonthYear(dateStr) {
  const dt = parseLocalDate(dateStr);
  return new Intl.DateTimeFormat("en-IN", { month: "long", year: "numeric" }).format(dt);
}
