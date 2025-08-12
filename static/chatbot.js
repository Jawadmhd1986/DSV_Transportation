// ---- Viewport fix (unchanged) ----
window.addEventListener('load', () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});
window.addEventListener('resize', () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});

document.addEventListener('DOMContentLoaded', () => {
  // ---------------- Chatbot (UNCHANGED UX & API) ----------------
  const chatBox    = document.getElementById('chat-box');
  const chatToggle = document.querySelector('.chat-toggle');
  const chatClose  = document.getElementById('chat-close');
  const sendBtn    = document.getElementById('chat-send');
  const inputEl    = document.getElementById('chat-input');
  const msgsEl     = document.getElementById('chat-messages');

  if (chatToggle && chatBox && chatClose && sendBtn && inputEl && msgsEl) {
    chatToggle.addEventListener('click', () => chatBox.classList.toggle('open'));
    chatClose.addEventListener('click', () => chatBox.classList.remove('open'));
    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;
    appendMessage('user', text);
    inputEl.value = '';

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      const reply = (data && data.reply) ? data.reply : '...';
      const hasHTML = /<[^>]+>/.test(reply);
      appendMessage('bot', reply, !hasHTML);
    } catch {
      appendMessage('bot', 'Sorry, something went wrong.');
    }
  }

  function appendMessage(sender, text, typewriter = false) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${sender}`;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    wrapper.appendChild(bubble);
    msgsEl.appendChild(wrapper);
    msgsEl.scrollTop = msgsEl.scrollHeight;

    if (!typewriter) {
      bubble.innerHTML = text;
    } else {
      let i = 0;
      (function typeChar(){
        if (i < text.length) {
          bubble.innerHTML += text.charAt(i++);
          msgsEl.scrollTop = msgsEl.scrollHeight;
          setTimeout(typeChar, 15);
        }
      })();
    }
  }

  // ---------------- Transport UI (One Way / Back Load) ----------------
  const tripRadios = document.querySelectorAll('input[name="trip_type"]');
  tripRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.trip-options label').forEach(l => l.classList.remove('selected'));
      const label = radio.closest('label');
      if (label) label.classList.add('selected');
    });
  });

  // Truck rows (use server-provided whitelist)
  const truckTypeContainer = document.getElementById('truckTypeContainer');
  const addTruckTypeBtn    = document.getElementById('add-truck-type');
  const TRUCK_TYPES        = (window.TRUCK_TYPES || []);

  function createTruckRow(){
    const row = document.createElement('div');
    row.className = 'truck-type-row';
    const options = ['<option value="">— Select Truck Type —</option>']
      .concat(TRUCK_TYPES.map(t => `<option value="${t}">${t}</option>`))
      .join('');

    row.innerHTML = `
      <div class="select-wrapper">
        <label class="inline-label">Type</label>
        <select name="truck_type[]" required>${options}</select>
      </div>
      <div class="qty-wrapper">
        <label class="inline-label">QTY</label>
        <input type="number" name="truck_qty[]" min="1" placeholder="Count" required />
      </div>
      <button type="button" class="btn-remove" title="Remove Truck Type">Clear</button>
    `;
    row.querySelector('.btn-remove').addEventListener('click', () => row.remove());
    return row;
  }

  // ---------------- CICPA filtering add-on ----------------
  const destSel = document.getElementById('destination');

  const CICPA_CITY_SET = new Set(
    (window.CICPA_CITIES || []).map(s =>
      (s || '').toString().trim().toLowerCase().replace(/\s+/g, ' ').replace(/[_–—]/g, '-')
    )
  );
  const LOCAL_TRUCKS = Array.isArray(window.LOCAL_TRUCKS) ? window.LOCAL_TRUCKS : [];
  const CICPA_TRUCKS = Array.isArray(window.CICPA_TRUCKS) ? window.CICPA_TRUCKS : [];
  const UNION_TRUCKS = Array.isArray(window.TRUCK_TYPES)  ? window.TRUCK_TYPES  : [];

  function normCity(s) {
    return (s || '').toString().trim().toLowerCase()
      .replace(/\s+/g, ' ')
      .replace(/[_–—]/g, '-');
  }

  function isCICPASelected() {
    if (!destSel || !destSel.value) return null; // no selection yet
    return CICPA_CITY_SET.has(normCity(destSel.value));
  }

  function allowedList() {
    const cicpa = isCICPASelected();
    if (cicpa === true)  return CICPA_TRUCKS;
    if (cicpa === false) return LOCAL_TRUCKS;
    return UNION_TRUCKS; // before a city is chosen
  }

  function optionsHTML(allowed, current) {
    const opts = ['<option value="">— Select Truck Type —</option>'];
    allowed.forEach(t => {
      const sel = (t === current) ? ' selected' : '';
      opts.push(`<option value="${t}"${sel}>${t}</option>`);
    });
    return opts.join('');
  }

  function applyFilterToRow(selectEl) {
    const allowed = allowedList();
    const prev = selectEl.value;
    const keep = allowed.includes(prev);
    selectEl.innerHTML = optionsHTML(allowed, keep ? prev : "");
  }

  function applyFilterToAllRows() {
    if (!truckTypeContainer) return;
    truckTypeContainer
      .querySelectorAll('select[name="truck_type[]"]')
      .forEach(applyFilterToRow);
  }

  // Add-row button — **fixed syntax (removed stray ')')**
  if (truckTypeContainer && addTruckTypeBtn) {
    addTruckTypeBtn.addEventListener('click', () => {
      truckTypeContainer.appendChild(createTruckRow());
      // ensure the new row respects current destination's CICPA status
      applyFilterToAllRows();
    });
    // initial row
    truckTypeContainer.appendChild(createTruckRow());
    // apply initial filter (in case a destination is preselected)
    applyFilterToAllRows();
  }

  if (destSel) {
    destSel.addEventListener('change', applyFilterToAllRows);
  }
});
