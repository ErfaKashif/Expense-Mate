/* ============================================================
   ExpenseMate — Client-side controller (the "Client" in client-server)
   Includes FULL multi-currency support: base-currency switching,
   converted analytics, a quick converter and an exchange-rate table.
   ============================================================ */
let state = { uid: null, month: defaultMonth(), base: 'USD', symbol: '$', currencies: [] };
let pieChart = null, lineChart = null;

function defaultMonth() { return new Date().toISOString().slice(0, 7); }
function hdr() { return { 'Content-Type': 'application/json', 'X-User-Id': state.uid }; }
function setMsg(el, text, ok) {
  el.textContent = text;
  el.className = 'msg ' + (ok === undefined ? '' : (ok ? 'ok' : 'err'));
}
/* format money in the user's BASE currency (multi-currency aware) */
function fmt(n) {
  return state.symbol + (+n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
/* format money in an arbitrary (native) currency */
function fmtCcy(n, code, symbol) {
  const s = symbol || code || '';
  return s + (+n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function $(id) { return document.getElementById(id); }

/* ---------- auth ---------- */
async function register() {
  const msg = $('authMsg');
  const r = await fetch('/api/register', { method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ username: $('user').value, password: $('pass').value,
                           base_currency: $('regCur').value }) });
  if (r.ok) { setMsg(msg, 'Registered — please log in.', true); }
  else { const d = await r.json().catch(()=>({})); setMsg(msg, d.error || 'Registration failed.', false); }
}
async function login() {
  const msg = $('authMsg');
  const r = await fetch('/api/login', { method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({ username: $('user').value, password: $('pass').value }) });
  const d = await r.json();
  if (!r.ok) { setMsg(msg, d.error || 'Invalid credentials.', false); return; }
  state.uid = d.user_id;
  state.base = d.base_currency || 'USD';
  state.symbol = d.base_symbol || '$';
  $('whoLabel').textContent = 'Hi, ' + d.username;
  $('auth').classList.add('hidden');
  $('app').classList.remove('hidden');
  await loadCurrencies();
  populateMonths();
  bindNav();
  refresh();
}
function logout() {
  state.uid = null;
  $('app').classList.add('hidden');
  $('auth').classList.remove('hidden');
}

/* ---------- MULTI-CURRENCY: rates, selectors, converter ---------- */
async function loadCurrencies() {
  const r = await fetch(`/api/currencies?uid=${state.uid || ''}`);
  const d = await r.json();
  state.currencies = d.currencies;
  state.base = d.base_currency || state.base;
  state.symbol = d.base_symbol || state.symbol;

  fillSelect($('txCur'), d.currencies, d.base_currency);
  fillSelect($('baseCurSel'), d.currencies, d.base_currency);
  fillSelect($('convFrom'), d.currencies, 'USD');
  fillSelect($('convTo'), d.currencies, d.base_currency);
  if ($('regCur')) fillSelect($('regCur'), d.currencies, 'USD');

  $('baseChip').textContent = state.symbol + ' ' + state.base;
  $('ratesBaseLabel').textContent = 'vs ' + state.base;
  renderRates(d.table, d.base_currency);
  doConvert();
}
function fillSelect(sel, list, selected) {
  if (!sel) return;
  sel.innerHTML = '';
  list.forEach(c => {
    const o = document.createElement('option');
    o.value = c; o.textContent = c;
    sel.appendChild(o);
  });
  if (selected && list.includes(selected)) sel.value = selected;
}
async function saveBaseCurrency() {
  const code = $('baseCurSel').value;
  const r = await fetch('/api/settings/base_currency', { method: 'POST', headers: hdr(),
    body: JSON.stringify({ base_currency: code }) });
  const d = await r.json();
  if (!r.ok) { setMsg($('baseMsg'), d.error || 'Could not change currency.', false); return; }
  state.base = d.base_currency; state.symbol = d.base_symbol;
  setMsg($('baseMsg'), `Base currency is now ${state.base} — everything re-converted ✓`, true);
  await loadCurrencies();
  refresh();                       // re-fetch summary -> charts/cards/budgets in new currency
}
async function doConvert() {
  const body = { amount: $('convAmt').value || 0, from: $('convFrom').value, to: $('convTo').value };
  const r = await fetch('/api/convert', { method: 'POST',
    headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) });
  const d = await r.json();
  $('convResult').innerHTML = r.ok
    ? `${d.from_symbol}${(+d.amount).toLocaleString()} ${d.from} &nbsp;=&nbsp; <strong>${d.to_symbol}${(+d.result).toLocaleString(undefined,{maximumFractionDigits:4})} ${d.to}</strong>`
    : '—';
}
function renderRates(table, base) {
  const tb = $('ratesTable');
  tb.innerHTML = table.map(x => `
    <tr${x.code === base ? ' class="base-row"' : ''}>
      <td><strong>${x.code}</strong></td><td>${x.name}</td>
      <td>${x.symbol}${x.per_base}</td><td>${x.symbol}${x.one_base_equals.toLocaleString()}</td>
    </tr>`).join('');
}
function renderByCurrency(byCcy) {
  const box = $('byCurrencyBox');
  const keys = Object.keys(byCcy || {});
  if (!keys.length) { box.innerHTML = '<div class="none">No transactions this month.</div>'; return; }
  box.innerHTML = keys.map(c => {
    const v = byCcy[c];
    return `<div class="ccy-card">
        <div class="ccy-head"><span class="ccy-code">${v.symbol} ${c}</span>
          <span class="ccy-count">${v.count} tx</span></div>
        <div class="ccy-line">Income <strong class="am-pos">${fmtCcy(v.income, c, v.symbol)}</strong></div>
        <div class="ccy-line">Expense <strong class="am-neg">${fmtCcy(v.expense, c, v.symbol)}</strong></div>
      </div>`;
  }).join('');
}

/* ---------- months ---------- */
function populateMonths() {
  const sel = $('monthSel');
  sel.innerHTML = '';
  for (let i = 0; i < 8; i++) {
    const d = new Date(); d.setMonth(d.getMonth() - i);
    const m = d.toISOString().slice(0, 7);
    const o = document.createElement('option'); o.value = m; o.textContent = m; sel.appendChild(o);
  }
  sel.value = state.month;
  sel.onchange = () => { state.month = sel.value; refresh(); };
}

/* ---------- NAVIGATION BAR: click -> slide-down + smooth scroll ---------- */
function bindNav() {
  document.querySelectorAll('.nav-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = $(link.getAttribute('data-target'));
      if (!target) return;
      document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
      link.classList.add('active');
      target.classList.remove('slide-section');
      void target.offsetWidth;                       // force reflow to restart animation
      target.classList.add('slide-section');
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
}

/* ---------- refresh dashboard ---------- */
async function refresh() {
  const r = await fetch(`/api/summary?month=${state.month}`, { headers: hdr() });
  const d = await r.json();
  state.base = d.base_currency || state.base;
  state.symbol = d.base_symbol || state.symbol;
  $('baseChip').textContent = state.symbol + ' ' + state.base;
  $('dashCurrencyNote').textContent =
    d.foreign_count ? `All amounts shown in ${state.base} (${d.foreign_count} foreign-currency record(s) converted)`
                    : `Reporting in ${state.base}`;

  $('cIncome').textContent = fmt(d.total_income);
  $('cExpense').textContent = fmt(d.total_expense);
  $('cBalance').textContent = fmt(d.balance);
  $('cAlerts').textContent = d.budget.alerts.length;

  renderAlerts(d.budget.alerts);
  renderBudgetsDetail(d.budget.status);
  renderCostBudgets(d.budget.status);
  renderByCurrency(d.by_currency);
  drawPie(d.by_category);
  drawTrend(d.trend);
  loadTransactions();
  populateBudgetCats();
}

function renderAlerts(alerts) {
  const box = $('alertBox');
  box.innerHTML = '<h3>Budget Alerts</h3>';
  if (!alerts.length) { box.innerHTML += '<div class="none">✅ No budget alerts — you are on track!</div>'; return; }
  alerts.forEach(a => { box.innerHTML += `<div class="alert ${a.level}">${a.message}</div>`; });
}

/* Budget bars in the "Add" panel */
function renderCostBudgets(status) {
  const box = $('budgetList');
  box.innerHTML = '';
  if (!status.length) { box.innerHTML = '<div class="none">No budgets set for this month.</div>'; return; }
  status.forEach(b => {
    box.innerHTML += `
      <div class="bg-item">
        <span class="bg-name">${b.category}</span>
        <div class="bg-bar"><div class="bg-fill ${b.level}" style="width:${Math.min(b.ratio*100,100)}%"></div></div>
        <span class="bg-nums">${fmt(b.spent)} / ${fmt(b.limit)}</span>
      </div>`;
  });
}

/* Dedicated "Budgets & Alerts" panel */
function renderBudgetsDetail(status) {
  const box = $('budgetsDetail');
  if (!status.length) { box.innerHTML = '<div class="none">No budgets set for this month yet.</div>'; return; }
  box.innerHTML = status.map(b => {
    const rem = b.remaining >= 0
      ? `<span class="ok">Remaining: ${fmt(b.remaining)}</span>`
      : `<span class="bad">Over by: ${fmt(-b.remaining)}</span>`;
    const conv = b.converted
      ? `<div class="budget-meta">budget set in ${b.budget_currency}
           (${fmtCcy(b.budget_amount_native, b.budget_currency)} → converted to ${b.currency})</div>`
      : '';
    return `<div class="budget-row">
        <div class="budget-top"><strong>${b.category}</strong> ${rem}</div>
        <div class="bg-bar"><div class="bg-fill ${b.level}" style="width:${Math.min(b.ratio*100,100)}%"></div></div>
        <div class="budget-meta">spent ${fmt(b.spent)} of ${fmt(b.limit)} · ${Math.round(b.ratio*100)}%</div>
        ${conv}
      </div>`;
  }).join('');
}

/* ---------- charts (Chart.js, served locally) ---------- */
function drawPie(byCat) {
  const keys = Object.keys(byCat || {});
  const empty = $('pieEmpty'), canvas = $('pieChart');
  if (!keys.length) {
    if (pieChart) { pieChart.destroy(); pieChart = null; }
    canvas.style.display = 'none'; empty.classList.remove('hidden'); return;
  }
  canvas.style.display = ''; empty.classList.add('hidden');
  if (pieChart) pieChart.destroy();
  pieChart = new Chart(canvas, {
    type: 'doughnut',
    data: { labels: keys, datasets: [{ data: keys.map(k => byCat[k]), backgroundColor: palette(keys.length) }] },
    options: { maintainAspectRatio: false, responsive: true,
      plugins: {
        legend: { position: 'right', labels: { color: '#5b6b8c', boxWidth: 12, font: {size:11} } },
        tooltip: { callbacks: { label: c => ` ${c.label}: ${fmt(c.parsed)}` } }
      } }
  });
}
function drawTrend(trend) {
  const labels = (trend || []).map(t => t[0]);
  const empty = $('lineEmpty'), canvas = $('lineChart');
  if (!labels.length) {
    if (lineChart) { lineChart.destroy(); lineChart = null; }
    canvas.style.display = 'none'; empty.classList.remove('hidden'); return;
  }
  canvas.style.display = ''; empty.classList.add('hidden');
  if (lineChart) lineChart.destroy();
  lineChart = new Chart(canvas, {
    type: 'line',
    data: { labels, datasets: [
      { label: 'Income', data: trend.map(t => t[1]), borderColor: '#6fae8f',
        backgroundColor: 'rgba(111,174,143,.15)', tension: .3, fill: true, pointRadius: 3 },
      { label: 'Expense', data: trend.map(t => t[2]), borderColor: '#7a9bd0',
        backgroundColor: 'rgba(122,155,208,.12)', tension: .3, fill: true, pointRadius: 3 } ]},
    options: { maintainAspectRatio: false, responsive: true,
      plugins: { legend: { labels: { color: '#5b6b8c', boxWidth: 12, font: {size:11} } },
        tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ${fmt(c.parsed.y)}` } } },
      scales: { x: { ticks: { color: '#7c8aa5' }, grid: { color: '#e7ecf5' } },
                y: { ticks: { color: '#7c8aa5', callback: v => state.symbol + v }, grid: { color: '#e7ecf5' } } } }
  });
}
function palette(n) {
  const c = ['#7a9bd0','#6fae8f','#f2c07a','#e28ba6','#8fa3c9','#9bc6b0','#d9c2a0','#a6b3d6'];
  return Array.from({length:n}, (_,i) => c[i % c.length]);
}

/* ---------- transactions ---------- */
async function addTx() {
  const msg = $('txMsg');
  const body = { date: $('txDate').value || new Date().toISOString().slice(0,10),
    description: $('txDesc').value, amount: $('txAmt').value, type: $('txType').value,
    category: $('txCat').value, currency: $('txCur').value };
  const r = await fetch('/api/transactions', { method: 'POST', headers: hdr(), body: JSON.stringify(body) });
  if (!r.ok) { const d = await r.json().catch(()=>({})); setMsg(msg, d.error || 'Error adding.', false); return; }
  setMsg(msg, `Added ✓ — recorded in ${body.currency}, reported in ${state.base}.`, true);
  ['txDesc','txAmt','txCat'].forEach(id => $(id).value = '');
  refresh();
}
async function loadTransactions() {
  const r = await fetch(`/api/transactions?month=${state.month}`, { headers: hdr() });
  const rows = await r.json();
  $('txCount').textContent = rows.length + ' record(s) · amounts converted to ' + state.base;
  const tb = $('txTable');
  tb.innerHTML = rows.map(t => `
    <tr>
      <td>${t.date}</td>
      <td>${t.description}</td>
      <td class="${t.type==='income'?'am-pos':'am-neg'}">${t.type==='income'?'+':'\u2212'}${fmtCcy(t.amount, t.currency, t.currency_symbol)}</td>
      <td>${t.currency}${t.is_foreign ? ' <span class="fx" title="Converted from '+t.currency+'">⇄</span>' : ''}</td>
      <td class="${t.type==='income'?'am-pos':'am-neg'}">${fmtCcy(t.amount_base, state.base, state.symbol)}</td>
      <td>${t.type}</td>
      <td>${t.category_name || '—'}</td>
      <td class="del" onclick="delTx(${t.id})" title="Delete">✕</td>
    </tr>`).join('') ||
    `<tr><td colspan="8" style="color:var(--muted)">No transactions.</td></tr>`;
}
async function delTx(id) {
  await fetch('/api/transactions/' + id, { method: 'DELETE', headers: hdr() });
  refresh();
}

/* ---------- budgets ---------- */
async function setBudget() {
  const msg = $('bgMsg');
  const body = { category: $('bgCat').value, month: state.month,
                 amount: $('bgAmt').value, currency: $('bgCur').value || $('txCur').value };
  const r = await fetch('/api/budgets', { method: 'POST', headers: hdr(), body: JSON.stringify(body) });
  if (!r.ok) { const d = await r.json().catch(()=>({})); setMsg(msg, d.error || 'Error.', false); return; }
  setMsg(msg, `Budget set in ${body.currency} ✓`, true);
  $('bgAmt').value = '';
  refresh();
}
async function populateBudgetCats() {
  const r = await fetch('/api/summary?month=' + state.month, { headers: hdr() });
  const d = await r.json();
  const cats = Object.keys(d.by_category || {});
  const sel = $('bgCat');
  const prev = sel.value;
  sel.innerHTML = '';
  cats.concat(['Misc','Food','Rent','Transport','Shopping','Utilities'])
    .filter((v,i,a) => a.indexOf(v) === i)
    .forEach(c => { const o = document.createElement('option'); o.value = c; o.textContent = c; sel.appendChild(o); });
  if (prev) sel.value = prev;
  // keep the budget currency selector in sync with available currencies
  fillSelect($('bgCur'), state.currencies.length ? state.currencies : ['USD'], state.base);
}

/* ---------- csv ---------- */
async function exportCsv() {
  const a = document.createElement('a');
  a.href = `/api/export?month=${state.month}&uid=${state.uid}`;
  a.download = 'expensemate-' + state.month + '.csv';
  a.click();
  setMsg($('csvMsg'), `Exported ✓ (includes native currency + amount in ${state.base})`, true);
}
async function importCsv(ev) {
  const f = ev.target.files[0]; if (!f) return;
  const text = await f.text();
  const r = await fetch('/api/import', { method: 'POST', headers: hdr(), body: JSON.stringify({ csv: text }) });
  const d = await r.json();
  if (!r.ok) { setMsg($('csvMsg'), d.error || 'Import failed.', false); return; }
  setMsg($('csvMsg'), `Imported ${d.imported} rows ✓`, true);
  ev.target.value = '';
  refresh();
}

/* ---------- init (runs before login too, so the register form has currencies) ---------- */
(async function init() {
  $('txDate').value = new Date().toISOString().slice(0,10);
  await loadCurrencies();      // fills register currency + converter selects
})();
