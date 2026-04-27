/* ─────────────────────────────────────────────────────────────────────────
   NoorFamily Dashboard — vanilla JS, zero build
   Design system: Minimalism + Micro-interactions
   ───────────────────────────────────────────────────────────────────────── */

// ── DOM helpers — h() builds elements via API (textContent, never innerHTML),
//                  so user data can never become HTML. Kills the XSS class.
function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  if (attrs) {
    for (const [k, v] of Object.entries(attrs)) {
      if (v === false || v == null) continue;
      if (k === "class") el.className = v;
      else if (k === "html") el.innerHTML = v; // explicit opt-in for SAFE static HTML
      else if (k === "dataset") Object.assign(el.dataset, v);
      else if (k.startsWith("on") && typeof v === "function") el.addEventListener(k.slice(2), v);
      else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
      else el.setAttribute(k, v);
    }
  }
  for (const c of children.flat()) {
    if (c == null || c === false) continue;
    if (c instanceof Node) el.appendChild(c);
    else el.appendChild(document.createTextNode(String(c)));
  }
  return el;
}
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// ── Icon set (Lucide) — inline SVG paths, no network ───────────────────────
const ICONS = {
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  bell: '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>',
  list: '<line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  settings: '<path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  edit: '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  pause: '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>',
  play: '<polygon points="5 3 19 12 5 21 5 3"/>',
  search: '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  alert: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
  info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>',
  moon: '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
  sun: '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
  refresh: '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  gitBranch: '<line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/>',
};
function icon(name, attrs = {}) {
  const svg = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ""}</svg>`;
  return h("span", { html: svg, class: "icon", ...attrs });
}

// ── Toast component ─────────────────────────────────────────────────────────
const TOAST_ICONS = { success: "check", error: "alert", warn: "alert", info: "info" };
function toast(message, kind = "info", timeout = 4000) {
  const region = $("#toast-region");
  const node = h("div",
    { class: `toast toast-${kind}`, role: kind === "error" ? "alert" : "status" },
    h("span", { class: "toast-icon", html: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[TOAST_ICONS[kind] || "info"]}</svg>` }),
    h("div", { class: "toast-body" }, message),
    h("button", {
      class: "toast-close",
      "aria-label": "Dismiss",
      onclick: () => dismiss(),
      html: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS.x}</svg>`,
    }),
  );
  region.appendChild(node);
  let timer = setTimeout(dismiss, timeout);
  function dismiss() {
    clearTimeout(timer);
    node.classList.add("dismissing");
    setTimeout(() => node.remove(), 250);
  }
  return dismiss;
}

// ── Modal with focus trap + Escape + scrim click ────────────────────────────
let _modalRestore = null;
function openModal({ title, body, actions = [] }) {
  closeModal();
  _modalRestore = document.activeElement;

  const closeBtn = h("button", {
    class: "icon-btn",
    "aria-label": "Close dialog",
    onclick: closeModal,
    html: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS.x}</svg>`,
  });

  const titleEl = h("h2", { class: "modal-title", id: "modal-title" }, title || "");
  const bodyEl = h("div", { class: "modal-body" });
  if (body instanceof Node) bodyEl.appendChild(body);
  else if (typeof body === "string") bodyEl.appendChild(document.createTextNode(body));

  // If body contains a <form>, route any submit-typed action button to it.
  // (The button lives in the modal footer, outside the form, so a plain
  // type="submit" wouldn't fire the form's submit event by itself.)
  const formEl = bodyEl.querySelector("form");
  if (formEl) {
    for (const a of actions) {
      if (a.tagName === "BUTTON" && a.type === "submit") {
        a.type = "button";
        a.addEventListener("click", () => {
          if (typeof formEl.requestSubmit === "function") formEl.requestSubmit();
          else formEl.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        });
      }
    }
  }

  const actionsEl = actions.length ? h("div", { class: "modal-actions" }, ...actions) : null;

  const modalCard = h("div", {
    class: "modal",
    role: "dialog",
    "aria-modal": "true",
    "aria-labelledby": "modal-title",
  },
    h("div", { class: "modal-header" }, titleEl, closeBtn),
    bodyEl,
    actionsEl,
  );

  const backdrop = h("div", {
    class: "modal-backdrop",
    onclick: e => { if (e.target === backdrop) closeModal(); },
  }, modalCard);
  backdrop.id = "modal-backdrop";

  document.body.appendChild(backdrop);
  document.body.style.overflow = "hidden";

  // Focus trap
  const focusables = () => $$('input, select, textarea, button, [tabindex]:not([tabindex="-1"])', modalCard)
    .filter(el => !el.disabled && !el.hidden);
  const f = focusables();
  (f[0] || closeBtn).focus();

  modalCard.addEventListener("keydown", e => {
    if (e.key === "Escape") { e.preventDefault(); closeModal(); return; }
    if (e.key !== "Tab") return;
    const list = focusables();
    if (!list.length) return;
    const first = list[0], last = list[list.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  return { close: closeModal };
}
function closeModal() {
  const b = $("#modal-backdrop");
  if (b) b.remove();
  document.body.style.overflow = "";
  if (_modalRestore && _modalRestore.focus) { _modalRestore.focus(); _modalRestore = null; }
}

// ── Confirm async — promise-based replacement for window.confirm() ──────────
function confirmAsync(message, { confirmText = "Confirm", danger = false } = {}) {
  return new Promise(resolve => {
    const cancelBtn = h("button", { class: "btn btn-ghost", onclick: () => { closeModal(); resolve(false); } }, "Cancel");
    const okBtn = h("button", {
      class: `btn ${danger ? "btn-danger" : "btn-primary"}`,
      onclick: () => { closeModal(); resolve(true); },
    }, confirmText);
    openModal({
      title: "Confirm",
      body: h("p", null, message),
      actions: [cancelBtn, okBtn],
    });
  });
}

// ── Button loading state ────────────────────────────────────────────────────
async function withBusy(btn, fn) {
  if (!btn) return await fn();
  const prevHTML = btn.innerHTML;
  const prevDisabled = btn.disabled;
  btn.setAttribute("aria-busy", "true");
  btn.disabled = true;
  btn.innerHTML = "";
  btn.appendChild(h("span", { class: "spinner", "aria-hidden": "true" }));
  btn.appendChild(document.createTextNode(" Working…"));
  try {
    return await fn();
  } finally {
    btn.removeAttribute("aria-busy");
    btn.disabled = prevDisabled;
    btn.innerHTML = prevHTML;
  }
}

// ── API helper ──────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  try {
    const r = await fetch("/api" + path, opts);
    if (!r.ok) {
      let detail = await r.text();
      try { detail = JSON.parse(detail).detail || detail; } catch {}
      toast(`${r.status}: ${detail}`, "error", 6000);
      return null;
    }
    if (r.status === 204) return true;
    return await r.json();
  } catch (e) {
    toast(`Network error: ${e.message}`, "error");
    return null;
  }
}

// ── Theme toggle ────────────────────────────────────────────────────────────
function readTheme() { return localStorage.getItem("nf-theme"); }
function setTheme(mode) {
  if (mode) { document.documentElement.setAttribute("data-theme", mode); localStorage.setItem("nf-theme", mode); }
  else { document.documentElement.removeAttribute("data-theme"); localStorage.removeItem("nf-theme"); }
  paintThemeToggle();
}
function paintThemeToggle() {
  const btn = $("#theme-toggle"); if (!btn) return;
  const dark = document.documentElement.getAttribute("data-theme") === "dark"
    || (!document.documentElement.getAttribute("data-theme")
        && window.matchMedia("(prefers-color-scheme: dark)").matches);
  btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${dark ? ICONS.sun : ICONS.moon}</svg>`;
}

// ── Channel badges ──────────────────────────────────────────────────────────
function chBadges(m) {
  const set = h("span", { class: "channel-set" });
  set.appendChild(h("span", { class: `ch ${m.phone ? "ch-on" : "ch-off"}`, title: m.phone || "no phone" }, "SMS"));
  set.appendChild(h("span", { class: `ch ${m.whatsapp ? "ch-on" : "ch-off"}`, title: m.whatsapp || "no WhatsApp" }, "WA"));
  set.appendChild(h("span", { class: `ch ${m.email ? "ch-on" : "ch-off"}`, title: m.email || "no email" }, "Email"));
  return set;
}

function fmtDays(n) {
  if (n === 0) return "Today";
  if (n === 1) return "Tomorrow";
  return `${n}d`;
}
function pillClassFor(n) { return n === 0 ? "today" : n <= 7 ? "soon" : ""; }

// ── Empty state ─────────────────────────────────────────────────────────────
function emptyState(iconName, title, sub) {
  return h("div", { class: "empty" },
    h("span", { html: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="width:40px;height:40px;display:block;margin:0 auto 12px">${ICONS[iconName]}</svg>` }),
    h("h3", null, title),
    h("p", null, sub),
  );
}

// ── Router ──────────────────────────────────────────────────────────────────
const NAV = [
  { id: "members",       label: "Members",       icon: "users" },
  { id: "tree",          label: "Family Tree",   icon: "gitBranch" },
  { id: "notifications", label: "Notifications", icon: "bell" },
  { id: "logs",          label: "Logs",          icon: "list" },
  { id: "schedule",      label: "Schedule",      icon: "clock" },
  { id: "settings",      label: "Settings",      icon: "settings" },
];
const pages = {};
function navigate(name) {
  const app = $("#app");
  app.replaceChildren();
  $$("#nav-list a").forEach(a => a.classList.toggle("active", a.dataset.page === name));
  closeSidebar();
  if (pages[name]) pages[name](app);
  app.focus();
}
function openSidebar() { $("#sidebar").classList.add("open"); $("#sidebar-scrim").classList.add("open"); }
function closeSidebar() { $("#sidebar").classList.remove("open"); $("#sidebar-scrim").classList.remove("open"); }

// ── Members ─────────────────────────────────────────────────────────────────
function nextEventDays(m) {
  const today = new Date();
  const targets = [];
  if (m.birthday) targets.push({ type: "birthday", date: m.birthday });
  if (m.married && m.anniversary) targets.push({ type: "anniversary", date: m.anniversary });
  let best = null;
  for (const ev of targets) {
    const [mon, day] = ev.date.split("-").map(Number);
    let d = new Date(today.getFullYear(), mon - 1, day);
    if (d < new Date(today.getFullYear(), today.getMonth(), today.getDate())) d.setFullYear(today.getFullYear() + 1);
    const days = Math.round((d - new Date(today.getFullYear(), today.getMonth(), today.getDate())) / 86400000);
    if (best == null || days < best.days) best = { ...ev, days };
  }
  return best;
}

pages.members = async (app) => {
  const [members, upcoming] = await Promise.all([api("GET", "/members"), api("GET", "/members/upcoming")]);
  if (members === null) return;

  const search = h("input", { type: "search", placeholder: "Search members…", "aria-label": "Search members" });
  const tableBody = h("tbody");
  const tableWrap = h("div", { class: "table-wrap" },
    h("table", null,
      h("thead", null,
        h("tr", null,
          h("th", null, "Name"),
          h("th", null, "Birthday"),
          h("th", null, "Anniversary"),
          h("th", null, "Channels"),
          h("th", null, "Next"),
          h("th", null, "Status"),
          h("th", null, "Actions"),
        ),
      ),
      tableBody,
    ),
  );

  function renderRows(filter = "") {
    tableBody.replaceChildren();
    const f = filter.trim().toLowerCase();
    const filtered = members.filter(m => !f || m.name.toLowerCase().includes(f));
    if (!filtered.length) {
      tableBody.appendChild(h("tr", null,
        h("td", { colspan: 7 }, emptyState("users", "No matches", "Try a different search")),
      ));
      return;
    }
    for (const m of filtered) {
      const next = nextEventDays(m);
      tableBody.appendChild(h("tr", null,
        h("td", null, h("strong", null, m.name)),
        h("td", null, m.birthday || "—"),
        h("td", null, m.married && m.anniversary ? m.anniversary : "—"),
        h("td", null, chBadges(m)),
        h("td", null, next ? h("span", { class: `days-pill ${pillClassFor(next.days)}` }, `${fmtDays(next.days)} · ${next.type}`) : "—"),
        h("td", null, m.notifications_paused ? h("span", { class: "badge badge-paused" }, "Paused") : ""),
        h("td", null, h("div", { class: "row-actions" },
          h("button", {
            class: "btn btn-sm btn-ghost",
            "aria-label": `Edit ${m.name}`,
            onclick: () => showMemberForm(m, members),
          }, icon("edit"), "Edit"),
          h("button", {
            class: m.notifications_paused ? "btn btn-sm btn-success" : "btn btn-sm btn-warn",
            onclick: async (e) => {
              await withBusy(e.currentTarget, async () => {
                const r = await api("PUT", `/members/${m.id}/pause`, { paused: !m.notifications_paused });
                if (r) { toast(m.notifications_paused ? "Resumed" : "Paused", "success"); navigate("members"); }
              });
            },
          }, icon(m.notifications_paused ? "play" : "pause"), m.notifications_paused ? "Resume" : "Pause"),
          h("button", {
            class: "btn btn-sm btn-danger",
            "aria-label": `Delete ${m.name}`,
            onclick: async (e) => {
              if (!await confirmAsync(`Delete ${m.name}? This also removes their notification logs.`, { confirmText: "Delete", danger: true })) return;
              await withBusy(e.currentTarget, async () => {
                const r = await api("DELETE", `/members/${m.id}`);
                if (r) { toast(`${m.name} deleted`, "success"); navigate("members"); }
              });
            },
          }, icon("trash"), "Delete"),
        )),
      ));
    }
  }

  search.addEventListener("input", () => renderRows(search.value));
  renderRows();

  const upcomingCard = h("div", { class: "card" },
    h("h2", { class: "section-title" }, "Upcoming events (next 30 days)"),
    upcoming && upcoming.length
      ? h("div", { class: "upcoming-list" }, ...upcoming.map(e =>
          h("div", { class: "upcoming-item" },
            h("div", null,
              h("span", { class: "upcoming-name" }, e.name),
              h("span", { class: "upcoming-event" }, `· ${e.event_type}`),
            ),
            h("span", { class: `days-pill ${pillClassFor(e.days_away)}` }, `${fmtDays(e.days_away)} · ${e.date}`),
          )
        ))
      : emptyState("inbox", "Nothing coming up", "No birthdays or anniversaries in the next 30 days"),
  );

  app.append(
    h("div", { class: "page-header" },
      h("h1", { class: "page-title" }, "Family Members"),
      h("button", {
        class: "btn btn-primary",
        onclick: () => showMemberForm(null, members),
      }, icon("plus"), "Add Member"),
    ),
    h("div", { class: "action-bar" },
      h("div", { class: "search-input" },
        h("span", { html: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS.search}</svg>` }),
        search,
      ),
      h("span", { class: "muted text-sm" }, `${members.length} ${members.length === 1 ? "member" : "members"}`),
    ),
    tableWrap,
    upcomingCard,
  );
};

function showMemberForm(m, members) {
  m = m || {};
  const fields = {};
  function field(name, label, props = {}) {
    const input = h("input", { name, value: m[name] != null ? m[name] : "", ...props });
    fields[name] = input;
    return h("div", { class: "field" }, h("label", null, label), input);
  }
  function textareaField(name, label, sub) {
    const input = h("textarea", { name }, m[name] || "");
    fields[name] = input;
    return h("div", { class: "field" },
      h("label", null, label),
      input,
      sub ? h("div", { class: "field-help" }, sub) : null,
    );
  }
  const marriedCheck = h("input", { type: "checkbox", checked: !!m.married });
  const pausedCheck = h("input", { type: "checkbox", checked: !!m.notifications_paused });
  const annSection = h("div", null,
    h("div", { class: "form-row" },
      field("spouse_name", "Spouse Name"),
      field("anniversary", "Anniversary (MM-DD)", { placeholder: "03-11" }),
    ),
    field("anniversary_year", "Anniversary Year (optional)", { type: "number" }),
  );
  if (!m.married) annSection.style.display = "none";
  marriedCheck.addEventListener("change", e => annSection.style.display = e.target.checked ? "" : "none");

  function relSelect(name, label) {
    const others = (members || []).filter(x => x.id !== m.id);
    const sel = h("select", { name },
      h("option", { value: "" }, "— none —"),
      ...others.map(x => h("option", { value: x.id, selected: m[name] === x.id }, x.name)),
    );
    fields[name] = sel;
    return h("div", { class: "field" }, h("label", null, label), sel);
  }

  const form = h("form", null,
    h("div", { class: "form-row" },
      field("name", "Name *", { required: true }),
      field("birthday", "Birthday (MM-DD) *", { required: true, placeholder: "01-28" }),
    ),
    h("div", { class: "form-row" },
      field("phone", "Phone", { placeholder: "(555) 123-4567" }),
      field("email", "Email", { type: "email", placeholder: "name@example.com" }),
    ),
    h("div", { class: "form-row" },
      field("whatsapp", "WhatsApp (only if different from phone)"),
      field("birth_year", "Birth Year (optional, enables {age})", { type: "number" }),
    ),
    h("label", { class: "check-label" }, marriedCheck, "Married"),
    annSection,
    textareaField("custom_birthday_message", "Custom Birthday Message", "Variables: {name} {age} {days} {day_of_week}"),
    textareaField("custom_anniversary_message", "Custom Anniversary Message", "Variables: {name} {spouse} {years_married} {days}"),
    h("label", { class: "check-label" }, pausedCheck, "Pause all notifications for this person"),
    h("h3", { class: "section-title", style: { marginTop: "1.25rem" } }, "Family relationships (for tree)"),
    h("div", { class: "form-row" },
      relSelect("mother_id", "Mother"),
      relSelect("father_id", "Father"),
    ),
    relSelect("spouse_id", "Spouse link"),
    h("div", { class: "field-help" }, "Spouse link connects people in the family tree — set on either person and it syncs both ways."),
  );

  const cancelBtn = h("button", { type: "button", class: "btn btn-ghost", onclick: closeModal }, "Cancel");
  const saveBtn = h("button", { type: "submit", class: "btn btn-primary" }, m.id ? "Update" : "Add Member");

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const data = {
      name: fields.name.value, birthday: fields.birthday.value,
      phone: fields.phone.value || null, email: fields.email.value || null,
      whatsapp: fields.whatsapp.value || null,
      birth_year: fields.birth_year.value ? parseInt(fields.birth_year.value) : null,
      married: marriedCheck.checked,
      spouse_name: fields.spouse_name.value || null,
      anniversary: fields.anniversary.value || null,
      anniversary_year: fields.anniversary_year.value ? parseInt(fields.anniversary_year.value) : null,
      custom_birthday_message: fields.custom_birthday_message.value || "",
      custom_anniversary_message: fields.custom_anniversary_message.value || "",
      notifications_paused: pausedCheck.checked,
      mother_id: fields.mother_id.value ? parseInt(fields.mother_id.value) : null,
      father_id: fields.father_id.value ? parseInt(fields.father_id.value) : null,
      spouse_id: fields.spouse_id.value ? parseInt(fields.spouse_id.value) : null,
    };
    await withBusy(saveBtn, async () => {
      const r = m.id ? await api("PUT", `/members/${m.id}`, data) : await api("POST", "/members", data);
      if (r) { toast(m.id ? "Updated" : "Added", "success"); closeModal(); navigate("members"); }
    });
  });

  openModal({ title: m.id ? `Edit ${m.name}` : "Add Member", body: form, actions: [cancelBtn, saveBtn] });
}

// ── Notifications ───────────────────────────────────────────────────────────
pages.notifications = async (app) => {
  const members = await api("GET", "/members");
  if (members === null) return;
  if (!members.length) {
    app.append(
      h("h1", { class: "page-title" }, "Send Notifications"),
      h("div", { class: "card" }, emptyState("users", "No members yet", "Add at least one family member first.")),
    );
    return;
  }

  const personSel = h("select", null,
    h("option", { value: "" }, "— select a person —"),
    ...members.map(m => h("option", { value: m.id }, m.name))
  );
  const eventSel = h("select", null, h("option", { value: "birthday" }, "Birthday"), h("option", { value: "anniversary" }, "Anniversary"));
  const triggerSel = h("select", null,
    h("option", { value: "same_day" }, "Same day · sends to the person"),
    h("option", { value: "1_day" }, "1-day advance · reminder to others"),
    h("option", { value: "7_day" }, "7-day advance · reminder to others"),
  );
  const previewBtn = h("button", { class: "btn btn-primary" }, icon("info"), "Preview");
  const sendBtn = h("button", { class: "btn btn-success" }, icon("bell"), "Send Now");
  const previewArea = h("div");

  function readPayload() {
    return {
      person_id: parseInt(personSel.value),
      event_type: eventSel.value,
      trigger_type: triggerSel.value,
    };
  }
  function buildEmailSubject(p) {
    const m = members.find(x => x.id === p.person_id) || {};
    if (p.event_type === "birthday") {
      return p.trigger_type === "same_day" ? `Happy Birthday, ${m.name}!` : `Reminder: ${m.name}'s birthday`;
    }
    const sp = m.spouse_name || "";
    return p.trigger_type === "same_day" ? `Happy Anniversary, ${m.name} & ${sp}!` : `Reminder: ${m.name} & ${sp} anniversary`;
  }

  previewBtn.addEventListener("click", async () => {
    const p = readPayload();
    if (!p.person_id) { toast("Select a person first", "warn"); return; }
    await withBusy(previewBtn, async () => {
      const r = await api("POST", "/notifications/preview", p);
      if (!r) return;
      previewArea.replaceChildren(
        h("div", { class: "preview-grid" },
          h("div", { class: "preview-card" },
            h("div", { class: "preview-label" }, icon("bell"), "SMS"),
            h("div", { class: "preview-body" }, r.sms),
          ),
          h("div", { class: "preview-card" },
            h("div", { class: "preview-label" }, icon("bell"), "WhatsApp"),
            h("div", { class: "preview-body" }, r.whatsapp),
          ),
          h("div", { class: "preview-card" },
            h("div", { class: "preview-label" }, icon("inbox"), "Email"),
            h("div", { class: "preview-subject" }, `Subject: ${buildEmailSubject(p)}`),
            h("div", { class: "preview-body" }, r.email),
          ),
        ),
      );
    });
  });

  sendBtn.addEventListener("click", async () => {
    const p = readPayload();
    if (!p.person_id) { toast("Select a person first", "warn"); return; }
    const m = members.find(x => x.id === p.person_id);
    if (!await confirmAsync(`Send ${p.event_type} (${p.trigger_type.replace("_", " ")}) for ${m.name} now?`, { confirmText: "Send" })) return;
    await withBusy(sendBtn, async () => {
      const r = await api("POST", "/notifications/send", p);
      if (r) toast("Dispatched — check Logs for delivery status", "success");
    });
  });

  app.append(
    h("h1", { class: "page-title" }, "Send Notifications"),
    h("div", { class: "card" },
      h("div", { class: "form-row" },
        h("div", { class: "field" }, h("label", null, "Person"), personSel),
        h("div", { class: "field" }, h("label", null, "Event"), eventSel),
        h("div", { class: "field" }, h("label", null, "Trigger"), triggerSel),
      ),
      h("div", { class: "flex gap-2" }, previewBtn, sendBtn),
      previewArea,
    ),
  );
};

// ── Logs ────────────────────────────────────────────────────────────────────
pages.logs = async (app) => {
  const channelSel = h("select", null, h("option", { value: "" }, "All channels"),
    h("option", { value: "sms" }, "SMS"), h("option", { value: "whatsapp" }, "WhatsApp"), h("option", { value: "email" }, "Email"));
  const statusSel = h("select", null, h("option", { value: "" }, "All statuses"),
    h("option", { value: "sent" }, "Sent"), h("option", { value: "failed" }, "Failed"));
  const eventSel = h("select", null, h("option", { value: "" }, "All events"),
    h("option", { value: "birthday" }, "Birthday"), h("option", { value: "anniversary" }, "Anniversary"));
  const fromInput = h("input", { type: "date", "aria-label": "From date" });
  const toInput = h("input", { type: "date", "aria-label": "To date" });
  const filterBtn = h("button", { class: "btn btn-primary btn-sm" }, "Apply filters");
  const exportBtn = h("button", { class: "btn btn-ghost" }, icon("download"), "Export CSV");
  const resetBtn = h("button", { class: "btn btn-danger" }, icon("trash"), "Reset");
  const countLabel = h("span", { class: "muted text-sm" });

  const out = h("div");

  function currentParams() {
    const params = new URLSearchParams();
    if (channelSel.value) params.set("channel", channelSel.value);
    if (statusSel.value) params.set("status", statusSel.value);
    if (eventSel.value) params.set("event_type", eventSel.value);
    if (fromInput.value) params.set("date_from", fromInput.value);
    if (toInput.value) params.set("date_to", toInput.value);
    return params;
  }

  exportBtn.addEventListener("click", () => {
    const params = currentParams();
    const qs = params.toString();
    window.location.href = `/api/logs/export.csv${qs ? "?" + qs : ""}`;
  });

  resetBtn.addEventListener("click", async () => {
    const params = currentParams();
    const filtered = params.toString() !== "";
    const msg = filtered
      ? "Delete all log rows matching the current filters? This cannot be undone."
      : "Delete ALL notification log entries? Notification state (the per-year duplicate guard) is preserved. This cannot be undone — export first if you want a backup.";
    if (!await confirmAsync(msg, { confirmText: "Delete logs", danger: true })) return;
    await withBusy(resetBtn, async () => {
      const qs = params.toString();
      const r = await fetch(`/api/logs${qs ? "?" + qs : ""}`, { method: "DELETE" });
      if (!r.ok) { toast(`${r.status}: ${await r.text()}`, "error"); return; }
      const j = await r.json();
      toast(`Deleted ${j.deleted} log ${j.deleted === 1 ? "entry" : "entries"}`, "success");
      load();
    });
  });

  async function load() {
    const params = currentParams();
    const logs = await api("GET", `/logs?${params}`);
    if (!logs) return;
    countLabel.textContent = logs.length === 0
      ? "0 entries"
      : logs.length >= 500 ? "Showing latest 500 entries" : `${logs.length} ${logs.length === 1 ? "entry" : "entries"}`;
    if (!logs.length) {
      out.replaceChildren(h("div", { class: "card" }, emptyState("inbox", "No logs match these filters", "Try clearing filters or trigger a notification.")));
      return;
    }
    const rows = logs.map(l => {
      const errCell = l.error_message
        ? h("div", { class: "log-error", title: "Click to expand", onclick: e => e.currentTarget.classList.toggle("expanded") }, l.error_message)
        : "";
      const retryBtn = l.status === "failed"
        ? h("button", {
            class: "btn btn-sm btn-primary",
            onclick: async (e) => { await withBusy(e.currentTarget, async () => {
              const r = await api("POST", `/logs/${l.id}/retry`);
              if (r) { toast("Retry dispatched", "success"); load(); }
            }); },
          }, icon("refresh"), "Retry")
        : "";
      return h("tr", null,
        h("td", null, h("strong", null, l.person_name)),
        h("td", { class: "muted text-sm" }, `${l.event_type} · ${l.trigger_type.replace("_", " ")}`),
        h("td", null, l.channel),
        h("td", null,
          h("span", { class: `badge badge-${l.status}` }, l.status),
          errCell,
        ),
        h("td", { class: "muted text-sm mono" }, l.sent_at),
        h("td", null, retryBtn),
      );
    });
    out.replaceChildren(h("div", { class: "table-wrap" },
      h("table", null,
        h("thead", null, h("tr", null,
          h("th", null, "Person"), h("th", null, "Event"), h("th", null, "Channel"),
          h("th", null, "Status"), h("th", null, "Sent At"), h("th", null, ""),
        )),
        h("tbody", null, ...rows),
      ),
    ));
  }
  filterBtn.addEventListener("click", load);

  app.append(
    h("div", { class: "page-header" },
      h("h1", { class: "page-title" }, "Notification Logs"),
      h("div", { class: "flex gap-2" }, exportBtn, resetBtn),
    ),
    h("div", { class: "filter-bar" },
      h("div", { class: "field" }, h("label", null, "Channel"), channelSel),
      h("div", { class: "field" }, h("label", null, "Status"), statusSel),
      h("div", { class: "field" }, h("label", null, "Event"), eventSel),
      h("div", { class: "field" }, h("label", null, "From"), fromInput),
      h("div", { class: "field" }, h("label", null, "To"), toInput),
      filterBtn,
    ),
    h("div", { class: "action-bar", style: { marginBottom: "8px", marginTop: "-8px" } }, countLabel),
    out,
  );
  load();
};

// ── Schedule ────────────────────────────────────────────────────────────────
pages.schedule = async (app) => {
  const s = await api("GET", "/settings");
  if (!s) return;

  const sw = h("input", { type: "number", min: 0, max: 365, value: s.advance_days_week });
  const sd = h("input", { type: "number", min: 0, max: 365, value: s.advance_days_day });
  const sj1 = h("input", { type: "time", value: s.job1_time });
  const sj2 = h("input", { type: "time", value: s.job2_time });
  const sc = h("input", { type: "number", min: 0, max: 24, value: s.catch_up_hours });
  const ssms = h("input", { type: "checkbox", checked: s.sms_enabled === "true" });
  const swa = h("input", { type: "checkbox", checked: s.whatsapp_enabled === "true" });
  const semail = h("input", { type: "checkbox", checked: s.email_enabled === "true" });
  const saveBtn = h("button", { class: "btn btn-primary" }, icon("check"), "Save");

  saveBtn.addEventListener("click", async () => {
    await withBusy(saveBtn, async () => {
      const r = await api("PUT", "/settings", {
        advance_days_week: String(sw.value),
        advance_days_day: String(sd.value),
        job1_time: sj1.value,
        job2_time: sj2.value,
        catch_up_hours: String(sc.value),
        sms_enabled: ssms.checked ? "true" : "false",
        whatsapp_enabled: swa.checked ? "true" : "false",
        email_enabled: semail.checked ? "true" : "false",
      });
      if (r) toast("Schedule applied — changes are live", "success");
    });
  });

  app.append(
    h("h1", { class: "page-title" }, "Schedule & Channels"),
    h("div", { class: "card" },
      h("h2", { class: "section-title" }, "Advance reminder windows"),
      h("p", { class: "muted text-sm", style: { marginBottom: "12px" } },
        "How many days before an event to send reminder messages to the rest of the family."),
      h("div", { class: "form-row" },
        h("div", { class: "field" }, h("label", null, "Week-ahead (days before)"), sw),
        h("div", { class: "field" }, h("label", null, "Day-before (days before)"), sd),
      ),
    ),
    h("div", { class: "card" },
      h("h2", { class: "section-title" }, "Job times"),
      h("div", { class: "form-row" },
        h("div", { class: "field" }, h("label", null, "Advance reminders run at"), sj1),
        h("div", { class: "field" }, h("label", null, "Day-of wishes run at"), sj2),
      ),
      h("div", { class: "field", style: { maxWidth: "240px" } },
        h("label", null, "Reboot catch-up window (hours)"), sc,
        h("div", { class: "field-help" }, "If the Pi was offline past the day-of run time, fire once on startup if within this window."),
      ),
    ),
    h("div", { class: "card" },
      h("h2", { class: "section-title" }, "Channels"),
      h("label", { class: "check-label" }, ssms, "Enable SMS"),
      h("br"),
      h("label", { class: "check-label" }, swa, "Enable WhatsApp"),
      h("br"),
      h("label", { class: "check-label" }, semail, "Enable Email"),
    ),
    saveBtn,
  );
};

// ── Settings ────────────────────────────────────────────────────────────────
pages.settings = async (app) => {
  const c = await api("GET", "/credentials");
  if (!c) return;

  function credField(name, label, value, masked) {
    const input = h("input", {
      class: "cinp", id: `ci_${name}`, name,
      type: masked ? "password" : "text",
      value: value != null ? value : "",
    });
    let toggle = null;
    if (masked) {
      toggle = h("button", {
        type: "button", class: "cred-toggle",
        onclick: () => {
          input.type = input.type === "password" ? "text" : "password";
          toggle.textContent = input.type === "password" ? "Show" : "Hide";
        },
      }, "Show");
    }
    return h("div", { class: "cred-wrap" },
      h("label", null, label),
      h("div", { style: { position: "relative" } }, input, toggle),
    );
  }
  const inputs = {};
  function reg(name, label, masked) {
    const wrap = credField(name, label, c[name], masked);
    inputs[name] = $("input", wrap);
    return wrap;
  }

  const saveBtn = h("button", { class: "btn btn-primary" }, icon("check"), "Save credentials");
  const exportBtn = h("button", { class: "btn btn-ghost" }, icon("download"), "Export JSON");
  const importInput = h("input", { type: "file", accept: ".json", style: { display: "none" } });
  const importLabel = h("label", { class: "btn btn-ghost", style: { cursor: "pointer" } }, icon("upload"), "Import JSON", importInput);

  saveBtn.addEventListener("click", async () => {
    await withBusy(saveBtn, async () => {
      const data = {};
      for (const [k, el] of Object.entries(inputs)) data[k] = el.value || null;
      if (data.smtp_port) data.smtp_port = parseInt(data.smtp_port);
      const r = await api("PUT", "/credentials", data);
      if (r) toast("Credentials saved — config reloaded", "success");
    });
  });
  exportBtn.addEventListener("click", () => { window.location.href = "/api/export"; });
  importInput.addEventListener("change", async e => {
    const file = e.target.files[0]; if (!file) return;
    try {
      const json = JSON.parse(await file.text());
      const r = await api("POST", "/import", json);
      if (r) toast(`Import complete — ${r.imported} added, ${r.skipped} skipped`, "success");
    } catch (err) {
      toast(`Bad JSON: ${err.message}`, "error");
    }
    e.target.value = "";
  });

  app.append(
    h("h1", { class: "page-title" }, "Settings"),
    h("div", { class: "card" },
      h("h2", { class: "section-title" }, "Twilio (SMS & WhatsApp)"),
      reg("twilio_account_sid", "Account SID", true),
      reg("twilio_auth_token", "Auth Token", true),
      h("div", { class: "form-row" },
        h("div", null, reg("twilio_from_number", "SMS From Number", false)),
        h("div", null, reg("twilio_whatsapp_number", "WhatsApp Number", false)),
      ),
    ),
    h("div", { class: "card" },
      h("h2", { class: "section-title" }, "SMTP (Email)"),
      reg("smtp_host", "Host", false),
      h("div", { class: "form-row" },
        h("div", null, reg("smtp_port", "Port", false)),
        h("div", null, reg("smtp_username", "Username", false)),
      ),
      reg("smtp_password", "Password", true),
      reg("smtp_from_address", "From Address", false),
    ),
    saveBtn,
    h("div", { class: "card mt-5" },
      h("h2", { class: "section-title" }, "Data management"),
      h("div", { class: "flex gap-2", style: { flexWrap: "wrap" } }, exportBtn, importLabel),
      h("p", { class: "muted text-sm mt-4" },
        "Import accepts both the export format and the legacy dict-of-dicts format. Members are deduped by name."),
    ),
  );
};

// ── Family Tree ─────────────────────────────────────────────────────────────
// Powered by family-chart (MIT, github.com/donatso/family-chart) + d3.
// The chart is interactive: click a card to re-center on that person, drag to
// pan, scroll to zoom. Library files are vendored under /static/vendor/.

function buildFamilyChartData(nodes) {
  const childrenByParent = {};
  const spousesByPerson = {};
  for (const n of nodes) {
    if (n.mother_id) (childrenByParent[n.mother_id] ||= []).push(String(n.id));
    if (n.father_id) (childrenByParent[n.father_id] ||= []).push(String(n.id));
    if (n.spouse_id) (spousesByPerson[n.id] ||= []).push(String(n.spouse_id));
  }
  // Infer gender from how the person is referenced — mom-of-someone -> F, dad -> M
  const genderOf = {};
  for (const n of nodes) {
    if (n.mother_id && !genderOf[n.mother_id]) genderOf[n.mother_id] = "F";
    if (n.father_id && !genderOf[n.father_id]) genderOf[n.father_id] = "M";
  }
  return nodes.map(n => ({
    id: String(n.id),
    rels: {
      mother: n.mother_id ? String(n.mother_id) : undefined,
      father: n.father_id ? String(n.father_id) : undefined,
      spouses: spousesByPerson[n.id] || [],
      children: childrenByParent[n.id] || [],
    },
    data: {
      first_name: n.name,
      birthday: n.birthday || "",
      gender: genderOf[n.id] || "",
    },
  }));
}

pages.tree = async (app) => {
  const data = await api("GET", "/members/tree");
  if (data === null) return;
  const { nodes, edges } = data;

  const header = h("div", { class: "page-header" },
    h("h1", { class: "page-title" }, "Family Tree"),
    h("span", { class: "muted text-sm" },
      `${nodes.length} ${nodes.length === 1 ? "member" : "members"} · ${edges.length} link${edges.length === 1 ? "" : "s"}`),
  );

  if (!nodes.length) {
    app.replaceChildren(header,
      h("div", { class: "card" }, emptyState("users", "No family members yet",
        "Add members and link their parent and spouse relationships to see the family tree.")),
    );
    return;
  }
  if (!edges.length) {
    app.replaceChildren(header,
      h("div", { class: "card" }, emptyState("users", "No relationships linked yet",
        "Edit a member to set their mother, father, or spouse — links will appear here.")),
    );
    return;
  }
  if (typeof f3 === "undefined" || typeof d3 === "undefined") {
    app.replaceChildren(header,
      h("div", { class: "card" }, emptyState("alert", "Visualization library failed to load",
        "Refresh the page. If it persists, check that /vendor/d3.min.js and /vendor/family-chart.js are reachable.")),
    );
    return;
  }

  // Compute connection count so the most-connected person becomes the default
  // focus — that gives the largest visible tree out of the box. f3 uses
  // data[0].id as the main person on first render.
  const connections = {};
  for (const n of nodes) {
    connections[n.id] = (n.mother_id ? 1 : 0) + (n.father_id ? 1 : 0) + (n.spouse_id ? 1 : 0);
  }
  for (const n of nodes) {
    if (n.mother_id) connections[n.mother_id] = (connections[n.mother_id] || 0) + 1;
    if (n.father_id) connections[n.father_id] = (connections[n.father_id] || 0) + 1;
  }
  const sortedNodes = [...nodes].sort((a, b) => (connections[b.id] || 0) - (connections[a.id] || 0));
  const f3Data = buildFamilyChartData(sortedNodes);

  // "Focus on" picker — switches main person so users can jump between
  // disjoint family clusters (the chart only shows one connected component).
  const focusSelect = h("select", { class: "tree-focus-select", "aria-label": "Focus tree on" },
    ...[...nodes].sort((a, b) => a.name.localeCompare(b.name))
      .map(n => h("option", { value: String(n.id) }, n.name)),
  );
  focusSelect.value = String(sortedNodes[0].id);

  const chartHost = h("div", { id: "FamilyChart", class: "f3 family-chart-host" });
  const wrapper = h("div", { class: "tree-page-bleed" }, chartHost);

  app.replaceChildren(
    header,
    h("div", { class: "tree-toolbar" },
      h("label", { class: "tree-focus-label" }, "Focus on:", focusSelect),
      h("span", { class: "muted text-sm" }, "Click a card to re-center · scroll to zoom · drag to pan"),
    ),
    wrapper,
  );

  // Defer to next frame so the host has dimensions before f3 measures it
  let chartRef = null;
  requestAnimationFrame(() => {
    try {
      const chart = f3.createChart("#FamilyChart", f3Data)
        .setTransitionTime(700)
        .setCardXSpacing(260)
        .setCardYSpacing(110)
        .setOrientationHorizontal()
        .setSingleParentEmptyCard(false);

      chart.setCard(f3.CardHtml)
        .setCardDisplay([["first_name"], ["birthday"]])
        .setCardDim({ w: 200, h: 70, text_x: 75, text_y: 15, img_w: 60, img_h: 60, img_x: 5, img_y: 5 })
        .setMiniTree(true)
        .setStyle("imageRect")
        .setOnHoverPathToMain();

      chart.updateTree({ initial: true, tree_position: "fit" });
      chartRef = chart;
    } catch (err) {
      console.error("family-chart failed:", err);
      toast("Could not render tree — see console", "error");
    }
  });

  focusSelect.addEventListener("change", () => {
    if (!chartRef) return;
    chartRef.store.updateMainId(focusSelect.value);
    chartRef.updateTree({ tree_position: "fit" });
  });

};

// ── Init ────────────────────────────────────────────────────────────────────
function buildNav() {
  const ul = $("#nav-list");
  ul.replaceChildren(...NAV.map(item => h("li", null,
    h("a", {
      href: "#", "data-page": item.id,
      onclick: e => { e.preventDefault(); navigate(item.id); },
    }, icon(item.icon), item.label),
  )));
}
buildNav();

// Theme init — restore saved or follow OS
(function () {
  const saved = readTheme();
  if (saved) document.documentElement.setAttribute("data-theme", saved);
  paintThemeToggle();
  $("#theme-toggle").addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme");
    setTheme(cur === "dark" ? "light" : "dark");
  });
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", paintThemeToggle);
})();

// Mobile drawer
$("#menu-btn").addEventListener("click", openSidebar);
$("#sidebar-scrim").addEventListener("click", closeSidebar);

navigate("members");
