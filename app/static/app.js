// ── Router ───────────────────────────────────────────────────────────────────
const pages = {};
function registerPage(name, fn) { pages[name] = fn; }

document.querySelectorAll(".sidebar a").forEach(a => {
  a.addEventListener("click", e => {
    e.preventDefault();
    document.querySelectorAll(".sidebar a").forEach(x => x.classList.remove("active"));
    a.classList.add("active");
    navigate(a.dataset.page);
  });
});

function navigate(page) {
  document.getElementById("app").innerHTML = "";
  if (pages[page]) pages[page]();
}

// ── API helpers ───────────────────────────────────────────────────────────────
async function api(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const r = await fetch("/api" + path, opts);
  if (!r.ok) { alert("Error " + r.status + ": " + await r.text()); return null; }
  if (r.status === 204) return null;
  return r.json();
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function showModal(html) {
  document.getElementById("modal-box").innerHTML = html;
  document.getElementById("modal-overlay").classList.remove("hidden");
}
function closeModal() { document.getElementById("modal-overlay").classList.add("hidden"); }
document.getElementById("modal-overlay").addEventListener("click", e => {
  if (e.target.id === "modal-overlay") closeModal();
});

// ── Channel badges ────────────────────────────────────────────────────────────
function chBadges(m) {
  return `<span class="ch ${m.phone ? "ch-on" : "ch-off"}">SMS</span>`
       + `<span class="ch ${(m.whatsapp || m.phone) ? "ch-on" : "ch-off"}">WA</span>`
       + `<span class="ch ${m.email ? "ch-on" : "ch-off"}">Email</span>`;
}

// ── Members page ──────────────────────────────────────────────────────────────
registerPage("members", async () => {
  const [members, upcoming] = await Promise.all([api("GET", "/members"), api("GET", "/members/upcoming")]);
  if (!members) return;
  const app = document.getElementById("app");
  app.innerHTML = `
    <div class="action-bar"><h2>Family Members</h2><button class="btn btn-primary" id="add-btn">+ Add Member</button></div>
    <table>
      <thead><tr><th>Name</th><th>Birthday</th><th>Anniversary</th><th>Channels</th><th>Status</th><th>Actions</th></tr></thead>
      <tbody>${members.map(m => `<tr>
        <td><strong>${m.name}</strong></td>
        <td>${m.birthday || "—"}</td>
        <td>${m.married && m.anniversary ? m.anniversary : "—"}</td>
        <td>${chBadges(m)}</td>
        <td>${m.notifications_paused ? '<span class="badge badge-paused">Paused</span>' : ""}</td>
        <td style="display:flex;gap:6px">
          <button class="btn btn-sm btn-primary edit-btn" data-id="${m.id}">Edit</button>
          <button class="btn btn-sm btn-danger del-btn" data-id="${m.id}">Delete</button>
          <button class="btn btn-sm ${m.notifications_paused ? "btn-success" : ""}" style="${m.notifications_paused ? "" : "background:#f59e0b;color:#fff"}" data-id="${m.id}" data-paused="${m.notifications_paused}" class="pause-btn">
            ${m.notifications_paused ? "Resume" : "Pause"}
          </button>
        </td>
      </tr>`).join("")}</tbody>
    </table>
    <div class="card" style="margin-top:24px">
      <h3>Upcoming Events (next 30 days)</h3>
      ${upcoming && upcoming.length ? upcoming.map(e => `
        <div class="upcoming-item">
          <span><strong>${e.name}</strong> — ${e.event_type}</span>
          <span class="days-pill ${e.days_away === 0 ? "today" : ""}">
            ${e.days_away === 0 ? "TODAY" : `in ${e.days_away}d`} · ${e.date}
          </span>
        </div>`).join("") : '<p class="empty-msg">No upcoming events in the next 30 days</p>'}
    </div>`;

  document.getElementById("add-btn").onclick = () => showMemberForm(null, members);
  document.querySelectorAll(".edit-btn").forEach(b => b.onclick = () => showMemberForm(members.find(m => m.id == b.dataset.id), members));
  document.querySelectorAll(".del-btn").forEach(b => b.onclick = async () => {
    if (confirm("Delete this member?")) { await api("DELETE", `/members/${b.dataset.id}`); navigate("members"); }
  });
  document.querySelectorAll("[data-paused]").forEach(b => b.onclick = async () => {
    const paused = b.dataset.paused == "1" || b.dataset.paused === "true";
    await api("PUT", `/members/${b.dataset.id}/pause`, { paused: !paused });
    navigate("members");
  });
});

function showMemberForm(m, _members) {
  m = m || {};
  showModal(`<h3>${m.id ? "Edit" : "Add"} Member</h3>
  <form id="mf">
    <div class="form-row">
      <div><label>Name *</label><input name="name" value="${esc(m.name)}" required></div>
      <div><label>Birthday (MM-DD) *</label><input name="birthday" value="${esc(m.birthday)}" placeholder="01-28" required></div>
    </div>
    <div class="form-row">
      <div><label>Phone</label><input name="phone" value="${esc(m.phone)}"></div>
      <div><label>Email</label><input type="email" name="email" value="${esc(m.email)}"></div>
    </div>
    <div class="form-row">
      <div><label>WhatsApp (if different from phone)</label><input name="whatsapp" value="${esc(m.whatsapp)}"></div>
      <div><label>Birth Year (for age)</label><input type="number" name="birth_year" value="${m.birth_year || ""}"></div>
    </div>
    <label class="check-label"><input type="checkbox" name="married" ${m.married ? "checked" : ""}> Married</label>
    <div id="mf-married" style="${m.married ? "" : "display:none"}">
      <div class="form-row">
        <div><label>Spouse Name</label><input name="spouse_name" value="${esc(m.spouse_name)}"></div>
        <div><label>Anniversary (MM-DD)</label><input name="anniversary" value="${esc(m.anniversary)}"></div>
      </div>
      <div><label>Anniversary Year</label><input type="number" name="anniversary_year" value="${m.anniversary_year || ""}"></div>
    </div>
    <label>Custom Birthday Message <small style="color:#9ca3af">(supports {name}, {age}, {days})</small></label>
    <textarea name="custom_birthday_message">${esc(m.custom_birthday_message)}</textarea>
    <label>Custom Anniversary Message</label>
    <textarea name="custom_anniversary_message">${esc(m.custom_anniversary_message)}</textarea>
    <label class="check-label"><input type="checkbox" name="notifications_paused" ${m.notifications_paused ? "checked" : ""}> Pause notifications</label>
    <div style="display:flex;gap:10px;margin-top:8px">
      <button type="submit" class="btn btn-primary">${m.id ? "Update" : "Add"}</button>
      <button type="button" class="btn" onclick="closeModal()">Cancel</button>
    </div>
  </form>`);

  document.querySelector('[name="married"]').onchange = e => {
    document.getElementById("mf-married").style.display = e.target.checked ? "" : "none";
  };
  document.getElementById("mf").onsubmit = async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = { name: fd.get("name"), birthday: fd.get("birthday"), phone: fd.get("phone") || null,
      email: fd.get("email") || null, whatsapp: fd.get("whatsapp") || null,
      birth_year: fd.get("birth_year") ? parseInt(fd.get("birth_year")) : null,
      married: !!fd.get("married"), spouse_name: fd.get("spouse_name") || null,
      anniversary: fd.get("anniversary") || null,
      anniversary_year: fd.get("anniversary_year") ? parseInt(fd.get("anniversary_year")) : null,
      custom_birthday_message: fd.get("custom_birthday_message") || "",
      custom_anniversary_message: fd.get("custom_anniversary_message") || "",
      notifications_paused: !!fd.get("notifications_paused") };
    const result = m.id ? await api("PUT", `/members/${m.id}`, data) : await api("POST", "/members", data);
    if (result) { closeModal(); navigate("members"); }
  };
}

// ── Notifications page ────────────────────────────────────────────────────────
registerPage("notifications", async () => {
  const members = await api("GET", "/members");
  if (!members || !members.length) {
    document.getElementById("app").innerHTML = '<h2>Notifications</h2><p class="empty-msg">No family members yet. Add some first.</p>';
    return;
  }
  document.getElementById("app").innerHTML = `
    <h2>Send Notifications</h2>
    <div class="card">
      <div class="form-row">
        <div><label>Person</label><select id="np"><option value="">— select —</option>${members.map(m => `<option value="${m.id}">${m.name}</option>`).join("")}</select></div>
        <div><label>Event</label><select id="ne"><option value="birthday">Birthday</option><option value="anniversary">Anniversary</option></select></div>
        <div><label>Trigger</label><select id="nt"><option value="same_day">Same Day (personal wish)</option><option value="1_day">1-Day Advance (reminder)</option><option value="7_day">7-Day Advance (reminder)</option></select></div>
      </div>
      <div style="display:flex;gap:10px;margin-top:4px">
        <button class="btn btn-primary" id="prev-btn">Preview</button>
        <button class="btn btn-success" id="send-btn">Send Now</button>
      </div>
      <div id="prev-out"></div>
    </div>`;

  function payload() {
    return { person_id: parseInt(document.getElementById("np").value),
             event_type: document.getElementById("ne").value,
             trigger_type: document.getElementById("nt").value };
  }
  document.getElementById("prev-btn").onclick = async () => {
    const p = payload(); if (!p.person_id) { alert("Select a person"); return; }
    const r = await api("POST", "/notifications/preview", p);
    if (r) document.getElementById("prev-out").innerHTML =
      `<strong>SMS / WhatsApp:</strong><div class="preview-box">${r.sms}</div><strong>Email:</strong><div class="preview-box">${r.email}</div>`;
  };
  document.getElementById("send-btn").onclick = async () => {
    const p = payload(); if (!p.person_id) { alert("Select a person"); return; }
    if (confirm("Send this notification now?")) {
      const r = await api("POST", "/notifications/send", p);
      if (r) alert("Dispatched! Check Logs for delivery status.");
    }
  };
});

// ── Logs page ─────────────────────────────────────────────────────────────────
registerPage("logs", async () => {
  document.getElementById("app").innerHTML = `
    <h2>Notification Logs</h2>
    <div class="filter-bar">
      <select id="fc"><option value="">All channels</option><option>sms</option><option>whatsapp</option><option>email</option></select>
      <select id="fs"><option value="">All statuses</option><option value="sent">Sent</option><option value="failed">Failed</option></select>
      <select id="fe"><option value="">All events</option><option value="birthday">Birthday</option><option value="anniversary">Anniversary</option></select>
      <button class="btn btn-primary btn-sm" id="fa">Filter</button>
    </div>
    <div id="logs-out"></div>`;

  async function load() {
    const params = new URLSearchParams();
    ["fc","fs","fe"].forEach((id, i) => { const v = document.getElementById(id).value; if (v) params.set(["channel","status","event_type"][i], v); });
    const logs = await api("GET", `/logs?${params}`);
    if (!logs) return;
    document.getElementById("logs-out").innerHTML = logs.length ? `<table>
      <thead><tr><th>Person</th><th>Event</th><th>Trigger</th><th>Channel</th><th>Status</th><th>Sent At</th><th></th></tr></thead>
      <tbody>${logs.map(l => `<tr>
        <td>${l.person_name}</td><td>${l.event_type}</td><td>${l.trigger_type}</td><td>${l.channel}</td>
        <td><span class="badge badge-${l.status}">${l.status}${l.error_message ? " · " + l.error_message : ""}</span></td>
        <td style="font-size:.78rem;color:#9ca3af">${l.sent_at}</td>
        <td>${l.status === "failed" ? `<button class="btn btn-sm btn-primary retry-btn" data-id="${l.id}">Retry</button>` : ""}</td>
      </tr>`).join("")}</tbody></table>`
    : '<p class="empty-msg">No logs found.</p>';
    document.querySelectorAll(".retry-btn").forEach(b => b.onclick = async () => { await api("POST", `/logs/${b.dataset.id}/retry`); load(); });
  }
  document.getElementById("fa").onclick = load;
  load();
});

// ── Schedule page ─────────────────────────────────────────────────────────────
registerPage("schedule", async () => {
  const s = await api("GET", "/settings");
  if (!s) return;
  document.getElementById("app").innerHTML = `
    <h2>Schedule</h2>
    <div class="card"><h3>Advance Reminder Windows</h3>
      <div class="form-row">
        <div><label>Week-ahead reminder (days before)</label><input type="number" id="sw" value="${s.advance_days_week}"></div>
        <div><label>Day-before reminder (days before)</label><input type="number" id="sd" value="${s.advance_days_day}"></div>
      </div></div>
    <div class="card"><h3>Job Times</h3>
      <div class="form-row">
        <div><label>Advance reminders run at</label><input type="time" id="sj1" value="${s.job1_time}"></div>
        <div><label>Day-of wishes run at</label><input type="time" id="sj2" value="${s.job2_time}"></div>
      </div>
      <div style="max-width:200px"><label>Catch-up window (hours)</label><input type="number" id="sc" value="${s.catch_up_hours}"></div>
    </div>
    <div class="card"><h3>Channels</h3>
      <label class="check-label"><input type="checkbox" id="ssms" ${s.sms_enabled==="true"?"checked":""}> Enable SMS</label>
      <label class="check-label"><input type="checkbox" id="swa" ${s.whatsapp_enabled==="true"?"checked":""}> Enable WhatsApp</label>
      <label class="check-label"><input type="checkbox" id="semail" ${s.email_enabled==="true"?"checked":""}> Enable Email</label>
    </div>
    <button class="btn btn-primary" id="save-sched">Save Schedule</button>`;

  document.getElementById("save-sched").onclick = async () => {
    const r = await api("PUT", "/settings", {
      advance_days_week: document.getElementById("sw").value,
      advance_days_day: document.getElementById("sd").value,
      job1_time: document.getElementById("sj1").value,
      job2_time: document.getElementById("sj2").value,
      catch_up_hours: document.getElementById("sc").value,
      sms_enabled: document.getElementById("ssms").checked ? "true" : "false",
      whatsapp_enabled: document.getElementById("swa").checked ? "true" : "false",
      email_enabled: document.getElementById("semail").checked ? "true" : "false",
    });
    if (r) alert("Schedule saved! Restart the app for job time changes to take effect.");
  };
});

// ── Settings page ─────────────────────────────────────────────────────────────
registerPage("settings", async () => {
  const c = await api("GET", "/credentials");
  if (!c) return;
  document.getElementById("app").innerHTML = `
    <h2>Settings</h2>
    <div class="card"><h3>Twilio — SMS &amp; WhatsApp</h3>
      ${cf("twilio_account_sid","Account SID",c.twilio_account_sid,true)}
      ${cf("twilio_auth_token","Auth Token",c.twilio_auth_token,true)}
      ${cf("twilio_from_number","SMS From Number",c.twilio_from_number,false)}
      ${cf("twilio_whatsapp_number","WhatsApp Number",c.twilio_whatsapp_number,false)}
    </div>
    <div class="card"><h3>Email — SMTP</h3>
      ${cf("smtp_host","SMTP Host",c.smtp_host,false)}
      <div class="form-row"><div>${cf("smtp_port","Port",String(c.smtp_port),false)}</div><div>${cf("smtp_username","Username",c.smtp_username,false)}</div></div>
      ${cf("smtp_password","Password",c.smtp_password,true)}
      ${cf("smtp_from_address","From Address",c.smtp_from_address,false)}
    </div>
    <button class="btn btn-primary" id="save-creds" style="margin-bottom:24px">Save Credentials</button>
    <div class="card"><h3>Data Management</h3>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
        <button class="btn btn-primary" id="exp-btn">Export JSON</button>
        <label class="btn" style="background:#6b7280;color:#fff;cursor:pointer">
          Import JSON <input type="file" id="imp-file" accept=".json" style="display:none">
        </label>
      </div>
    </div>`;

  document.querySelectorAll(".ctog").forEach(btn => {
    btn.onclick = () => {
      const inp = document.getElementById(btn.dataset.for);
      inp.type = inp.type === "password" ? "text" : "password";
      btn.textContent = inp.type === "password" ? "Show" : "Hide";
    };
  });
  document.getElementById("save-creds").onclick = async () => {
    const data = {};
    document.querySelectorAll(".cinp").forEach(inp => { data[inp.name] = inp.value || null; });
    if (data.smtp_port) data.smtp_port = parseInt(data.smtp_port);
    const r = await api("PUT", "/credentials", data);
    if (r) alert("Credentials saved and config reloaded!");
  };
  document.getElementById("exp-btn").onclick = () => { window.location.href = "/api/export"; };
  document.getElementById("imp-file").onchange = async e => {
    const file = e.target.files[0]; if (!file) return;
    const json = JSON.parse(await file.text());
    const r = await api("POST", "/import", json);
    if (r) alert(`Import complete: ${r.imported} added, ${r.skipped} skipped.`);
    e.target.value = "";
  };
});

function cf(name, label, value, masked) {
  const id = "ci_" + name;
  return `<label>${label}</label><div class="cred-wrap">
    <input class="cinp" id="${id}" name="${name}" type="${masked ? "password" : "text"}" value="${esc(value || "")}">
    ${masked ? `<button class="cred-toggle ctog" data-for="${id}">Show</button>` : ""}
  </div>`;
}

function esc(s) {
  if (!s) return "";
  return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

// ── Init ──────────────────────────────────────────────────────────────────────
navigate("members");
