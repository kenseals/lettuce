const TOKEN_STORAGE_KEY = 'lettuce.previewToken';
const TOKEN_HEADER = 'X-Lettuce-Preview-Token';
const VIEWS = ['dashboard', 'setup', 'sources', 'brain', 'lenses', 'destinations', 'signals', 'settings'];

const VIEW_META = {
  dashboard: {
    kicker: 'Workspace overview',
    title: 'Dashboard',
    subtitle: 'See setup progress, recent signal flow, and the next useful action.'
  },
  setup: {
    kicker: 'First steps',
    title: 'Setup',
    subtitle: 'Choose the workspace, capture the company summary, and get to the first signal.'
  },
  sources: {
    kicker: 'Inputs',
    title: 'Sources',
    subtitle: 'Connect or request sources, and use manual paste for the fastest signal capture path.'
  },
  brain: {
    kicker: 'Durable state',
    title: 'Company Brain',
    subtitle: 'Inspect first-class objects and the update log that changes them.'
  },
  lenses: {
    kicker: 'Interpretation',
    title: 'Lenses',
    subtitle: 'Review the default lens pack and add local custom lenses when needed.'
  },
  destinations: {
    kicker: 'Outputs',
    title: 'Destinations',
    subtitle: 'Company Brain is active now; other destinations stay request-only until the loop is trusted.'
  },
  signals: {
    kicker: 'Audit trail',
    title: 'Signals / Audit',
    subtitle: 'Review recent signals, lens findings, route proposals, company changes, and feedback.'
  },
  settings: {
    kicker: 'Runtime access',
    title: 'Settings',
    subtitle: 'Keep the preview token out of the way until you need write access.'
  }
};

const fallbackState = {
  metrics: [
    { label: 'Signals processed', value: '0', detail: 'No runtime connection' },
    { label: 'Connected sources', value: '0', detail: 'Runtime unavailable' },
    { label: 'Custom lenses', value: '0', detail: 'Add one when defaults are not enough' },
    { label: 'Pending requests', value: '0', detail: 'Connectors and destinations queue here' }
  ],
  organization: {
    id: 'lettuce-labs',
    name: 'Lettuce Labs',
    slug: 'lettuce-labs',
    status: 'workspace selected',
    setup_stage: 'Starter workspace',
    updated_at: 'seed',
    summary: 'Local runtime workspace for product setup and signal review.'
  },
  user_profile: {
    name: '',
    email: '',
    role: '',
    updated_at: 'seed'
  },
  current_org_id: 'lettuce-labs',
  organizations: [
    { id: 'lettuce-labs', name: 'Lettuce Labs', slug: 'lettuce-labs', created_at: 'seed' }
  ],
  onboarding: {
    user_ready: false,
    org_ready: true,
    brain_ready: true,
    sources_ready: true,
    lenses_ready: false,
    destinations_ready: true,
    first_signal_ready: false
  },
  sources: [
    {
      id: 'openclaw-client',
      icon: '◌',
      name: 'OpenClaw client',
      detail: 'Submit signals from your agent into Lettuce while Lettuce runs independently.',
      status: 'Active',
      active: true,
      action: 'active',
      button: 'Active',
      setup: 'Use the Lettuce client/API to submit real session summaries, decisions, and workflow signals.'
    },
    {
      id: 'manual-paste',
      icon: '✎',
      name: 'Manual paste',
      detail: 'Paste notes, transcripts, summaries, or customer messages.',
      status: 'Active',
      active: true,
      action: 'manual',
      button: 'Open paste form',
      setup: 'Fastest path to the first signal.'
    },
    {
      id: 'markdown-github',
      icon: '◧',
      name: 'Markdown / GitHub',
      detail: 'Docs, issues, exported notes, and repo material.',
      status: 'Request connector',
      active: false,
      action: 'request',
      button: 'Request',
      setup: 'Store a local request; no external integration is configured here.'
    }
  ],
  requested_connectors: [],
  destinations: [
    {
      id: 'company-brain',
      icon: '☘',
      name: 'Company Brain',
      detail: 'Active local JSON destination for reviewed context updates and update logs.',
      status: 'Active',
      active: true,
      action: 'active',
      button: 'Active'
    },
    {
      id: 'linear',
      icon: '▣',
      name: 'Linear',
      detail: 'Request issue and project routing once the local loop is trusted.',
      status: 'Coming soon',
      active: false,
      action: 'request',
      button: 'Request'
    },
    {
      id: 'notion',
      icon: 'N',
      name: 'Notion',
      detail: 'Request reviewed push or sync workflows to operating docs.',
      status: 'Coming soon',
      active: false,
      action: 'request',
      button: 'Request'
    }
  ],
  requested_destinations: [],
  lenses: [
    { id: 'opportunity-signal', name: 'Opportunity Signal', body: 'Find market pull, painful workflows, budget clues, and wedge shifts.', tags: ['product', 'market', 'revenue'] },
    { id: 'relationship-signal', name: 'Relationship Signal', body: 'Notice named people, accounts, commitments, trust changes, and follow-up loops.', tags: ['crm', 'account'] },
    { id: 'project-focus-shift', name: 'Project Focus Shift', body: 'Notice changes in scope, priority, active work, or direction.', tags: ['execution', 'project'] },
    { id: 'next-action', name: 'Next Action', body: 'Turn the signal into one useful owner, route, and next step.', tags: ['owner', 'execution'] }
  ],
  routers: [
    { name: 'Company Brain profile', detail: 'Writes reviewed updates into local company profile objects.', status: 'Preview only' },
    { name: 'Operator brief', detail: 'Builds a packet-backed review surface before any external write.', status: 'Preview only' }
  ],
  signals: [
    {
      id: 'baschez-company-brain',
      title: 'Baschez: company brain control problem',
      quote: 'Better organized Notion is not enough if agents are not forced, reminded, and equipped to use the context.',
      lenses: ['Opportunity', 'Project Shift', 'Next Action'],
      routes: ['Operational memory note', 'Lettuce positioning doc', 'daily memory'],
      feedback: 'Waiting for operator feedback'
    }
  ],
  audit: [
    { time: 'seed', title: 'Runtime unavailable', body: 'Start the Lettuce runtime to load live workspace state.' }
  ],
  feedback_actions: [
    { id: 'approve', label: 'Approve', description: 'Mark the proposed routes as useful enough to apply.' },
    { id: 'edit', label: 'Edit', description: 'Capture the correction that should train the lens or router.' },
    { id: 'decline', label: 'Decline', description: 'Reject noisy or unsafe recommendations and record why.' }
  ],
  feedback: [],
  company_brain: {
    company_profile: {
      summary: 'Workspace for reviewed context updates.',
      positioning: 'Inspectable company context for agent workflows.',
      current_stage: 'Starter workspace',
      updated_at: 'seed'
    },
    people_accounts: [
      { id: 'ken', name: 'Ken', type: 'operator', status: 'active', notes: 'Primary reviewer for the app shell and runtime loop.' }
    ],
    projects_products: [
      { id: 'lettuce-app', name: 'Lettuce app', status: 'active', notes: 'Standalone app/runtime for source, lens, destination, signal review, and company-brain updates.' }
    ],
    decisions_defaults: [
      { id: 'review-first', decision: 'Keep reviewed context updates local first.', source: 'seed', updated_at: 'seed' }
    ],
    open_loops_risks: [
      { id: 'first-real-signal', risk: 'Need more real signals in the audit trail.', owner: 'operator', status: 'open' }
    ],
    agent_context_changelog: [
      { id: 'runtime-unavailable', time: 'seed', title: 'Runtime unavailable', body: 'Start the runtime to inspect live Company Brain state.' }
    ]
  }
};

const appState = {
  data: clone(fallbackState),
  apiOnline: false,
  view: 'dashboard',
  selectedSignalId: '',
  selectedSignalDetail: null,
  previewToken: readStoredToken()
};

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function $(selector) {
  return document.querySelector(selector);
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}

function normalizeView(value) {
  return VIEWS.includes(value) ? value : '';
}

function readStoredToken() {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

function saveStoredToken(token) {
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {
    return;
  }
}

function showNotice(message, tone = 'info') {
  const notice = $('#globalNotice');
  if (!notice) return;
  notice.hidden = false;
  notice.className = `notice${tone === 'info' ? '' : ` ${tone}`}`;
  notice.textContent = message;
}

function clearNotice() {
  const notice = $('#globalNotice');
  if (!notice) return;
  notice.hidden = true;
  notice.textContent = '';
  notice.className = 'notice';
}

function setStatus(id, message) {
  const element = document.getElementById(id);
  if (element) {
    element.textContent = message;
  }
}

function statusClass(active, fallback = false) {
  if (active) return 'ready';
  if (fallback) return 'warning';
  return '';
}

function metricsFromState(data) {
  const customLensCount = (data.lenses || []).filter((lens) => lens.custom).length;
  const appliedSignals = (data.signals || []).filter((signal) => (signal.company_changes || []).length).length;
  return [
    { label: 'Signals processed', value: String((data.signals || []).length), detail: 'Stored in local runtime state' },
    { label: 'Applied updates', value: String(appliedSignals), detail: 'Reviewed into Company Brain' },
    { label: 'Connected sources', value: String((data.sources || []).filter((source) => source.active).length), detail: 'Usable now' },
    { label: 'Lenses', value: String((data.lenses || []).length), detail: `${customLensCount} custom` }
  ];
}

function checklistItems(data) {
  const onboarding = data.onboarding || {};
  return [
    { key: 'user_ready', label: 'Create your user profile', detail: 'Save the operator account that reviews signal and applies updates.', view: 'setup', cta: 'Open setup', done: !!onboarding.user_ready },
    { key: 'org_ready', label: 'Choose the workspace', detail: 'Select an existing org or create a new local workspace.', view: 'setup', cta: 'Open setup', done: !!onboarding.org_ready },
    { key: 'brain_ready', label: 'Save company brain basics', detail: 'Capture summary, positioning, and current stage.', view: 'setup', cta: 'Edit brain', done: !!onboarding.brain_ready },
    { key: 'sources_ready', label: 'Confirm a source path', detail: 'Manual paste and OpenClaw should be usable before connector work.', view: 'sources', cta: 'Open sources', done: !!onboarding.sources_ready },
    { key: 'lenses_ready', label: 'Review or add lenses', detail: 'Defaults are usable; add one custom lens when a workflow needs it.', view: 'lenses', cta: 'Open lenses', done: !!onboarding.lenses_ready },
    { key: 'destinations_ready', label: 'Confirm output destination', detail: 'Company Brain should stay active until external writes are approved.', view: 'destinations', cta: 'Open destinations', done: !!onboarding.destinations_ready },
    { key: 'first_signal_ready', label: 'Process the first signal', detail: 'Submit a pasted signal and review the audit detail.', view: 'sources', cta: 'Paste signal', done: !!onboarding.first_signal_ready }
  ];
}

function preferredView(data) {
  return checklistItems(data).every((item) => item.done) ? 'dashboard' : 'setup';
}

function nextAction(data) {
  return checklistItems(data).find((item) => !item.done) || {
    label: 'Review the latest signal',
    detail: 'The core setup is done. Inspect recent signals and feedback next.',
    view: 'signals',
    cta: 'Open audit',
    done: true
  };
}

async function fetchJson(path) {
  const response = await fetch(path, { headers: { accept: 'application/json' } });
  const raw = await response.text();
  let data = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = {};
  }
  if (!response.ok) {
    const error = new Error(data.error || `${response.status} ${response.statusText}`);
    error.data = data;
    throw error;
  }
  return data;
}

async function postJson(path, payload) {
  const headers = { accept: 'application/json', 'Content-Type': 'application/json' };
  if (appState.previewToken) {
    headers[TOKEN_HEADER] = appState.previewToken;
  }
  const response = await fetch(path, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload)
  });
  const raw = await response.text();
  let data = {};
  try {
    data = raw ? JSON.parse(raw) : {};
  } catch {
    data = {};
  }
  if (!response.ok) {
    const error = new Error(data.error || `${response.status} ${response.statusText}`);
    error.data = data;
    throw error;
  }
  return data;
}

function buildFallbackDetail(signal) {
  const summary = signal || {};
  return {
    id: summary.id || 'fallback-signal',
    summary,
    input: {
      source: 'fallback',
      path: null,
      body: summary.quote || ''
    },
    lens_findings: (summary.lenses || []).map((lens) => ({ lens, finding: 'Available in fallback mode.', fired: true, skipped: false, runner: 'fallback' })),
    route_proposals: (summary.routes || []).map((route) => ({ path: route, action: 'preview', requires_approval: true, preview: 'Preview-only in fallback mode.' })),
    feedback_history: [],
    context_update: {
      company_changes: summary.company_changes || [],
      update_logs: [],
      provenance_chain: { raw_signal_path: null, route_paths: summary.routes || [], updated_objects: [] },
      result: 'Fallback mode only shows minimal offline structure. Start the runtime for real workspace data.'
    }
  };
}

async function refreshData(options = {}) {
  try {
    const remote = await fetchJson('/api/state');
    appState.apiOnline = true;
    appState.data = remote;
    clearNotice();
  } catch {
    appState.apiOnline = false;
    appState.data = clone(fallbackState);
    showNotice('Runtime unavailable. Start `python3 -m lettuce.runtime` for live state and writes.', 'warning');
  }

  const currentSignals = appState.data.signals || [];
  if (!currentSignals.find((signal) => signal.id === appState.selectedSignalId)) {
    appState.selectedSignalId = currentSignals[0]?.id || '';
  }

  const hashView = normalizeView(window.location.hash.slice(1));
  appState.view = hashView || preferredView(appState.data);
  if (!hashView) {
    history.replaceState(null, '', `#${appState.view}`);
  }

  await ensureSelectedSignalDetail();
  renderAll();
  if (options.notice) {
    showNotice(options.notice, 'info');
  }
}

async function ensureSelectedSignalDetail() {
  const signalId = appState.selectedSignalId;
  if (!signalId) {
    appState.selectedSignalDetail = null;
    return;
  }
  const signal = (appState.data.signals || []).find((entry) => entry.id === signalId);
  if (!appState.apiOnline) {
    appState.selectedSignalDetail = buildFallbackDetail(signal);
    return;
  }
  try {
    appState.selectedSignalDetail = await fetchJson(`/api/signals/${encodeURIComponent(signalId)}`);
  } catch {
    appState.selectedSignalDetail = buildFallbackDetail(signal);
  }
}

function renderAll() {
  renderChrome();
  renderDashboard();
  renderSetup();
  renderSources();
  renderBrain();
  renderLenses();
  renderDestinations();
  renderSignals();
  renderSettings();
}

function renderChrome() {
  const data = appState.data;
  const organization = data.organization || {};
  const meta = VIEW_META[appState.view] || VIEW_META.dashboard;
  $('#viewKicker').textContent = meta.kicker;
  $('#viewTitle').textContent = meta.title;
  $('#viewSubtitle').textContent = meta.subtitle;

  $('#sidebarOrgName').textContent = organization.name || 'Unnamed workspace';
  $('#sidebarOrgSummary').textContent = organization.summary || 'No workspace summary saved yet.';
  $('#sidebarCounts').innerHTML = [
    `<span class="pill ${statusClass(appState.apiOnline, !appState.apiOnline)}">${escapeHtml(appState.apiOnline ? 'Runtime connected' : 'Fallback data')}</span>`,
    `<span class="pill">${escapeHtml(String((data.sources || []).filter((source) => source.active).length))} sources</span>`,
    `<span class="pill">${escapeHtml(String((data.signals || []).length))} ${(data.signals || []).length === 1 ? 'signal' : 'signals'}</span>`
  ].join('');

  const tokenReady = Boolean(appState.previewToken);
  const tokenMessage = tokenReady ? 'Write token active' : 'Read-only mode';
  $('#tokenPill').textContent = tokenMessage;
  $('#tokenPill').className = `token-pill${tokenReady ? ' ready' : ''}`;
  $('#sidebarTokenState').textContent = tokenReady ? 'Preview token saved locally' : 'Preview token not saved';
  $('#sidebarTokenState').className = `token-state${tokenReady ? ' ready' : ''}`;

  document.querySelectorAll('[data-view-link]').forEach((link) => {
    link.classList.toggle('active', link.getAttribute('data-view-link') === appState.view);
  });
  document.querySelectorAll('.view').forEach((section) => {
    section.classList.toggle('active', section.getAttribute('data-view') === appState.view);
  });
}

function renderChecklistHtml(data) {
  return `<div class="checklist">${checklistItems(data).map((item) => `
    <div class="check-item ${item.done ? 'done' : ''}">
      <span class="check-dot" aria-hidden="true"></span>
      <div class="check-copy">
        <strong>${escapeHtml(item.label)}</strong>
        <span>${escapeHtml(item.detail)}</span>
        <a class="ghost-link" href="#${escapeHtml(item.view)}">${escapeHtml(item.cta)}</a>
      </div>
    </div>
  `).join('')}</div>`;
}

function renderDashboard() {
  const data = appState.data;
  const next = nextAction(data);
  $('#dashboardActionCard').innerHTML = `
    <p class="section-label">Next action</p>
    <div class="summary-block">
      <h2>${escapeHtml(next.label)}</h2>
      <p>${escapeHtml(next.detail)}</p>
      <div class="row-actions">
        <a class="primary button-link" href="#${escapeHtml(next.view)}">${escapeHtml(next.cta)}</a>
        <a class="secondary button-link" href="#signals">Open recent audit</a>
      </div>
    </div>
  `;

  $('#dashboardChecklist').innerHTML = renderChecklistHtml(data);
  $('#dashboardMetrics').innerHTML = metricsFromState(data).map((metric) => `
    <article class="metric-card">
      <span>${escapeHtml(metric.label)}</span>
      <strong>${escapeHtml(metric.value)}</strong>
      <small>${escapeHtml(metric.detail || '')}</small>
    </article>
  `).join('');

  const signals = data.signals || [];
  $('#dashboardSignals').innerHTML = signals.length ? signals.slice(0, 5).map((signal) => renderSignalRow(signal, false)).join('') : emptyState('No signals yet. Use Manual paste or the OpenClaw source to create one.');

  const activeSources = (data.sources || []).filter((source) => source.active);
  $('#dashboardSources').innerHTML = activeSources.length ? activeSources.map((source) => `
    <article class="source-card">
      <div class="row-head">
        <div class="card-topline">
          <span class="card-icon">${escapeHtml(source.icon || '•')}</span>
          <strong>${escapeHtml(source.name)}</strong>
        </div>
        <span class="pill success">${escapeHtml(source.status || 'Active')}</span>
      </div>
      <small>${escapeHtml(source.detail || '')}</small>
    </article>
  `).join('') : emptyState('No active sources yet.');
}

function renderSetup() {
  const data = appState.data;
  const organization = data.organization || {};
  const user = data.user_profile || {};
  const organizations = data.organizations || [];
  const profile = (data.company_brain || {}).company_profile || {};
  const orgSelect = $('#orgSelect');
  if (orgSelect) {
    orgSelect.innerHTML = organizations.map((org) => `<option value="${escapeHtml(org.id)}" ${org.id === data.current_org_id ? 'selected' : ''}>${escapeHtml(org.name)}</option>`).join('');
  }

  if (document.activeElement !== $('#userName')) {
    $('#userName').value = user.name || '';
  }
  if (document.activeElement !== $('#userEmail')) {
    $('#userEmail').value = user.email || '';
  }
  if (document.activeElement !== $('#userRole')) {
    $('#userRole').value = user.role || '';
  }

  $('#currentOrgStatus').textContent = organization.status || 'Not configured';
  $('#setupChecklist').innerHTML = renderChecklistHtml(data);
  $('#setupWorkspaceSummary').innerHTML = `
    <div class="workspace-block">
      <h3>${escapeHtml(organization.name || 'No workspace selected')}</h3>
      <p>${escapeHtml(organization.summary || 'Select a workspace to start storing state locally.')}</p>
      <dl>
        <div><dt>User</dt><dd>${escapeHtml(user.name ? `${user.name}${user.role ? ` · ${user.role}` : ''}` : 'Not set')}</dd></div>
        <div><dt>Stage</dt><dd>${escapeHtml(organization.setup_stage || 'Not set')}</dd></div>
        <div><dt>Updated</dt><dd>${escapeHtml(organization.updated_at || 'Never')}</dd></div>
      </dl>
    </div>
  `;

  $('#setupNextCard').innerHTML = `
    <p class="section-label">Recommended next step</p>
    <div class="summary-block">
      <h2>${escapeHtml(nextAction(data).label)}</h2>
      <p>${escapeHtml(nextAction(data).detail)}</p>
      <a class="primary button-link" href="#${escapeHtml(nextAction(data).view)}">${escapeHtml(nextAction(data).cta)}</a>
      <p class="muted">Preview token stays optional until you need to submit writes from this browser.</p>
    </div>
  `;

  if (document.activeElement !== $('#brainSummary')) {
    $('#brainSummary').value = profile.summary || '';
  }
  if (document.activeElement !== $('#brainPositioning')) {
    $('#brainPositioning').value = profile.positioning || '';
  }
  if (document.activeElement !== $('#brainStage')) {
    $('#brainStage').value = profile.current_stage || organization.setup_stage || '';
  }
}

function sourceActionButton(source) {
  if (source.action === 'manual') {
    return `<button class="primary" type="button" data-source-action="manual">${escapeHtml(source.button || 'Open')}</button>`;
  }
  if (source.action === 'request') {
    return `<button class="secondary" type="button" data-request-connector="${escapeHtml(source.name || '')}">${escapeHtml(source.button || 'Request')}</button>`;
  }
  return `<span class="pill success">${escapeHtml(source.button || source.status || 'Active')}</span>`;
}

function renderSources() {
  const data = appState.data;
  $('#sourceCatalog').innerHTML = (data.sources || []).map((source) => `
    <article class="source-card">
      <div class="row-head">
        <div class="card-topline">
          <span class="card-icon">${escapeHtml(source.icon || '•')}</span>
          <strong>${escapeHtml(source.name || 'Source')}</strong>
        </div>
        <span class="pill ${source.active ? 'success' : 'warning'}">${escapeHtml(source.status || (source.active ? 'Active' : 'Inactive'))}</span>
      </div>
      <small>${escapeHtml(source.detail || '')}</small>
      <p>${escapeHtml(source.setup || '')}</p>
      ${sourceActionButton(source)}
    </article>
  `).join('');

  const requests = data.requested_connectors || [];
  $('#requestedConnectors').innerHTML = requests.length ? requests.map((entry) => `
    <article class="request-item">
      <strong>${escapeHtml(entry.name || 'Connector')}</strong>
      <small>Requested ${escapeHtml(entry.requested_at || 'recently')}</small>
    </article>
  `).join('') : emptyState('No connector requests yet. Requestable sources will show up here.');
}

function brainGroups(brain) {
  return [
    { key: 'people_accounts', title: 'People + accounts', items: brain.people_accounts || [] },
    { key: 'projects_products', title: 'Projects + products', items: brain.projects_products || [] },
    { key: 'decisions_defaults', title: 'Decisions + defaults', items: brain.decisions_defaults || [] },
    { key: 'open_loops_risks', title: 'Open loops + risks', items: brain.open_loops_risks || [] },
    { key: 'agent_context_changelog', title: 'Agent context changelog', items: brain.agent_context_changelog || [] }
  ];
}

function describeBrainItem(item) {
  return item.notes || item.body || item.summary || item.positioning || item.detail || item.decision || item.risk || 'No detail saved.';
}

function titleForBrainItem(item) {
  return item.name || item.title || item.decision || item.risk || item.id || 'Untitled object';
}

function metaForBrainItem(item) {
  return [item.type, item.status, item.owner, item.source, item.updated_at, item.time].filter(Boolean).join(' · ');
}

function collectBrainUpdates(brain) {
  const updates = [];
  const sections = [
    ['company_profile', [brain.company_profile || {}]],
    ['people_accounts', brain.people_accounts || []],
    ['projects_products', brain.projects_products || []],
    ['decisions_defaults', brain.decisions_defaults || []],
    ['open_loops_risks', brain.open_loops_risks || []]
  ];

  sections.forEach(([section, items]) => {
    items.forEach((item) => {
      (item.update_log || []).forEach((entry) => {
        const provenance = entry.provenance || {};
        updates.push({
          section,
          label: entry.label || 'Updated object',
          detail: entry.detail || describeBrainItem(item),
          objectLabel: titleForBrainItem(item),
          time: entry.time || entry.updated_at || item.updated_at || 'recently',
          provenance: [provenance.raw_signal_path ? 'raw signal' : '', provenance.run_id ? `packet ${provenance.run_id}` : '', entry.object_area && entry.object_id ? `${entry.object_area}:${entry.object_id}` : ''].filter(Boolean).join(' → ')
        });
      });
    });
  });

  (brain.agent_context_changelog || []).forEach((entry) => {
    updates.push({
      section: 'agent_context_changelog',
      label: entry.title || 'Agent context updated',
      detail: entry.body || '',
      objectLabel: entry.id || 'changelog',
      time: entry.time || 'recently',
      provenance: ''
    });
  });

  return updates;
}

function renderBrain() {
  const data = appState.data;
  const organization = data.organization || {};
  const brain = data.company_brain || {};
  const profile = brain.company_profile || {};
  $('#brainProfileCard').innerHTML = `
    <p class="section-label">Company profile</p>
    <div class="summary-block">
      <h2>${escapeHtml(organization.name || 'Unnamed workspace')}</h2>
      <p>${escapeHtml(profile.summary || organization.summary || 'No company summary saved yet.')}</p>
      <dl>
        <div><dt>Positioning</dt><dd>${escapeHtml(profile.positioning || 'Not set')}</dd></div>
        <div><dt>Stage</dt><dd>${escapeHtml(profile.current_stage || organization.setup_stage || 'Not set')}</dd></div>
        <div><dt>Workspace status</dt><dd>${escapeHtml(organization.status || 'Unknown')}</dd></div>
        <div><dt>Updated</dt><dd>${escapeHtml(profile.updated_at || organization.updated_at || 'Never')}</dd></div>
      </dl>
    </div>
  `;

  $('#brainObjects').innerHTML = brainGroups(brain).map((group) => `
    <article class="brain-object">
      <div class="row-head">
        <strong>${escapeHtml(group.title)}</strong>
        <span class="pill">${escapeHtml(String(group.items.length))}</span>
      </div>
      <div class="object-list">
        ${group.items.length ? group.items.map((item) => `
          <div class="brain-object">
            <strong>${escapeHtml(titleForBrainItem(item))}</strong>
            <p>${escapeHtml(describeBrainItem(item))}</p>
            <small>${escapeHtml(metaForBrainItem(item) || 'No metadata yet.')}</small>
          </div>
        `).join('') : emptyState('No objects yet.')}
      </div>
    </article>
  `).join('');

  const updates = collectBrainUpdates(brain);
  $('#brainUpdateLog').innerHTML = updates.length ? updates.map((entry) => `
    <article class="update-row">
      <div class="row-head">
        <strong>${escapeHtml(entry.label)}</strong>
        <small>${escapeHtml(entry.time || 'recently')}</small>
      </div>
      <p>${escapeHtml(entry.detail)}</p>
      <small>${escapeHtml(entry.objectLabel)}${entry.provenance ? ` · ${escapeHtml(entry.provenance)}` : ''}</small>
    </article>
  `).join('') : emptyState('No update log entries recorded yet. Process a signal to create them.');
}

function renderLenses() {
  const lenses = appState.data.lenses || [];
  $('#lensCatalog').innerHTML = lenses.length ? lenses.map((lens) => `
    <article class="lens-card">
      <div class="row-head">
        <strong>${escapeHtml(lens.name || 'Lens')}</strong>
        <span class="pill ${lens.custom ? 'success' : ''}">${escapeHtml(lens.custom ? 'Custom' : 'Default')}</span>
      </div>
      <p>${escapeHtml(lens.body || '')}</p>
      <div class="card-meta">${(lens.tags || []).map((tag) => `<span class="pill">${escapeHtml(tag)}</span>`).join('')}</div>
      ${lens.custom ? `<button class="secondary" type="button" data-edit-lens-id="${escapeHtml(lens.id || '')}">Edit lens</button>` : ''}
    </article>
  `).join('') : emptyState('No lenses available.');
}

function renderDestinations() {
  const data = appState.data;
  const companyBrain = (data.destinations || []).find((destination) => destination.id === 'company-brain') || {};
  $('#destinationHeroCard').innerHTML = `
    <p class="section-label">Active destination</p>
    <div class="summary-block">
      <h2>${escapeHtml(companyBrain.name || 'Company Brain')}</h2>
      <p>${escapeHtml(companyBrain.detail || 'Local workspace state remains the active destination.')}</p>
      <dl>
        <div><dt>Status</dt><dd>${escapeHtml(companyBrain.status || 'Active')}</dd></div>
        <div><dt>Writes</dt><dd>Reviewed and local</dd></div>
        <div><dt>First path</dt><dd>Manual paste</dd></div>
        <div><dt>Audit</dt><dd>Packet-backed</dd></div>
      </dl>
      <a class="primary button-link" href="#sources">Submit signal</a>
    </div>
  `;

  $('#destinationCatalog').innerHTML = (data.destinations || []).map((destination) => `
    <article class="destination-card">
      <div class="row-head">
        <div class="card-topline">
          <span class="card-icon">${escapeHtml(destination.icon || '•')}</span>
          <strong>${escapeHtml(destination.name || 'Destination')}</strong>
        </div>
        <span class="pill ${destination.active ? 'success' : 'warning'}">${escapeHtml(destination.status || (destination.active ? 'Active' : 'Inactive'))}</span>
      </div>
      <p>${escapeHtml(destination.detail || '')}</p>
      ${destination.action === 'request' ? `<button class="secondary" type="button" data-request-destination="${escapeHtml(destination.id || '')}" data-request-destination-name="${escapeHtml(destination.name || '')}">${escapeHtml(destination.button || 'Request')}</button>` : `<span class="pill success">${escapeHtml(destination.button || 'Active')}</span>`}
    </article>
  `).join('');

  $('#routerPreview').innerHTML = (data.routers || []).length ? (data.routers || []).map((router) => `
    <article class="router-card">
      <div class="row-head">
        <strong>${escapeHtml(router.name || 'Router')}</strong>
        <span class="pill warning">${escapeHtml(router.status || 'Preview only')}</span>
      </div>
      <small>${escapeHtml(router.detail || '')}</small>
    </article>
  `).join('') : emptyState('No router previews yet.');

  const requested = data.requested_destinations || [];
  $('#requestedDestinations').innerHTML = requested.length ? requested.map((entry) => `
    <article class="request-item">
      <strong>${escapeHtml(entry.name || entry.id || 'Destination')}</strong>
      <small>Requested ${escapeHtml(entry.requested_at || 'recently')}</small>
    </article>
  `).join('') : emptyState('No destination requests yet.');
}

function renderSignalRow(signal, activeOnly) {
  const active = signal.id === appState.selectedSignalId;
  const reviewState = signal.company_changes?.length ? 'Applied' : (signal.review_decision?.action === 'decline' ? 'Declined' : 'Needs review');
  return `
    <article class="signal-row ${active && !activeOnly ? 'active' : ''}" data-signal-id="${escapeHtml(signal.id || '')}">
      <div class="row-head">
        <strong>${escapeHtml(signal.title || 'Signal')}</strong>
        <small>${escapeHtml(reviewState)} · ${escapeHtml((signal.lenses || []).length ? `${signal.lenses.length} lenses` : 'No lenses')}</small>
      </div>
      <p>${escapeHtml(signal.quote || '')}</p>
      <small>${escapeHtml((signal.routes || []).join(', ') || 'No routes recorded')}</small>
    </article>
  `;
}


function reviewStatusLabel(status) {
  const labels = {
    review_pending: 'Needs review',
    company_brain_updated: 'Applied',
    declined: 'Declined',
    preview_only: 'Preview only'
  };
  return labels[status] || String(status || 'Needs review').replaceAll('_', ' ');
}

function reviewStatusClass(status) {
  if (status === 'company_brain_updated') return 'success';
  if (status === 'declined') return 'danger';
  return 'warning';
}

function renderDiffFields(fields) {
  return (fields || []).map((field) => `
    <div class="diff-field">
      <strong>${escapeHtml(field.field || 'field')}</strong>
      <div class="diff-values">
        <span><em>Before</em>${escapeHtml(field.before ?? 'Not set')}</span>
        <span><em>After</em>${escapeHtml(field.after ?? 'Not set')}</span>
      </div>
    </div>
  `).join('');
}

function feedbackButtonClass(actionId) {
  if (actionId === 'approve') return 'primary';
  if (actionId === 'decline') return 'secondary danger-button';
  return 'secondary';
}

function renderSignals() {
  const data = appState.data;
  const signals = data.signals || [];
  $('#signalList').innerHTML = signals.length ? signals.map((signal) => renderSignalRow(signal, false)).join('') : emptyState('No signals yet. Submit a manual signal to populate the audit view.');

  const selected = signals.find((signal) => signal.id === appState.selectedSignalId) || signals[0];
  if (!selected) {
    $('#signalSummary').innerHTML = emptyState('Select a signal to inspect its findings and routes.');
    $('#signalDetail').innerHTML = '';
    $('#feedbackActions').innerHTML = '';
    $('#auditFeed').innerHTML = (data.audit || []).map(renderAuditRow).join('');
    return;
  }

  const detail = appState.selectedSignalDetail || buildFallbackDetail(selected);
  const firedLenses = (detail.lens_findings || []).filter((item) => item.fired !== false && !item.skipped);
  const routeProposals = detail.route_proposals || [];
  const companyChanges = detail.context_update?.company_changes || [];
  const updateLogs = detail.context_update?.update_logs || [];
  const feedbackHistory = detail.feedback_history || [];
  const provenance = detail.context_update?.provenance_chain || {};
  const reviewStatus = detail.context_update?.status || 'review_pending';
  const reviewDecision = detail.review_decision || selected.review_decision || null;
  const reviewDiff = detail.context_update?.review_diff?.diff || [];
  const inputBody = detail.input?.body || selected.quote || '';

  $('#signalSummary').innerHTML = `
    <section class="review-workbench">
      <div class="review-hero">
        <div>
          <p class="section-label">Signal review</p>
          <h2>${escapeHtml(selected.title || 'Signal')}</h2>
          <p>${escapeHtml(selected.quote || '')}</p>
        </div>
        <span class="pill ${reviewStatusClass(reviewStatus)}">${escapeHtml(reviewStatusLabel(reviewStatus))}</span>
      </div>
      <div class="review-meta-grid">
        <div><span>Source</span><strong>${escapeHtml(selected.source_name || detail.input?.source || 'Manual signal')}</strong></div>
        <div><span>Lenses fired</span><strong>${escapeHtml(String(firedLenses.length))}</strong></div>
        <div><span>Routes proposed</span><strong>${escapeHtml(String(routeProposals.length))}</strong></div>
        <div><span>Signal id</span><strong>${escapeHtml(selected.id || 'Unknown')}</strong></div>
      </div>
    </section>
  `;

  $('#signalDetail').innerHTML = `
    <div class="review-layout">
      <section class="review-main">
        <article class="review-panel">
          <div class="card-head">
            <h3>Original signal</h3>
            <span class="muted">What Lettuce received</span>
          </div>
          <pre class="signal-body">${escapeHtml(inputBody || 'No body recorded.')}</pre>
        </article>

        <article class="review-panel">
          <div class="card-head">
            <h3>Lens findings</h3>
            <span class="muted">Why this matters</span>
          </div>
          <div class="finding-list">
            ${firedLenses.length ? firedLenses.map((item) => `
              <div class="finding-card">
                <div class="row-head">
                  <strong>${escapeHtml(item.lens || 'Lens')}</strong>
                  <span class="pill">${escapeHtml(item.runner || 'runner')}</span>
                </div>
                <p>${escapeHtml(item.finding || 'No finding text')}</p>
                ${item.operator_implication ? `<small>${escapeHtml(item.operator_implication)}</small>` : ''}
              </div>
            `).join('') : emptyState('No fired lenses recorded yet.')}
          </div>
        </article>

        <article class="review-panel">
          <div class="card-head">
            <h3>Route proposals</h3>
            <span class="muted">Where updates would go</span>
          </div>
          <div class="route-list">
            ${routeProposals.length ? routeProposals.map((route) => `
              <div class="route-card">
                <strong>${escapeHtml(route.path || 'Route')}</strong>
                <p>${escapeHtml(route.preview || route.action || 'Review required before apply.')}</p>
                <small>${route.requires_approval ? 'Requires review' : 'No review required'}</small>
              </div>
            `).join('') : emptyState('No route proposals recorded yet.')}
          </div>
        </article>
      </section>

      <aside class="review-side">
        <article class="review-panel decision-panel">
          <div class="card-head">
            <h3>Decision</h3>
            <span class="pill ${reviewStatusClass(reviewStatus)}">${escapeHtml(reviewStatusLabel(reviewStatus))}</span>
          </div>
          <p>${escapeHtml(detail.context_update?.result || '')}</p>
          ${reviewDecision ? `<div class="decision-note"><strong>${escapeHtml(reviewDecision.action || 'review')}</strong><span>${escapeHtml(reviewDecision.note || 'No note')}</span></div>` : '<p class="muted">Approve to apply the proposed Company Brain update, edit to apply with a note, or decline to record why it should not update context.</p>'}
        </article>

        <article class="review-panel">
          <h3>Company Brain changes</h3>
          <div class="change-list">
            ${companyChanges.length ? companyChanges.map((change) => `
              <div class="change-card">
                <strong>${escapeHtml(change.label || change.area || 'Change')}</strong>
                <p>${escapeHtml(change.detail || '')}</p>
                <small>${escapeHtml([change.area, change.object_id].filter(Boolean).join(' · '))}</small>
              </div>
            `).join('') : emptyState('No Company Brain changes applied yet.')}
          </div>
        </article>

        <article class="review-panel">
          <h3>Before / after diff</h3>
          <div class="diff-list">
            ${reviewDiff.length ? reviewDiff.map((item) => `
              <div class="diff-card">
                <strong>${escapeHtml(item.object || 'Object')}</strong>
                ${renderDiffFields(item.fields)}
              </div>
            `).join('') : emptyState('No applied diff yet.')}
          </div>
        </article>

        <article class="review-panel compact-panel">
          <h3>Provenance</h3>
          <ul>
            <li>${escapeHtml(provenance.raw_signal_path || 'Raw signal path unavailable')}</li>
            <li>${escapeHtml((provenance.route_paths || []).join(', ') || 'No route paths recorded')}</li>
            <li>${escapeHtml((provenance.updated_objects || []).join(', ') || 'No updated objects recorded')}</li>
          </ul>
        </article>

        <article class="review-panel compact-panel">
          <h3>Feedback history</h3>
          <ul>${feedbackHistory.length ? feedbackHistory.map((entry) => `<li>${escapeHtml(entry.action || 'feedback')}: ${escapeHtml(entry.note || 'No note')}</li>`).join('') : '<li>No feedback captured yet.</li>'}</ul>
        </article>
      </aside>
    </div>
  `;

  $('#feedbackActions').innerHTML = (data.feedback_actions || []).map((action) => `
    <button class="${feedbackButtonClass(action.id)}" type="button" data-feedback-action="${escapeHtml(action.id || '')}">${escapeHtml(action.label || action.id || 'Action')}</button>
  `).join('');

  $('#auditFeed').innerHTML = (data.audit || []).length ? (data.audit || []).map(renderAuditRow).join('') : emptyState('No audit events yet.');
}

function renderAuditRow(entry) {
  return `
    <article class="audit-row">
      <div class="row-head">
        <strong>${escapeHtml(entry.title || 'Event')}</strong>
        <small>${escapeHtml(entry.time || 'recently')}</small>
      </div>
      <p>${escapeHtml(entry.body || '')}</p>
    </article>
  `;
}

function renderSettings() {
  const data = appState.data;
  $('#previewToken').value = appState.previewToken;
  setStatus('previewTokenStatus', appState.previewToken ? 'Token is stored in this browser and sent only on write requests.' : 'Writes stay locked until you save the preview token here.');
  $('#runtimeStatus').innerHTML = `
    <div class="runtime-grid">
      <article class="summary-block">
        <h3>Connection</h3>
        <p>${escapeHtml(appState.apiOnline ? 'Connected to local runtime' : 'Using embedded fallback state')}</p>
        <small>${escapeHtml(appState.apiOnline ? 'GET views are live. Writes still require the preview token.' : 'Start the Python runtime to enable live reads and writes.')}</small>
      </article>
      <article class="summary-block">
        <h3>Workspace</h3>
        <p>${escapeHtml((data.organization || {}).name || 'No workspace')}</p>
        <small>${escapeHtml((data.organization || {}).setup_stage || 'No setup stage')}</small>
      </article>
      <article class="summary-block">
        <h3>Signal count</h3>
        <p>${escapeHtml(String((data.signals || []).length))}</p>
        <small>Recent signals in local state</small>
      </article>
      <article class="summary-block">
        <h3>Pending requests</h3>
        <p>${escapeHtml(String((data.requested_connectors || []).length + (data.requested_destinations || []).length))}</p>
        <small>Connectors and destinations</small>
      </article>
    </div>
  `;
}

function emptyState(message) {
  return `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function findLensById(lensId) {
  return (appState.data.lenses || []).find((lens) => lens.id === lensId);
}

function resetLensForm() {
  $('#customLensId').value = '';
  $('#customLensName').value = '';
  $('#customLensBody').value = '';
  $('#customLensTags').value = '';
  setStatus('customLensStatus', '');
}

function fillLensForm(lens) {
  $('#customLensId').value = lens.id || '';
  $('#customLensName').value = lens.name || '';
  $('#customLensBody').value = lens.body || '';
  $('#customLensTags').value = (lens.tags || []).join(', ');
  setStatus('customLensStatus', `Editing ${lens.name}. Save to update this custom lens.`);
}

function goToView(view) {
  const next = normalizeView(view) || preferredView(appState.data);
  appState.view = next;
  history.replaceState(null, '', `#${next}`);
  renderChrome();
}

async function handleWrite(action) {
  try {
    await action();
    await refreshData();
  } catch (error) {
    const hint = error?.data?.hint ? ` ${error.data.hint}` : '';
    showNotice(`${error.message || 'Write failed.'}${hint}`, 'danger');
    throw error;
  }
}

document.addEventListener('click', async (event) => {
  const target = event.target.closest('[data-source-action], [data-request-connector], [data-request-destination], [data-edit-lens-id], [data-signal-id], [data-feedback-action], #refreshButton, #clearPreviewToken, #resetLensForm');
  if (!target) return;

  if (target.id === 'refreshButton') {
    await refreshData({ notice: 'Local state refreshed.' });
    return;
  }

  if (target.id === 'clearPreviewToken') {
    appState.previewToken = '';
    saveStoredToken('');
    renderChrome();
    renderSettings();
    showNotice('Preview token cleared from this browser.', 'info');
    return;
  }

  if (target.id === 'resetLensForm') {
    resetLensForm();
    return;
  }

  const sourceAction = target.getAttribute('data-source-action');
  if (sourceAction === 'manual') {
    goToView('sources');
    $('#manualPasteCard')?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    $('#manualBody')?.focus();
    return;
  }
  const connectorName = target.getAttribute('data-request-connector');
  if (connectorName) {
    await handleWrite(async () => {
      await postJson('/api/request-connector', { name: connectorName });
    });
    goToView('sources');
    showNotice(`${connectorName} saved to the connector request queue.`, 'info');
    return;
  }

  const destinationId = target.getAttribute('data-request-destination');
  if (destinationId) {
    await handleWrite(async () => {
      await postJson('/api/request-destination', {
        id: destinationId,
        name: target.getAttribute('data-request-destination-name') || destinationId
      });
    });
    goToView('destinations');
    showNotice('Destination request saved locally.', 'info');
    return;
  }

  const lensId = target.getAttribute('data-edit-lens-id');
  if (lensId) {
    const lens = findLensById(lensId);
    if (lens) {
      goToView('lenses');
      fillLensForm(lens);
      $('#customLensName')?.focus();
    }
    return;
  }

  const signalId = target.getAttribute('data-signal-id');
  if (signalId) {
    appState.selectedSignalId = signalId;
    await ensureSelectedSignalDetail();
    renderSignals();
    return;
  }

  const feedbackAction = target.getAttribute('data-feedback-action');
  if (feedbackAction) {
    const note = $('#feedbackNote')?.value || '';
    await handleWrite(async () => {
      await postJson('/api/feedback', {
        action: feedbackAction,
        signal_id: appState.selectedSignalId,
        note
      });
    });
    $('#feedbackNote').value = '';
    goToView('signals');
    showNotice(`Feedback saved: ${feedbackAction}.`, 'info');
  }
});

window.addEventListener('hashchange', () => {
  appState.view = normalizeView(window.location.hash.slice(1)) || preferredView(appState.data);
  renderChrome();
});

$('#orgForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setStatus('orgStatusMessage', 'Saving workspace…');
  const name = ($('#orgName')?.value || '').trim();
  const orgId = $('#orgSelect')?.value || '';
  try {
    await handleWrite(async () => {
      await postJson('/api/org', name ? { name } : { org_id: orgId });
    });
    $('#orgName').value = '';
    setStatus('orgStatusMessage', 'Workspace saved locally.');
    showNotice('Workspace updated.', 'info');
  } catch {
    setStatus('orgStatusMessage', '');
  }
});

$('#userForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setStatus('userStatusMessage', 'Saving user profile…');
  try {
    await handleWrite(async () => {
      await postJson('/api/user', {
        name: ($('#userName')?.value || '').trim(),
        email: ($('#userEmail')?.value || '').trim(),
        role: ($('#userRole')?.value || '').trim()
      });
    });
    setStatus('userStatusMessage', 'User profile saved locally.');
    showNotice('User profile updated.', 'info');
  } catch {
    setStatus('userStatusMessage', '');
  }
});

$('#brainSetupForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setStatus('brainSetupStatus', 'Saving company brain…');
  try {
    await handleWrite(async () => {
      await postJson('/api/brain-setup', {
        summary: $('#brainSummary')?.value || '',
        positioning: $('#brainPositioning')?.value || '',
        stage: $('#brainStage')?.value || ''
      });
    });
    setStatus('brainSetupStatus', 'Company brain saved locally.');
    showNotice('Company brain setup updated.', 'info');
  } catch {
    setStatus('brainSetupStatus', '');
  }
});

$('#sourceForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setStatus('sourceStatus', 'Saving source…');
  try {
    await handleWrite(async () => {
      await postJson('/api/sources', {
        name: ($('#sourceName')?.value || '').trim(),
        kind: $('#sourceKind')?.value || 'manual',
        detail: ($('#sourceDetail')?.value || '').trim()
      });
    });
    $('#sourceName').value = '';
    $('#sourceDetail').value = '';
    setStatus('sourceStatus', 'Source saved locally.');
    showNotice('Source configuration saved.', 'info');
  } catch {
    setStatus('sourceStatus', '');
  }
});

$('#manualSignalForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setStatus('manualStatus', 'Processing signal…');
  try {
    await handleWrite(async () => {
      await postJson('/api/manual-signal', {
        title: $('#manualTitle')?.value || '',
        body: $('#manualBody')?.value || ''
      });
    });
    $('#manualTitle').value = '';
    $('#manualBody').value = '';
    setStatus('manualStatus', 'Signal processed. Review it in Signals / Audit.');
    goToView('signals');
    showNotice('Manual signal processed into the local runtime.', 'info');
  } catch {
    setStatus('manualStatus', '');
  }
});

$('#customLensForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setStatus('customLensStatus', 'Saving custom lens…');
  try {
    await handleWrite(async () => {
      await postJson('/api/lenses/custom', {
        id: $('#customLensId')?.value || '',
        name: $('#customLensName')?.value || '',
        body: $('#customLensBody')?.value || '',
        tags: $('#customLensTags')?.value || ''
      });
    });
    setStatus('customLensStatus', 'Custom lens saved locally.');
    resetLensForm();
    showNotice('Custom lens saved.', 'info');
  } catch {
    setStatus('customLensStatus', '');
  }
});

$('#destinationForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  setStatus('destinationStatus', 'Saving destination…');
  try {
    await handleWrite(async () => {
      await postJson('/api/destinations', {
        name: ($('#destinationName')?.value || '').trim(),
        kind: $('#destinationKind')?.value || 'company-brain',
        detail: ($('#destinationDetail')?.value || '').trim()
      });
    });
    $('#destinationName').value = '';
    $('#destinationDetail').value = '';
    setStatus('destinationStatus', 'Destination saved locally.');
    showNotice('Destination configuration saved.', 'info');
  } catch {
    setStatus('destinationStatus', '');
  }
});

$('#previewTokenForm')?.addEventListener('submit', (event) => {
  event.preventDefault();
  const token = ($('#previewToken')?.value || '').trim();
  appState.previewToken = token;
  saveStoredToken(token);
  renderChrome();
  renderSettings();
  showNotice(token ? 'Preview token saved in this browser.' : 'Preview token cleared.', 'info');
});

refreshData();
