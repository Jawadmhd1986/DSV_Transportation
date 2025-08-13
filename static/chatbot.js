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

  // Global Trip radios
  const tripRadios = document.querySelectorAll('input[name="trip_type"]');
  function getGlobalTrip() {
    const checked = document.querySelector('input[name="trip_type"]:checked');
    return checked ? checked.value : 'one_way';
  }

  // CICPA filtering (arrays provided by the template)
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

  // Create a truck row. `independentTrip` = true for rows >= 2; false for the first row.
  function createTruckRow(independentTrip) {
    const row = document.createElement('div');
    row.className = 'truck-type-row';
    const allowed = truckListForCity(currentCity());
    const options = buildOptions(allowed, null);

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

      <div class="select-wrapper" style="grid-column: 1 / span 2;">
        <label class="inline-label">Trip</label>
        <select name="trip_kind[]" required>
          <option value="one_way">One Way</option>
          <option value="back_load">Back Load</option>
        </select>
      </div>
    `;

    // Trip select
    const tripSel = row.querySelector('select[name="trip_kind[]"]');
    tripSel.value = getGlobalTrip();          // default from main radios
    tripSel.dataset.userSet = '0';
    tripSel.addEventListener('change', () => { tripSel.dataset.userSet = '1'; });

    // Remove handler
    row.querySelector('.btn-remove').addEventListener('click', () => {
      row.remove();
      applyFirstRowLock(); // keep the "first row inherits main trip" rule
    });

    // If this row is the first row (independentTrip=false), lock it right away.
    if (!independentTrip) {
      lockRowTripToGlobal(row);
    }

    return row;
  }

  // Lock a row's Trip to the main Trip Type:
  //  - disable the select (disabled elements aren't submitted)
  //  - mirror its value to a hidden input named trip_kind[] so the server receives it
  function lockRowTripToGlobal(row) {
    const sel = row.querySelector('select[name="trip_kind[]"]');
    if (!sel) return;
    sel.value = getGlobalTrip();
    sel.disabled = true;

    let hidden = row.querySelector('input.trip-hidden[name="trip_kind[]"]');
    if (!hidden) {
      hidden = document.createElement('input');
      hidden.type  = 'hidden';
      hidden.name  = 'trip_kind[]';
      hidden.className = 'trip-hidden';
      // append after the select so ordering stays first-row, then others
      sel.parentElement.appendChild(hidden);
    }
    hidden.value = sel.value;
  }

  // Unlock a row (make Trip independent) and remove any hidden mirror
  function unlockRowTrip(row) {
    const sel = row.querySelector('select[name="trip_kind[]"]');
    if (sel) {
      sel.disabled = false;
      if (sel.dataset.userSet !== '1') sel.value = getGlobalTrip();
    }
    const hidden = row.querySelector('input.trip-hidden[name="trip_kind[]"]');
    if (hidden) hidden.remove();
  }

  // Ensure the first visible row is locked to the main Trip; all others independent
  function applyFirstRowLock() {
    const rows = [...document.querySelectorAll('#truckTypeContainer .truck-type-row')];
    rows.forEach((row, idx) => {
      if (idx === 0) {
        lockRowTripToGlobal(row);
      } else {
        unlockRowTrip(row);
      }
    });
  }

  // Re-filter truck type options when destination changes
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

  // Add new rows (independent trip)
  if (truckTypeContainer && addTruckTypeBtn) {
    addTruckTypeBtn.addEventListener('click', () => {
      truckTypeContainer.appendChild(createTruckRow(true));
      applyFirstRowLock();
    });
    // initial row (locked to main trip)
    truckTypeContainer.appendChild(createTruckRow(false));
    applyFirstRowLock();
  }

  // When main Trip Type changes, update ONLY the first row (locked one)
  tripRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.trip-options label').forEach(l => l.classList.remove('selected'));
      const label = radio.closest('label');
      if (label) label.classList.add('selected');
      applyFirstRowLock(); // pushes new main value into the locked first row + hidden mirror
    });
  });
});
