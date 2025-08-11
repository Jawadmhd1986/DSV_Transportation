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
  // ===== DOM refs (match your existing IDs/classes) =====
  const chatBox    = document.getElementById('chat-box');      // scrollable container
  const chatToggle = document.querySelector('.chat-toggle');    // small round button
  const chatClose  = document.getElementById('chat-close');     // 'X' close button
  const sendBtn    = document.getElementById('chat-send');      // Send button
  const inputEl    = document.getElementById('chat-input');     // Input field
  const chatWin    = document.querySelector('.chat-window');    // chat window root (for open/close)
  const bodyEl     = chatBox || document.getElementById('chat-body') || document.querySelector('.chat-body');

  // ===== Helpers =====
  const scrollToBottom = () => { if (bodyEl) bodyEl.scrollTop = bodyEl.scrollHeight; };

  // Convert lightweight markdown-ish text to HTML with bullet normalization
  function renderRich(text){
    // **bold**
    let t = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

    // 1) Normalize inline bullets like ": - A - B - C" into real lines
    t = t.replace(/:\s*-\s/g, ':\n- ');
    // 2) Anywhere we find " - Word/Emoji", put it on a new line (avoid hyphenated words)
    t = t.replace(/(\S)\s-\s(?=[\p{Emoji}\w])/gu, '$1\n- ');

    // 3) Convert lines starting with "- " into <ul><li>..</li></ul>
    if (/^- |\n- /m.test(t)){
      const lines = t.split(/\n/);
      let out = [], inList = false;
      for (const ln of lines){
        if (ln.trim().startsWith('- ')){
          if (!inList){ out.push('<ul>'); inList = true; }
          out.push('<li>' + ln.trim().slice(2) + '</li>');
        } else {
          if (inList){ out.push('</ul>'); inList = false; }
          out.push(ln);
        }
      }
      if (inList) out.push('</ul>');
      t = out.join('\n');
    }

    // 4) Newlines -> <br> (after list conversion)
    t = t.replace(/\n/g, '<br>');
    return t;
  }

  // Create a message bubble (from = 'bot' | 'user')
  function addMsg(text, from='bot', asCard=false){
    if (!bodyEl) return;
    const wrap = document.createElement('div');
    wrap.className = `msg ${from}`;
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = asCard ? `<div class="card">${renderRich(text)}</div>` : renderRich(text);
    wrap.appendChild(bubble);
    bodyEl.appendChild(wrap);
    scrollToBottom();
  }

  // Typing indicator
  let typingEl = null;
  function showTyping(){
    if (!bodyEl) return;
    typingEl = document.createElement('div');
    typingEl.className = 'msg bot';
    typingEl.innerHTML = `
      <div class="bubble">
        <span class="typing">
          <span class="dot"></span><span class="dot"></span><span class="dot"></span>
        </span>
      </div>`;
    bodyEl.appendChild(typingEl);
    scrollToBottom();
  }
  function hideTyping(){
    if (typingEl){ typingEl.remove(); typingEl = null; }
  }

  // Greeting (once per open)
  let greeted = false;
  function greetOnce(){
    if (greeted) return;
    greeted = true;
    addMsg(
      "Hi! I’m your DSV assistant. Ask me about **storage rates**, **VAS**, **truck types**, **distances**, **racking**, or anything logistics.",
      'bot',
      true
    );
  }

  // ===== Open / Close =====
  if (chatToggle){
    chatToggle.addEventListener('click', () => {
      if (!chatWin) return;
      chatWin.classList.toggle('open');
      if (chatWin.classList.contains('open')){
        greetOnce();
        setTimeout(()=> inputEl && inputEl.focus(), 80);
      }
    });
  }
  if (chatClose){
    chatClose.addEventListener('click', () => {
      if (chatWin) chatWin.classList.remove('open');
    });
  }

  // ===== Send flow =====
  async function send(){
    const text = (inputEl?.value || '').trim();
    if (!text) return;
    addMsg(text, 'user');
    if (inputEl) inputEl.value = '';
    showTyping();

    try{
      const res = await fetch('/chat', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ message: text })
      });
      const data = await res.json();
      hideTyping();

      // Treat multi-line / bulleted / bold answers as a “card”
      const looksCard = /\n- |\*\*/.test(data.reply) || (data.reply.split('\n').length >= 3);
      addMsg(data.reply, 'bot', looksCard);

    }catch(e){
      hideTyping();
      addMsg("Sorry, I couldn’t reach the server. Please try again.", 'bot');
    }
  }

  if (sendBtn) sendBtn.addEventListener('click', send);
  if (inputEl){
    inputEl.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') send();
    });
  }

  // Optional: open on load
  // if (chatWin){ chatWin.classList.add('open'); greetOnce(); }
});
