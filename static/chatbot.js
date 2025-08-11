// Fix for mobile viewport height
window.addEventListener('load', () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});
window.addEventListener('resize', () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});

document.addEventListener('DOMContentLoaded', () => {
  // --- Chat UI elements ---
  const chatBox    = document.getElementById('chat-box');
  const chatToggle = document.querySelector('.chat-toggle');
  const chatClose  = document.getElementById('chat-close');
  const sendBtn    = document.getElementById('chat-send');
  const inputEl    = document.getElementById('chat-input');
  const msgsEl     = document.getElementById('chat-messages');

  // Safeguard: only bind if all elements exist
  if (chatToggle && chatBox && chatClose && sendBtn && inputEl && msgsEl) {
    chatToggle.addEventListener('click', () => chatBox.classList.toggle('open'));
    chatClose.addEventListener('click', () => chatBox.classList.remove('open'));
    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    });
  }

  // Add a chat message bubble
  function addMessage(text, sender = 'bot') {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.innerHTML = `<div class="bubble">${text}</div>`;
    msgsEl.appendChild(div);
    msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  // ---- REAL backend call to /chat (Flask) ----
  async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    // show user's bubble
    addMessage(text, 'user');
    inputEl.value = '';

    // show temporary typing bubble
    const thinking = document.createElement('div');
    thinking.className = 'message bot';
    thinking.innerHTML = `<div class="bubble">...</div>`;
    msgsEl.appendChild(thinking);
    msgsEl.scrollTop = msgsEl.scrollHeight;

    try {
      const resp = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const data = await resp.json();
      thinking.remove();
      addMessage((data && data.reply) ? data.reply : "Sorry, I didn't catch that.");
    } catch (err) {
      thinking.remove();
      console.error('Chat error:', err);
      addMessage('Sorry, there was a problem reaching the assistant. Please try again.');
    }
  }

  // -------------------------------
  // Trip type & extra cities UI
  // -------------------------------
  const tripRadios = document.querySelectorAll('input[name="trip_type"]');
  const stopsContainer = document.getElementById('stops-container');
  const stopsList = document.getElementById('stops-list');
  const addStopBtn = document.getElementById('add-stop');

  tripRadios.forEach((radio) => {
    radio.addEventListener('change', () => {
      if (radio.value === 'multi' && radio.checked) {
        stopsContainer.style.display = 'block';
        stopsContainer.style.overflowY = 'auto';
      } else {
        stopsContainer.style.display = 'none';
        stopsContainer.style.overflowY = 'hidden';
        if (stopsList) stopsList.innerHTML = '';
      }

      const truckTypeContainer = document.getElementById('truckTypeContainer');
      if (truckTypeContainer) {
        if (radio.value === 'multi' && radio.checked) {
          truckTypeContainer.style.overflowY = 'auto';
          truckTypeContainer.style.maxHeight = '200px';
        } else {
          truckTypeContainer.style.overflowY = 'hidden';
          truckTypeContainer.style.maxHeight = 'none';
        }
      }
    });
  });

  if (addStopBtn && stopsList) {
    addStopBtn.addEventListener('click', () => {
      const stopGroup = document.createElement('div');
      stopGroup.classList.add('stop-group');
      stopGroup.innerHTML = `
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
      stopsList.appendChild(stopGroup);

      stopGroup.querySelector('.btn-remove').addEventListener('click', () => {
        stopsList.removeChild(stopGroup);
      });
    });
  }

  // -------------------------------
  // Truck type dynamic rows
  // -------------------------------
  const truckTypeContainer = document.getElementById('truckTypeContainer');
  const addTruckTypeBtn = document.getElementById('add-truck-type');

  function createTruckTypeRow() {
    const row = document.createElement('div');
    row.classList.add('truck-type-row');

    const selectWrapper = document.createElement('div');
    selectWrapper.classList.add('select-wrapper');

    const selectLabel = document.createElement('label');
    selectLabel.textContent = 'Type';
    selectLabel.classList.add('inline-label');

    const select = document.createElement('select');
    select.name = 'truck_type[]';
    select.required = true;
    select.innerHTML = `
      <option value="">— Select Truck Type —</option>
      <option value="flatbed">Flatbed (22–25 tons)</option>
      <option value="box">Box / Curtainside (5–10 tons)</option>
      <option value="reefer">Refrigerated (3–12 tons)</option>
      <option value="city">City (1–3 tons)</option>
      <option value="tipper">Tipper / Dump (15–20 tons)</option>
      <option value="double_trailer">Double Trailer</option>
      <option value="10_ton">10-Ton Truck</option>
      <option value="lowbed">Lowbed</option>
    `;

    selectWrapper.appendChild(selectLabel);
    selectWrapper.appendChild(select);

    const qtyWrapper = document.createElement('div');
    qtyWrapper.classList.add('qty-wrapper');

    const qtyLabel = document.createElement('label');
    qtyLabel.textContent = 'QTY';
    qtyLabel.classList.add('inline-label');

    const input = document.createElement('input');
    input.type = 'number';
    input.name = 'truck_qty[]';
    input.placeholder = 'Count';
    input.min = '1';
    input.required = true;

    qtyWrapper.appendChild(qtyLabel);
    qtyWrapper.appendChild(input);

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'btn-remove';
    removeBtn.title = 'Remove Truck Type';
    removeBtn.textContent = 'Clear';
    removeBtn.addEventListener('click', () => row.remove());

    row.appendChild(selectWrapper);
    row.appendChild(qtyWrapper);
    row.appendChild(removeBtn);

    return row;
  }

  if (addTruckTypeBtn && truckTypeContainer) {
    addTruckTypeBtn.addEventListener('click', () => {
      truckTypeContainer.appendChild(createTruckTypeRow());
    });
    // initial row
    truckTypeContainer.appendChild(createTruckTypeRow());
  }

  // Trip type visual highlight
  const tripOptionLabels = document.querySelectorAll('.trip-options label');
  tripRadios.forEach((radio) => {
    radio.addEventListener('change', () => {
      tripOptionLabels.forEach((l) => l.classList.remove('selected'));
      if (radio.checked) {
        const label = radio.closest('label') ||
          [...tripOptionLabels].find((l) => l.querySelector(`input[value="${radio.value}"]`));
        if (label) label.classList.add('selected');
      }
    });
  });
});
