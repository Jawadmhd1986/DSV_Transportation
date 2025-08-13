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

  // ---------------- Transport UI ----------------

  // Main trip toggle (top of form)
  const tripRadios = document.querySelectorAll('input[name="trip_type"]');
  tripRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.trip-options label').forEach(l => l.classList.remove('selected'));
      const label = radio.closest('label');
      if (label) label.classList.add('selected');
      // keep first row (only) in sync with main trip
      normalizeFirstRowUI();
    });
  });

  function getGlobalTrip() {
    const checked = document.querySelector('input[name="trip_type"]:checked');
    return checked ? checked.value : 'one_way';
  }

  // CICPA filtering support (arrays injected by the template)
  const CICPA_CITIES = (window.CICPA_CITIES || []).map(s => (s || '').toLowerCase());
  const LOCAL_TRUCKS = window.LOCAL_TRUCKS || [];
  const CICPA_TRUCKS = window.CICPA_TRUCKS || [];

  function isCicpaCity(city) {
    return !!city && CICPA_CITIES.includes(String(city).toLowerCase().trim());
  }
  function truckListForCity(city) {
    return isCicpaCity(city) ? CICPA_TRUCKS : LOCAL_TRUCKS;
  }
  function buildOptions(list, current) {
    const opts = ['<option value="">— Select Truck Type —</option>']
      .concat(list.map(t => `<option value="${t}">${t}</option>`))
      .join('');
    // rebuild but keep current if still allowed
    const wrap = document.createElement('select');
    wrap.innerHTML = opts;
    if (current && list.includes(current)) wrap.value = current;
    return wrap.innerHTML;
  }

  const truckTypeContainer = document.getElementById('truckTypeContainer');
  const addTruckTypeBtn    = document.getElementById('add-truck-type');
  const destEl             = document.getElementById('destination');

  function currentCity() {
    return destEl ? destEl.value : '';
  }

  // === Row creation & first-row rules ===
  function createTruckRow(index /* 0-based */) {
    const row = document.createElement('div');
    row.className = 'truck-type-row';

    const allowed = truckListForCity(currentCity());
    const options = buildOptions(allowed, null);

    // Type / Qty / Clear
    row.innerHTML = `
      <div class="select-wrapper">
        <label class="inline-label">Type</label>
        <select name="truck_type[]" required>${options}</select>
      </div>

      <div class="qty-wrapper">
        <label class="inline-label">QTY</label>
        <input type="number" name="truck_qty[]" min="1" value="1" required />
      </div>

      <button type="button" class="btn-remove" title="Remove Truck Type">Clear</button>
    `;

    if (index === 0) {
      // First row follows the main trip (hidden input)
      const hidden = document.createElement('input');
      hidden.type  = 'hidden';
      hidden.name  = 'trip_kind[]';
      hidden.className = 'trip-kind-hidden';
      hidden.value = getGlobalTrip();
      row.appendChild(hidden);
    } else {
      // Additional rows get their own visible trip selector
      const tripBlock = document.createElement('div');
      tripBlock.className = 'select-wrapper';
      tripBlock.style.gridColumn = '1 / span 2';
      tripBlock.innerHTML = `
        <label class="inline-label">Trip (this row)</label>
        <select name="trip_kind[]" required>
          <option value="one_way">One Way</option>
          <option value="back_load">Back Load</option>
        </select>
      `;
      tripBlock.querySelector('select').value = getGlobalTrip();
      row.appendChild(tripBlock);
    }

    // Clear button
    row.querySelector('.btn-remove').addEventListener('click', () => {
      row.remove();
      normalizeFirstRowUI(); // ensure first row keeps hidden trip, others visible
    });

    return row;
  }

  function normalizeFirstRowUI() {
    const rows = [...truckTypeContainer.querySelectorAll('.truck-type-row')];
    rows.forEach((row, i) => {
      const selectTrip = row.querySelector('select[name="trip_kind[]"]');
      const hiddenTrip = row.querySelector('input.trip-kind-hidden[name="trip_kind[]"]');

      if (i === 0) {
        // Must be hidden + synced to main
        if (selectTrip) selectTrip.closest('.select-wrapper')?.remove();
        if (!hiddenTrip) {
          const hidden = document.createElement('input');
          hidden.type = 'hidden';
          hidden.name = 'trip_kind[]';
          hidden.className = 'trip-kind-hidden';
          row.appendChild(hidden);
        }
        const hiddenNow = row.querySelector('input.trip-kind-hidden[name="trip_kind[]"]');
        if (hiddenNow) hiddenNow.value = getGlobalTrip();
      } else {
        // Must be visible dropdown
        if (hiddenTrip) hiddenTrip.remove();
        if (!selectTrip) {
          const block = document.createElement('div');
          block.className = 'select-wrapper';
          block.style.gridColumn = '1 / span 2';
          block.innerHTML = `
            <label class="inline-label">Trip (this row)</label>
            <select name="trip_kind[]" required>
              <option value="one_way">One Way</option>
              <option value="back_load">Back Load</option>
            </select>
          `;
          block.querySelector('select').value = getGlobalTrip();
          row.appendChild(block);
        }
      }
    });
  }

  // Add-row button
  if (truckTypeContainer && addTruckTypeBtn) {
    addTruckTypeBtn.addEventListener('click', () => {
      const index = truckTypeContainer.querySelectorAll('.truck-type-row').length;
      const newRow = createTruckRow(index);
      truckTypeContainer.appendChild(newRow);
      normalizeFirstRowUI();
      // Focus the new row’s trip selector if it exists
      const tripSel = newRow.querySelector('select[name="trip_kind[]"]');
      if (tripSel) tripSel.focus();
    });

    // initial row (inherits main trip)
    truckTypeContainer.appendChild(createTruckRow(0));
  }

  // Re-filter truck types when destination changes
  if (destEl) {
    destEl.addEventListener('change', () => {
      const allowed = truckListForCity(currentCity());
      truckTypeContainer.querySelectorAll('.truck-type-row').forEach(row => {
        const typeSel = row.querySelector('select[name="truck_type[]"]');
        if (!typeSel) return;
        const cur = typeSel.value;
        typeSel.innerHTML = buildOptions(allowed, cur);
      });
    });
  }
});
