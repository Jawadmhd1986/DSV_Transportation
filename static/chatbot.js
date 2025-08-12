// ───────────────────────────────────────────────────────────────────
// Viewport fix (mobile safe; harmless on desktop too)
// ───────────────────────────────────────────────────────────────────
function setVH() {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
}
window.addEventListener('load', setVH);
window.addEventListener('resize', setVH);

// ───────────────────────────────────────────────────────────────────
// Helpers
// ───────────────────────────────────────────────────────────────────
function normCity(s) {
  return (s || '')
    .toString()
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .replace(/[_–—]/g, '-');
}

// Globals from template
const ALL_TRUCKS      = (window.TRUCK_TYPES || []);
const CICPA_CITY_SET  = new Set((window.CICPA_CITIES || []).map(normCity));
const CICPA_ALLOWED   = (window.CICPA_ALLOWED || ["3TPickup","7TPickup","Flatbed","HazmatFB"]);

// Figure out if current destination is CICPA
function isDestinationCICPA() {
  const destSel = document.getElementById('destination');
  const val = destSel ? destSel.value : '';
  return CICPA_CITY_SET.has(normCity(val));
}

// Build <option> list for a given allowed set
function optionsHTML(allowedList, currentValue) {
  const opts = ['<option value="">— Select Truck Type —</option>'];
  allowedList.forEach(t => {
    const sel = (t === currentValue) ? ' selected' : '';
    opts.push(`<option value="${t}"${sel}>${t}</option>`);
  });
  return opts.join('');
}

// Return trucks allowed right now (based on selected destination)
function currentAllowedTrucks() {
  if (isDestinationCICPA()) {
    // keep intersection in case server sends a subset
    const allowed = new Set(CICPA_ALLOWED);
    return ALL_TRUCKS.filter(t => allowed.has(t));
  }
  return ALL_TRUCKS.slice();
}

// Refresh every truck row select when destination changes
function refreshTruckRowsForDestination() {
  const allowed = currentAllowedTrucks();
  document
    .querySelectorAll('#truckTypeContainer select[name="truck_type[]"]')
    .forEach(sel => {
      const previous = sel.value;
      sel.innerHTML = optionsHTML(allowed, allowed.includes(previous) ? previous : "");
    });

  // Optional: show a tiny hint near the destination if it’s CICPA
  const badge = document.getElementById('cicpa-badge');
  if (badge) {
    badge.textContent = isDestinationCICPA() ? '(CICPA)' : '(Non-CICPA)';
  }
}

// ───────────────────────────────────────────────────────────────────
// Chatbot (unchanged behaviour)
// ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
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

  // ─────────────────────────────────────────────────────────────────
  // Transport UI (One Way / Back Load + CICPA filtering)
  // ─────────────────────────────────────────────────────────────────
  const tripRadios = document.querySelectorAll('input[name="trip_type"]');
  tripRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      document.querySelectorAll('.trip-options label').forEach(l => l.classList.remove('selected'));
      const label = radio.closest('label');
      if (label) label.classList.add('selected');
    });
  });

  const truckTypeContainer = document.getElementById('truckTypeContainer');
  const addTruckTypeBtn    = document.getElementById('add-truck-type');
  const destinationSel     = document.getElementById('destination');

  function createTruckRow() {
    const row = document.createElement('div');
    row.className = 'truck-type-row';

    const allowed = currentAllowedTrucks();
    row.innerHTML = `
      <div class="select-wrapper">
        <label class="inline-label">Type</label>
        <select name="truck_type[]" required>
          ${optionsHTML(allowed, "")}
        </select>
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

  if (truckTypeContainer && addTruckTypeBtn) {
    addTruckTypeBtn.addEventListener('click', () => {
      truckTypeContainer.appendChild(createTruckRow());
    });
    // initial row
    truckTypeContainer.appendChild(createTruckRow());
  }

  if (destinationSel) {
    destinationSel.addEventListener('change', refreshTruckRowsForDestination);
  }
  // Initial sync in case template pre-selects a destination
  refreshTruckRowsForDestination();
});
