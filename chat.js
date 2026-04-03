/* chat.js — handles AJAX messaging + voice input */

const form      = document.getElementById('chatForm');
const input     = document.getElementById('textInput');
const chat      = document.getElementById('chatMain');
const micBtn    = document.getElementById('micBtn');
const voiceNote = document.getElementById('voiceSupportNote');

/* ── Scroll to bottom ── */
function scrollBottom() {
  chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
}

/* ── Append a message bubble ── */
function appendMsg(text, who) {
  // Remove empty state if present
  const empty = chat.querySelector('.empty');
  if (empty) empty.remove();

  const row    = document.createElement('div');
  row.className = `msg-row ${who}`;

  const bubble = document.createElement('div');
  bubble.className = `bubble ${who}`;
  bubble.textContent = text;

  row.appendChild(bubble);
  chat.appendChild(row);
  scrollBottom();
  return row;
}

/* ── Show typing indicator ── */
function showTyping() {
  const row    = document.createElement('div');
  row.className = 'msg-row bot typing';
  row.id = 'typingIndicator';

  const bubble = document.createElement('div');
  bubble.className = 'bubble bot';
  bubble.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';

  row.appendChild(bubble);
  chat.appendChild(row);
  scrollBottom();
}

function hideTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

/* ── Send message ── */
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const msg = input.value.trim();
  if (!msg) return;

  appendMsg(msg, 'user');
  input.value = '';
  input.focus();
  showTyping();

  try {
    const res  = await fetch('/get', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `msg=${encodeURIComponent(msg)}`
    });
    const data = await res.json();
    hideTyping();
    appendMsg(data.response, 'bot');
  } catch (err) {
    hideTyping();
    appendMsg('⚠️ Could not reach the server. Please try again.', 'bot');
    console.error(err);
  }
});

/* ── Send on Enter (no Shift) ── */
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    form.dispatchEvent(new Event('submit'));
  }
});

/* ── Voice input ── */
const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

if (SpeechRecognition) {
  if (voiceNote) voiceNote.textContent = '🎤 Voice input supported in this browser.';

  const recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.interimResults = false;

  let listening = false;

  micBtn.addEventListener('click', () => {
    if (listening) {
      recognition.stop();
    } else {
      recognition.start();
      micBtn.textContent = '⏹️';
      micBtn.title = 'Stop recording';
      listening = true;
    }
  });

  recognition.addEventListener('result', (e) => {
    const transcript = e.results[0][0].transcript;
    input.value = transcript;
  });

  recognition.addEventListener('end', () => {
    listening = false;
    micBtn.textContent = '🎤';
    micBtn.title = 'Voice input';
  });

  recognition.addEventListener('error', (e) => {
    listening = false;
    micBtn.textContent = '🎤';
    console.warn('Speech error:', e.error);
  });

} else {
  // Hide mic button if not supported
  micBtn.style.display = 'none';
  if (voiceNote) voiceNote.textContent = 'Voice input is not supported in this browser.';
}

/* ── Auto scroll on load ── */
scrollBottom();
