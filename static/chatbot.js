// ---- Viewport fix (same as project 1) ----
window.addEventListener('load', () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});
window.addEventListener('resize', () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});

document.addEventListener('DOMContentLoaded', () => {
  // ---------------- Chatbot (same UX & API as project 1) ----------------
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

  // ---------------- Transport dynamic UI ----------------
  const tripRadios      = document.querySelectorAll('input[name="trip_type"]');
  const stopsContainer  = document.getElementById('stops-container');
  const stopsList       = document.getElementById('stops-list');
  const addStopBtn      = document.getElementById('add-stop');

  const truckTypeContainer = document.getElementById('truckTypeContainer');
  const addTruckTypeBtn    = document.getElementById('add-truck-type');

  // Trip type behavior
  tripRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      const isMulti = radio.value === 'multi' && radio.checked;
      if (isMulti) {
        stopsContainer.style.display  = 'block';
        stopsContainer.style.overflowY = 'auto';
      } else {
        stopsContainer.style.display  = 'none';
        stopsContainer.style.overflowY = 'hidden';
        if (stopsList) stopsList.innerHTML = '';
      }
      // selection highlight
      document.querySelectorAll('.trip-options label').forEach(l => l.classList.remove('selected'));
      const label = radio.closest('label');
      if (label) label.classList.add('selected');
    });
  });

  // Add additional stop
  if (addStopBtn && stopsList) {
    addStopBtn.addEventListener('click', () => {
      const wrap = document.createElement('div');
      wrap.className = 'stop-group';
      wrap.innerHTML = `
        <select name="additional_cities[]" required>
          <option value="">— Select City —</option>
          <option>Mussafah</option>
          <option>Alain Industrial Area</option>
          <option>Al Ain City Limits</option>
          <option>AUH Airport</option>
          <option>Abu Dhabi City Limits</option>
          <option>Mafraq</option>
          <option>ICAD 2/ICAD3</option>
          <option>ICAD 4</option>
          <option>Al Wathba</option>
          <option>Mina Zayed/Free Port</option>
          <option>Tawazun Industrial Park</option>
          <option>KIZAD</option>
          <option>Khalifa Port/Taweelah</option>
          <option>Sweihan</option>
          <option>Yas Island</option>
          <option>Ghantoot</option>
          <option>Jebel Ali</option>
          <option>Dubai-Al Qusais</option>
          <option>Dubai-Al Quoz</option>
          <option>Dubai-DIP/DIC</option>
          <option>Dubai-DMC</option>
          <option>Dubai-City Limits</option>
          <option>Sharjah</option>
          <option>Sharjah-Hamriyah</option>
          <option>Ajman</option>
          <option>Umm Al Quwain</option>
          <option>Fujairah</option>
          <option>Ras Al Khaimah-Al Ghail</option>
          <option>Ras Al Khaimah-Hamra</option>
          <option>Al Markaz Area</option>
          <option>Baniyas</option>
        </select>
        <button type="button" class="btn-remove" title="Remove City">Clear</button>
      `;
      stopsList.appendChild(wrap);
      wrap.querySelector('.btn-remove').addEventListener('click', () => {
        stopsList.removeChild(wrap);
      });
    });
  }

  // Truck rows
  function createTruckRow(){
    const row = document.createElement('div');
    row.className = 'truck-type-row';
    row.innerHTML = `
      <div class="select-wrapper">
        <label class="inline-label">Type</label>
        <select name="truck_type[]" required>
          <option value="">— Select Truck Type —</option>
          <option value="flatbed">Flatbed (22–25 tons)</option>
          <option value="box">Box / Curtainside (5–10 tons)</option>
          <option value="reefer">Refrigerated (3–12 tons)</option>
          <option value="city">City (1–3 tons)</option>
          <option value="tipper">Tipper / Dump (15–20 tons)</option>
          <option value="double_trailer">Double Trailer</option>
          <option value="10_ton">10-Ton Truck</option>
          <option value="lowbed">Lowbed</option>
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
});
