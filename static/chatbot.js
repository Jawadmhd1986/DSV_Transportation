// -------- Mobile viewport height fix (100vh on iOS/Android) --------
function setVH() {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
}
window.addEventListener('load', setVH);
window.addEventListener('resize', setVH);

document.addEventListener('DOMContentLoaded', () => {
  const chatBox    = document.getElementById('chat-box');
  const chatToggle = document.querySelector('.chat-toggle');
  const chatClose  = document.getElementById('chat-close');
  const sendBtn    = document.getElementById('chat-send');
  const inputEl    = document.getElementById('chat-input');
  const msgsEl     = document.getElementById('chat-messages');

  // Open/close
  chatToggle?.addEventListener('click', () => {
    chatBox.classList.toggle('open');
    if (chatBox.classList.contains('open')) {
      setTimeout(() => stickyScroll(true), 30);
      // greet once on open if empty
      if (!msgsEl.children.length) {
        pushBot("Hello! I'm here to help with anything related to DSV logistics, transport, or warehousing.");
      }
    }
  });
  chatClose?.addEventListener('click', () => chatBox.classList.remove('open'));

  // Autosize textarea
  function autosize() {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
  }
  inputEl?.addEventListener('input', autosize);
  autosize();

  // Sending
  sendBtn?.addEventListener('click', onSend);
  inputEl?.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  });

  // Sticky autoscroll (only if user is near bottom)
  function isNearBottom() {
    const threshold = 60;
    return msgsEl.scrollHeight - msgsEl.scrollTop - msgsEl.clientHeight < threshold;
  }
  function stickyScroll(force=false) {
    if (force || isNearBottom()) msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  // DOM message helpers
  function addRow(sender) {
    const row = document.createElement('div');
    row.className = `message ${sender}`;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    row.appendChild(bubble);
    msgsEl.appendChild(row);
    stickyScroll(true);
    return { row, bubble };
  }
  function pushUser(text) {
    const { bubble } = addRow('user');
    bubble.textContent = text;
  }
  function typingOn() {
    const { row, bubble } = addRow('bot');
    row.classList.add('typing');
    bubble.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    stickyScroll(true);
    return row;
  }
  function typingOff(row) {
    row?.remove();
  }

  // Typewriter animation
  async function typewriter(text) {
    const { bubble } = addRow('bot');
    bubble.textContent = '';
    stickyScroll(true);
    const delay = (ms) => new Promise(r => setTimeout(r, ms));
    for (const ch of text) {
      bubble.textContent += ch;
      stickyScroll();
      await delay(8); // speed
    }
  }

  // Queue to avoid overlapping replies
  let queue = Promise.resolve();
  function pushBot(text) {
    queue = queue.then(() => typewriter(text));
    return queue;
  }

  // Send handler
  async function onSend() {
    const text = (inputEl.value || '').trim();
    if (!text) return;
    inputEl.value = '';
    autosize();
    pushUser(text);

    // Show typing
    const spinner = typingOn();
    sendBtn.disabled = true;

    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json().catch(() => ({}));
      const reply = (data && data.reply) ? String(data.reply) : "Sorry, I couldn't process that.";
      typingOff(spinner);
      await pushBot(reply);
    } catch (e) {
      typingOff(spinner);
      await pushBot("Network error. Please try again.");
    } finally {
      sendBtn.disabled = false;
      stickyScroll(true);
      inputEl.focus();
    }
  }
});
