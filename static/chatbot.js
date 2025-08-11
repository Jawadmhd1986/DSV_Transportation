// Fix for mobile viewport height
window.addEventListener('load', () => {
  let vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});
window.addEventListener('resize', () => {
  let vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});

document.addEventListener('DOMContentLoaded', () => {
  // Chatbot functionality
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

    async function sendMessage() {
      const text = inputEl.value.trim();
      if (!text) return;
      addMessage(text, 'user');
      inputEl.value = '';
      // Simulate bot reply for now
      addMessage('Thanks for your message. We will get back shortly.', 'bot');
      msgsEl.scrollTop = msgsEl.scrollHeight;
    }

    function addMessage(text, sender) {
      const div = document.createElement('div');
      div.className = `message ${sender}`;
      div.innerHTML = `<div class="bubble">${text}</div>`;
      msgsEl.appendChild(div);
      msgsEl.scrollTop = msgsEl.scrollHeight;
    }
  }

  // Trip type selection and additional cities toggle
  const tripRadios = document.querySelectorAll('input[name="trip_type"]');
  const stopsContainer = document.getElementById('stops-container');
  const stopsList = document.getElementById('stops-list');
  const addStopBtn = document.getElementById('add-stop');

  tripRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      if (radio.value === 'multi' && radio.checked) {
        stopsContainer.style.display = 'block';
        stopsContainer.style.overflowY = 'auto';  // show scroll if needed
      } else {
        stopsContainer.style.display = 'none';
        stopsContainer.style.overflowY = 'hidden';
        stopsList.innerHTML = '';
      }

      // Adjust truck container scroll based on trip type
      const truckTypeContainer = document.getElementById('truckTypeContainer');
      if (radio.value === 'multi' && radio.checked) {
        truckTypeContainer.style.overflowY = 'auto';
        truckTypeContainer.style.maxHeight = '200px';
      } else {
        truckTypeContainer.style.overflowY = 'hidden';
        truckTypeContainer.style.maxHeight = 'none';
      }
    });
  });

  // Add additional city row
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
      <button type="button" class="btn-remove" title="Remove City">Clear</button> <!-- Changed × to Clear -->
    `;
    stopsList.appendChild(stopGroup);

    // Remove the stop group on Clear click
    stopGroup.querySelector('.btn-remove').addEventListener('click', () => {
      stopsList.removeChild(stopGroup);
    });
  });

  // Truck Types dynamic rows
  const truckTypeContainer = document.getElementById('truckTypeContainer');
  const addTruckTypeBtn = document.getElementById('add-truck-type');

  function createTruckTypeRow() {
    const row = document.createElement('div');
    row.classList.add('truck-type-row');

    // Truck Type select wrapper
    const selectWrapper = document.createElement('div');
    selectWrapper.classList.add('select-wrapper');

    const selectLabel = document.createElement('label');
    selectLabel.textContent = "Type";
    selectLabel.classList.add('inline-label');

    const select = document.createElement('select');
    select.name = "truck_type[]";
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

    // QTY wrapper
    const qtyWrapper = document.createElement('div');
    qtyWrapper.classList.add('qty-wrapper');

    const qtyLabel = document.createElement('label');
    qtyLabel.textContent = "QTY";
    qtyLabel.classList.add('inline-label');

    const input = document.createElement('input');
    input.type = "number";
    input.name = "truck_qty[]";
    input.placeholder = "Count";
    input.min = "1";
    input.required = true;

    qtyWrapper.appendChild(qtyLabel);
    qtyWrapper.appendChild(input);

    // Remove button with text "Clear"
    const removeBtn = document.createElement('button');
    removeBtn.type = "button";
    removeBtn.className = "btn-remove";
    removeBtn.title = "Remove Truck Type";
    removeBtn.textContent = "Clear";  // Changed × to Clear

    removeBtn.addEventListener('click', () => {
      truckTypeContainer.removeChild(row);
    });

    row.appendChild(selectWrapper);
    row.appendChild(qtyWrapper);
    row.appendChild(removeBtn);

    return row;
  }

  addTruckTypeBtn.addEventListener('click', () => {
    truckTypeContainer.appendChild(createTruckTypeRow());
  });

  // Add initial truck type row on load
  truckTypeContainer.appendChild(createTruckTypeRow());

  // Trip type radio button visual selection highlight
  const tripOptionLabels = document.querySelectorAll('.trip-options label');
  tripRadios.forEach(radio => {
    radio.addEventListener('change', () => {
      tripOptionLabels.forEach(label => label.classList.remove('selected'));
      if (radio.checked) {
        const label = radio.closest('label') || [...tripOptionLabels].find(l => l.querySelector(`input[value="${radio.value}"]`));
        if (label) label.classList.add('selected');
      }
    });
  });
});
