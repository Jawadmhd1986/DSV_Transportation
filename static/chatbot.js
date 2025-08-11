// ==== Fix for mobile viewport height (optional, safe to keep) ====
window.addEventListener('load', () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});
window.addEventListener('resize', () => {
  const vh = window.innerHeight * 0.01;
  document.documentElement.style.setProperty('--vh', `${vh}px`);
});

document.addEventListener('DOMContentLoaded', () => {
  const chatWin   = document.getElementById('chatWin');
  const openBtn   = document.querySelector('.chat-toggle');
  const closeBtn  = document.getElementById('chat-close');
  const chatBox   = document.getElementById('chat-box');
  const inputEl   = document.getElementById('chat-input');
  const sendBtn   = document.getElementById('chat-send');

  const scrollToBottom = () => { chatBox.scrollTop = chatBox.scrollHeight; };

  // Format bot messages, repair inline bullets
  function renderRich(text) {
    let t = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    t = t.replace(/:\s*-\s/g, ':\n- ');
    t = t.replace(/(\S)\s-\s(?=[\p{Emoji}\w])/gu, '$1\n- ');
    if (/^- |\n- /m.test(t)) {
      const lines = t.split(/\n/);
      let out = [], inList = false;
      for (const ln of lines) {
        if (ln.trim().startsWith('- ')) {
          if (!inList) { out.push('<ul>'); inList = true; }
          out.push('<li>' + ln.trim().slice(2) + '</li>');
        } else {
          if (inList) { out.push('</ul>'); inList = false; }
          out.push(ln);
        }
      }
      if (inList) out.push('</ul>');
      t = out.join('\n');
    }
    t = t.replace(/\n/g, '<br>');
    return t;
  }

  function addMsg(text, from='bot', asCard=false) {
    const wrap = document.createElement('div');
    wrap.className = `msg ${from}`;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = asCard ? `<div class="card">${renderRich(text)}</div>` : renderRich(text);
    wrap.appendChild(bubble);
    chatBox.appendChild(wrap);
    scrollToBottom();
  }

  let typingEl = null;
  function showTyping() {
    typingEl = document.createElement('div');
    typingEl.className = 'msg bot';
    typingEl.innerHTML = `<div class="bubble"><span class="typing">
      <span class="dot"></span><span class="dot"></span><span class="dot"></span>
    </span></div>`;
    chatBox.appendChild(typingEl);
    scrollToBottom();
  }
  function hideTyping() { if (typingEl) { typingEl.remove(); typingEl = null; } }

  // Greet once when opened
  let greeted = false;
  function greetOnce() {
    if (greeted) return;
    greeted = true;
    addMsg(
      "Hi! I’m your DSV assistant. Ask me about **storage rates**, **VAS**, **truck types**, **distances**, **racking**, or anything logistics.",
      'bot', true
    );
  }

  // Open/close chat
  openBtn.addEventListener('click', (e) => {
    e.preventDefault();
    chatWin.classList.toggle('open');
    if (chatWin.classList.contains('open')) { greetOnce(); setTimeout(() => inputEl.focus(), 80); }
  });
  closeBtn.addEventListener('click', () => chatWin.classList.remove('open'));

  // Send message
  async function send() {
    const text = (inputEl.value || '').trim();
    if (!text) return;
    addMsg(text, 'user');
    inputEl.value = '';
    showTyping();
    try {
      const res = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      hideTyping();
      const looksCard = /\n- |\*\*/.test(data.reply) || data.reply.split('\n').length >= 3;
      addMsg(data.reply, 'bot', looksCard);
    } catch (err) {
      hideTyping();
      addMsg("Sorry, I couldn’t reach the server. Please try again.", 'bot');
    }
  }
  sendBtn.addEventListener('click', send);
  inputEl.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
});
