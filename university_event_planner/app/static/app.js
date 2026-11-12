document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initChat();
  initBenchmark();
  loadVenues();
  loadPolicyDocuments();
});

// ----------------------------------------------------
// Tab Navigation
// ----------------------------------------------------
function initTabs() {
  const tabBtns = document.querySelectorAll('.nav-tab-btn');
  const tabPanes = document.querySelectorAll('.tab-pane');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      tabPanes.forEach(p => p.classList.remove('active'));

      btn.classList.add('active');
      const targetPane = document.getElementById(btn.dataset.tab);
      if (targetPane) targetPane.classList.add('active');
    });
  });
}

// ----------------------------------------------------
// Chat & Conversational Assistant
// ----------------------------------------------------
function initChat() {
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');

  // Quick chips
  document.querySelectorAll('.chat-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const q = chip.dataset.query;
      input.value = q;
      sendMessage(q);
    });
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (query) {
      sendMessage(query);
      input.value = '';
    }
  });

  // Shift+Enter newline, Enter submits
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      form.dispatchEvent(new Event('submit'));
    }
  });
}

async function sendMessage(text) {
  const container = document.getElementById('chat-messages');

  // 1. Append User Message
  const userMsgEl = document.createElement('div');
  userMsgEl.className = 'chat-msg user';
  userMsgEl.innerHTML = `
    <div class="msg-avatar">👤</div>
    <div class="msg-content">
      <div class="msg-sender">You</div>
      <div class="msg-body">${escapeHtml(text)}</div>
    </div>
  `;
  container.appendChild(userMsgEl);
  container.scrollTop = container.scrollHeight;

  // 2. Typing Indicator
  const typingEl = document.createElement('div');
  typingEl.className = 'chat-msg assistant';
  typingEl.id = 'typing-indicator';
  typingEl.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-content">
      <div class="msg-sender">Orchestrator Agent</div>
      <div class="msg-body">
        <span class="loading-spinner" style="font-size: 0.85rem; color: var(--gray-600);">
          Analyzing request, evaluating campus rules & dynamically orchestrating sub-agents...
        </span>
      </div>
    </div>
  `;
  container.appendChild(typingEl);
  container.scrollTop = container.scrollHeight;

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Request failed');
    }

    const data = await res.json();
    typingEl.remove();

    renderAssistantResponse(data);
  } catch (err) {
    typingEl.remove();
    const errEl = document.createElement('div');
    errEl.className = 'chat-msg assistant';
    errEl.innerHTML = `
      <div class="msg-avatar">⚠️</div>
      <div class="msg-content">
        <div class="msg-sender">Orchestrator Agent</div>
        <div class="msg-body" style="color: var(--danger);">
          Error processing request: ${escapeHtml(err.message)}
        </div>
      </div>
    `;
    container.appendChild(errEl);
    container.scrollTop = container.scrollHeight;
  }
}

function renderAssistantResponse(data) {
  const container = document.getElementById('chat-messages');
  const msgEl = document.createElement('div');
  msgEl.className = 'chat-msg assistant';

  let routeClass = 'route-MULTI';
  if (data.algorithm_selected.includes('CSP')) routeClass = 'route-CSP';
  else if (data.algorithm_selected.includes('A*')) routeClass = 'route-ASTAR';
  else if (data.algorithm_selected.includes('RAG')) routeClass = 'route-RAG';

  // Format reply markdown to basic HTML
  let formattedReply = formatMarkdown(data.reply);

  // Build Structured Event Card if plan exists
  let planHtml = '';
  if (data.plan && data.plan.assigned_venue_name) {
    const p = data.plan;
    const badgeClass = p.status === 'APPROVED' ? 'badge-APPROVED' : (p.status === 'CONDITIONALLY_APPROVED' ? 'badge-CONDITIONALLY_APPROVED' : 'badge-REJECTED');

    const checklistItems = (p.action_items || []).map(item => `
      <li>
        <input type="checkbox" checked disabled>
        <span>${escapeHtml(item)}</span>
      </li>
    `).join('');

    planHtml = `
      <div class="allocation-card">
        <div class="allocation-header">
          <div>
            <div class="allocation-title">${escapeHtml(p.assigned_venue_name)}</div>
            <span style="font-size: 0.78rem; color: var(--gray-600);">${escapeHtml(p.event_name)}</span>
          </div>
          <span class="badge ${badgeClass}">${p.status.replace('_', ' ')}</span>
        </div>

        <div class="allocation-grid">
          <div class="alloc-item">
            <span class="alloc-label">Date & Time</span>
            <span class="alloc-val">${formatDateTime(p.start_time)} – ${formatTime(p.end_time)}</span>
          </div>
          <div class="alloc-item">
            <span class="alloc-label">Capacity Efficiency</span>
            <span class="alloc-val">${p.capacity_waste} unused seats</span>
          </div>
          <div class="alloc-item">
            <span class="alloc-label">Compliance Score</span>
            <span class="alloc-val">${p.compliance_score}% Adherence</span>
          </div>
          <div class="alloc-item">
            <span class="alloc-label">Operational Buffer</span>
            <span class="alloc-val">15–45m setup buffer included</span>
          </div>
        </div>

        ${checklistItems ? `
          <div class="checklist-section">
            <div class="section-label">Logistics & Compliance Requirements</div>
            <ul class="checklist-items">${checklistItems}</ul>
          </div>
        ` : ''}

        <div style="margin-top: 0.85rem; display: flex; gap: 0.5rem;">
          <button class="btn btn-primary btn-sm btn-export-ics" data-plan='${escapeAttr(JSON.stringify(p))}'>
            📥 Download Calendar Invite (.ics)
          </button>
        </div>
      </div>
    `;
  }

  // Build Expandable Sub-agent Trace Accordion
  let traceHtml = '';
  if (data.subagent_dialogue && data.subagent_dialogue.length > 0) {
    const traceItems = data.subagent_dialogue.map(m => `
      <div class="trace-item ${escapeHtml(m.sender)}">
        <div style="display: flex; justify-content: space-between; font-weight: 600; color: var(--gray-800);">
          <span>${escapeHtml(m.sender)} ➔ ${escapeHtml(m.recipient)}</span>
          <span style="font-size: 0.7rem; color: var(--gray-500);">${m.message_type}</span>
        </div>
        <p style="margin-top: 0.2rem; color: var(--gray-700);">${escapeHtml(m.content)}</p>
      </div>
    `).join('');

    traceHtml = `
      <div class="trace-accordion">
        <button class="trace-toggle-btn" onclick="toggleTrace(this)">
          <span>🔍 Behind the Scenes: Multi-Agent Coordination Trace (${data.subagent_dialogue.length} messages)</span>
          <span class="toggle-icon">▼</span>
        </button>
        <div class="trace-content" style="display: none;">
          ${traceItems}
        </div>
      </div>
    `;
  }

  // Build Suggested Follow-ups
  let followupsHtml = '';
  if (data.suggested_followups && data.suggested_followups.length > 0) {
    followupsHtml = `
      <div class="quick-chips" style="margin-top: 0.75rem;">
        <span class="chips-label">Next steps:</span>
        ${data.suggested_followups.map(f => `
          <button class="chat-chip" onclick="sendMessage('${escapeHtml(f)}')">${escapeHtml(f)}</button>
        `).join('')}
      </div>
    `;
  }

  msgEl.innerHTML = `
    <div class="msg-avatar">🤖</div>
    <div class="msg-content">
      <div class="msg-sender">Orchestrator Agent</div>
      <div class="msg-body">
        <div class="routing-pill ${routeClass}">
          <span>⚙️ ${escapeHtml(data.algorithm_selected)}</span>
        </div>
        <div>${formattedReply}</div>
        ${planHtml}
        ${traceHtml}
      </div>
      ${followupsHtml}
    </div>
  `;

  container.appendChild(msgEl);

  // Attach .ics download listeners
  msgEl.querySelectorAll('.btn-export-ics').forEach(btn => {
    btn.addEventListener('click', () => {
      const planData = JSON.parse(btn.dataset.plan);
      exportCalendar(planData);
    });
  });

  container.scrollTop = container.scrollHeight;
}

window.toggleTrace = function(btn) {
  const content = btn.nextElementSibling;
  const icon = btn.querySelector('.toggle-icon');
  if (content.style.display === 'none') {
    content.style.display = 'flex';
    icon.textContent = '▲';
  } else {
    content.style.display = 'none';
    icon.textContent = '▼';
  }
};

async function exportCalendar(plan) {
  try {
    const res = await fetch('/schedule/export-ics', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        events: [{
          event_name: plan.event_name,
          venue_name: plan.assigned_venue_name,
          start_time: plan.start_time,
          end_time: plan.end_time,
          description: plan.executive_summary,
        }]
      })
    });

    if (!res.ok) throw new Error('Failed to generate .ics');
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${plan.event_name.replace(/\s+/g, '_')}.ics`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    alert(`Could not export calendar: ${err.message}`);
  }
}

// ----------------------------------------------------
// AI Benchmark Runner
// ----------------------------------------------------
function initBenchmark() {
  const btn = document.getElementById('btn-run-benchmark');
  btn.addEventListener('click', runBenchmark);
}

async function runBenchmark() {
  const scenario = document.getElementById('benchmark-scenario').value;
  const container = document.getElementById('benchmark-results');
  container.innerHTML = `<div class="loading-spinner">Executing benchmark on '${scenario}' scenario...</div>`;

  try {
    const res = await fetch('/evaluation/benchmark', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_name: scenario }),
    });

    if (!res.ok) throw new Error('Benchmark failed');
    const data = await res.json();

    const rows = data.evaluations.map(e => `
      <tr>
        <td><strong>${escapeHtml(e.algorithm_name)}</strong></td>
        <td><span class="badge ${e.success ? 'badge-APPROVED' : 'badge-CONDITIONALLY_APPROVED'}">${e.solve_rate_percent}% (${e.assigned_count}/${e.total_events})</span></td>
        <td>${e.execution_time_ms.toFixed(2)} ms</td>
        <td>${e.nodes_expanded}</td>
        <td>${e.total_capacity_waste} seats</td>
        <td style="font-size: 0.78rem; color: var(--gray-600);">${escapeHtml(e.trade_off_summary)}</td>
      </tr>
    `).join('');

    container.innerHTML = `
      <table class="benchmark-table">
        <thead>
          <tr>
            <th>Algorithm</th>
            <th>Solve Rate</th>
            <th>Execution Time</th>
            <th>Expansions / Iterations</th>
            <th>Seat Waste</th>
            <th>Key Trade-Off</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
      <div class="rec-banner">
        💡 <strong>Orchestrator Decision:</strong> ${escapeHtml(data.recommendation)}
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><p style="color: var(--danger);">${escapeHtml(err.message)}</p></div>`;
  }
}

// ----------------------------------------------------
// Directory & Corpus Loaders
// ----------------------------------------------------
async function loadVenues() {
  const container = document.getElementById('venues-grid');
  try {
    const res = await fetch('/venues');
    if (!res.ok) throw new Error('Failed to load venues');
    const venues = await res.json();

    container.innerHTML = venues.map(v => `
      <div class="venue-card">
        <div class="venue-card-header">
          <h3>${escapeHtml(v.name)}</h3>
          <span class="venue-capacity">👥 ${v.capacity} seats</span>
        </div>
        <div class="venue-building">📍 ${escapeHtml(v.building || 'Campus Grounds')} &bull; <span style="text-transform: capitalize;">${v.venue_type}</span></div>
        <div class="venue-facilities">
          ${v.facilities.map(f => `<span class="facility-pill">${escapeHtml(f)}</span>`).join('')}
        </div>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><p style="color: var(--danger);">${escapeHtml(err.message)}</p></div>`;
  }
}

async function loadPolicyDocuments() {
  const container = document.getElementById('policy-docs-grid');
  try {
    const res = await fetch('/rag/documents');
    if (!res.ok) throw new Error('Failed to load policy corpus');
    const data = await res.json();

    container.innerHTML = data.indexed_documents.map(d => `
      <div class="venue-card" style="margin-bottom: 1rem;">
        <div class="venue-card-header">
          <h3>📜 ${escapeHtml(d.title)}</h3>
          <span class="venue-capacity">${d.clauses_count} clauses</span>
        </div>
        <p style="font-size: 0.82rem; color: var(--gray-600);">Indexed sections: ${escapeHtml(d.sections.join(', '))}</p>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = `<div class="empty-state"><p style="color: var(--danger);">${escapeHtml(err.message)}</p></div>`;
  }
}

// Helpers
function escapeHtml(text) {
  if (!text) return '';
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeAttr(text) {
  if (!text) return '';
  return String(text).replace(/"/g, '&quot;');
}

function formatMarkdown(md) {
  if (!md) return '';
  let html = escapeHtml(md);
  html = html.replace(/^### (.*$)/gim, '<h3 style="font-size: 1.05rem; margin-bottom: 0.5rem; color: var(--gray-900);">$1</h3>');
  html = html.replace(/^#### (.*$)/gim, '<h4 style="font-size: 0.9rem; margin-top: 0.6rem; color: var(--gray-700);">$1</h4>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/_(.*?)_/g, '<em>$1</em>');
  html = html.replace(/`(.*?)`/g, '<code style="background: var(--gray-100); padding: 0.15rem 0.35rem; border-radius: 4px; font-family: monospace;">$1</code>');
  html = html.replace(/\n\n/g, '<br><br>');
  html = html.replace(/\n- /g, '<br>&bull; ');
  return html;
}

function formatDateTime(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return isoStr;
  }
}

function formatTime(isoStr) {
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  } catch {
    return isoStr;
  }
}
