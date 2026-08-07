const trackedIds = new Set();

async function submitEnrich() {
  const payload = {
    email: document.getElementById('f-email').value.trim(),
    domain: document.getElementById('f-domain').value.trim(),
    name: document.getElementById('f-name').value.trim(),
    company: document.getElementById('f-company').value.trim(),
    linkedin: document.getElementById('f-linkedin').value.trim(),
  };

  if (!Object.values(payload).some(v => v)) {
    document.getElementById('form-msg').textContent = 'Fill in at least one field.';
    return;
  }

  document.getElementById('form-msg').textContent = 'Enriching...';
  const resp = await fetch('/api/enrich', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await resp.json();

  if (!resp.ok) {
    document.getElementById('form-msg').textContent = data.error || 'Something went wrong.';
    return;
  }

  document.getElementById('form-msg').textContent = '';
  ['f-email', 'f-domain', 'f-name', 'f-company', 'f-linkedin'].forEach(id => {
    document.getElementById(id).value = '';
  });

  trackedIds.add(data.id);
  renderResults();
  pollUntilDone(data.id);
}

async function pollUntilDone(id) {
  const poll = async () => {
    const lead = await (await fetch(`/api/leads/${id}`)).json();
    if (lead.enrichment_status === 'pending' || lead.enrichment_status === 'partial') {
      renderResults();
      setTimeout(poll, 1500);
    } else {
      renderResults();
    }
  };
  poll();
}

async function renderResults() {
  const leads = await (await fetch('/api/leads')).json();
  const body = document.getElementById('results-body');
  body.innerHTML = leads.slice(0, 20).map(l => `
    <tr>
      <td><a class="row-link" href="/lead/${l.id}">${l.company_name || l.input_domain || l.input_email || '—'}</a></td>
      <td>${l.contact_name || l.contact_email || '—'}</td>
      <td>${l.company_domain || l.input_domain || '—'}</td>
      <td><span class="status ${l.enrichment_status}">${l.enrichment_status}</span></td>
      <td><a class="row-link" href="/lead/${l.id}">View</a></td>
    </tr>
  `).join('') || '<tr><td colspan="5" class="muted">No leads yet - enrich one above.</td></tr>';
}

document.getElementById('enrich-btn').addEventListener('click', submitEnrich);
renderResults();
