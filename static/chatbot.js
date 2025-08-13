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
  const truckTypeContainer = document.getElementById('truckTypeContainer');
  const addTruckTypeBtn    = document.getElementById('add-truck-type');

  // Global trip toggle (top of form)
  const tripRadios = document.querySelectorAll('input[name="trip_type"]');
  tripRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.trip-options label').forEach(l => l.classList.remove('selected'));
      const label = radio.closest('label');
      if (label) label.classList.add('selected');
      // keep row-1 (first row) in sync with the main trip
      syncFirstRowHiddenTrip();
    });
  });

  function getGlobalTrip() {
    const checked = document.querySelector('input[name="trip_type"]:checked');
    return checked ? checked.value : 'one_way';
  }

  // CICPA filtering support (arrays injected by template in HTML)
  const CICPA_CITIES = (window.CICPA_CITIES || []).map(s => (s || '').toLowerCase());
  const LOCAL_TRUCKS = window.LOCAL_TRUCKS || [];
  const CICPA_TRUCKS = window.CICPA_TRUCKS || [];

  function isCicpaCity(city) {
    return !!city && CICPA_CITIES.includes((city || '').toLowerCase().trim());
  }
  function truckListForCity(city) {
    return isCicpaCity(city) ? CICPA_TRUCKS : LOCAL_TRUCKS;
  }

  function buildOptions(list, current) {
    const opts = ['<option value="">— Select Truck Type —</option>']
      .concat(list.map(t => `<option value="${t}">${t}</option>`))
      .join('');
    // if current still allowed, keep it selected
    const wrap = document.createElement('select');
    wrap.innerHTML = opts;
    if (current && list.includes(current)) wrap.value = current;
    return wrap.innerHTML;
  }

  function currentCity() {
    const d = document.getElementById('destination');
    return d ? d.value : '';
  }

  function createTruckRow(index /* 0-based */) {
    const row = document.createElement('div');
    row.className = 'truck-type-row';

    const allowed = truckListForCity(currentCity());
    const options = buildOptions(allowed, null);

    // Common part (type / qty / clear)
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

    // Trip control:
    //   - Row 0: hidden input only (inherits main trip)
    //   - Row 1+ : visible dropdown so user can choose
    if (index === 0) {
      const hidden = document.createElement('input');
      hidden.type  = 'hidden';
      hidden.name  = 'trip_kind[]';
      hidden.className = 'trip-kind-hidden';
      hidden.value = getGlobalTrip();
      row.appendChild(hidden);
    } else {
      const tripBlock = document.createElement('div');
      tripBlock.className = 'select-wrapper';
      tripBlock.style.gridColumn = '1 / span 2';
      tripBlock.innerHTML = `
        <label class="inline-label">Trip</label>
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
      normalizeFirstRowUI(); // ensure first row stays hidden-trip
    });

    return row;
  }

  // Ensure the first row has hidden trip (no visible dropdown).
  // If user deleted the first row, upgrade the new first row accordingly.
  function normalizeFirstRowUI() {
    const rows = [...truckTypeContainer.querySelectorAll('.truck-type-row')];
    rows.forEach((row, i) => {
      const existingSelect = row.querySelector('select[name="trip_kind[]"]');
      const existingHidden = row.querySelector('input.trip-kind-hidden[name="trip_kind[]"]');

      if (i === 0) {
        // must be hidden
        if (existingSelect) existingSelect.closest('.select-wrapper')?.remove();
        if (!existingHidden) {
          const hidden = document.createElement('input');
          hidden.type = 'hidden';
          hidden.name = 'trip_kind[]';
          hidden.className = 'trip-kind-hidden';
          hidden.value = getGlobalTrip();
          row.appendChild(hidden);
        } else {
          existingHidden.value = getGlobalTrip();
        }
      } else {
        // must be visible select
        if (existingHidden) existingHidden.remove();
        if (!existingSelect) {
          const tripBlock = document.createElement('div');
          tripBlock.className = 'select-wrapper';
          tripBlock.style.gridColumn = '1 / span 2';
          tripBlock.innerHTML = `
            <label class="inline-label">Trip</label>
            <select name="trip_kind[]" required>
              <option value="one_way">One Way</option>
              <option value="back_load">Back Load</option>
            </select>
          `;
          tripBlock.querySelector('select').value = getGlobalTrip();
          row.appendChild(tripBlock);
        }
      }
    });
  }

  function syncFirstRowHiddenTrip() {
    const first = truckTypeContainer.querySelector('.truck-type-row');
    if (!first) return;
    const hidden = first.querySelector('input.trip-kind-hidden[name="trip_kind[]"]');
    if (hidden) hidden.value = getGlobalTrip();
  }

  // Add-row button
  if (truckTypeContainer && addTruckTypeBtn) {
    addTruckTypeBtn.addEventListener('click', () => {
      const index = truckTypeContainer.querySelectorAll('.truck-type-row').length;
      truckTypeContainer.appendChild(createTruckRow(index));
      normalizeFirstRowUI();
    });
    // initial row: index 0
    truckTypeContainer.appendChild(createTruckRow(0));
  }

  // Re-filter truck type options when destination changes
  const destEl = document.getElementById('destination');
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
