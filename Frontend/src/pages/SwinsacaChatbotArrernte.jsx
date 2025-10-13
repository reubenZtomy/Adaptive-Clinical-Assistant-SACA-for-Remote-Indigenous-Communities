import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useNavigate } from "react-router-dom";
import { Send, Mic, MicOff, Image as ImageIcon, Bot, User } from "lucide-react";

export default function SwinsacaChatbotArrernte() {
  const navigate = useNavigate();

  // messages: { id, type: 'bot'|'user', content, inputType?, imageUrl? }
  const [messages, setMessages] = useState(() => ([
    {
      id: "welcome",
      type: "bot",
      content:
        "Arrernte-ketye, welcome to SwinSACA 👋\nKenhe-werne itye atnyeme symptom-werne angkentye, nhenhe mic/imij-werne mape-ante.",
      timestamp: new Date(),
    },
  ]));

  const [currentInput, setCurrentInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);

  // Voice
  const Rec = typeof window !== "undefined"
    ? (window.SpeechRecognition || window.webkitSpeechRecognition)
    : null;
  const recognitionRef = useRef(null);

  const messagesEndRef = useRef(null);

  // autoscroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ---- helpers: message add/replace ----
  function addMessage({ id, content, type, inputType, imageUrl }) {
    const m = {
      id: id ?? String(Date.now() + Math.random()),
      type,
      content,
      timestamp: new Date(),
      inputType,
      imageUrl,
    };
    setMessages((prev) => [...prev, m]);
  }

  function replaceMessage(id, newMessage) {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? { ...msg, ...newMessage } : msg))
    );
  }

  // ---- normalize API response to a single reply string (aligned with your attached file) ----
  function extractReply(payload) {
    if (!payload) return null;

    const direct = payload.reply ?? payload.response ?? payload.message ?? payload.text ?? payload.answer;
    if (typeof direct === "string" && direct.trim()) return direct.trim();

    if (typeof payload.translated_text === "string" && payload.translated_text.trim()) {
      return payload.translated_text.trim();
    }
    if (payload.data) {
      const fromData = payload.data.reply ?? payload.data.response ?? payload.data.message ?? payload.data.text;
      if (typeof fromData === "string" && fromData.trim()) return fromData.trim();
    }
    if (Array.isArray(payload.messages)) {
      const assistant = payload.messages.find(m => (m.role === "assistant" || m.type === "bot") && m.content);
      if (assistant?.content) return String(assistant.content).trim();
    }
    try {
      return JSON.stringify(payload);
    } catch {
      return "Sorry, I didn’t get that.";
    }
  }

  // ---- send to API (replaces simulate/generateBotReply) ----
  async function handleSend() {
    const text = currentInput.trim();
    if (!text) return;

    const lang = sessionStorage.getItem("saca_language") || "arr+english"; // keep your hybrid default
    const mode = sessionStorage.getItem("saca_mode") || "text";

    // user bubble
    addMessage({ content: text, type: "user", inputType: "text" });
    setCurrentInput("");

    // placeholder bot bubble
    const thinkingMessages = [
      "Analyzing…",
      "Please wait, thinking…",
      "Processing your angkentye…",
      "Let me check that for you…",
      "Working on your answer…"
    ];
    const placeholderId = `ph-${Date.now()}`;
    addMessage({ id: placeholderId, content: thinkingMessages[Math.floor(Math.random()*thinkingMessages.length)], type: "bot", inputType: "status" });

    try {
      const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: {
          "Accept": "application/json, text/plain;q=0.9,*/*;q=0.8",
          "Content-Type": "application/json",
          "X-Language": lang,
          "X-Mode": mode
        },
        body: JSON.stringify({
          message: text,
          inputType: "text",
          _context: { language: lang, mode: mode }
        })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      let data;
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        data = await res.json();
      } else {
        const txt = await res.text();
        data = { reply: txt };
      }

      const botReply = extractReply(data) || "Sorry, I didn’t get that.";
      replaceMessage(placeholderId, { content: botReply, type: "bot", inputType: "text" });
    } catch (err) {
      console.error("Chat send failed:", err);
      replaceMessage(placeholderId, {
        content: "Server ileme-irre. Please try again.",
        type: "bot",
        inputType: "text"
      });
    }
  }

  // Voice: start/stop → onresult posts transcript to chat API
  function toggleVoice() {
    if (isRecording) {
      try { recognitionRef.current?.stop(); } catch {}
      setIsRecording(false);
      return;
    }
    if (!Rec) {
      addMessage({ content: "Voice recognition ileme-irre browser-werne. Nhenhe atnkwerene (text) atnyeme.", type: "bot" });
      return;
    }
    try {
      const rec = new Rec();
      rec.lang = "en-AU"; // keep English ASR locale unless you have Arrernte ASR
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      rec.onresult = async (e) => {
        const transcript = e.results[0][0].transcript.trim();
        if (!transcript) return;

        // show user voice bubble
        addMessage({ content: transcript, type: "user", inputType: "voice" });

        // placeholder
        const placeholderId = `ph-${Date.now()}`;
        addMessage({ id: placeholderId, content: "Transcribing & processing…", type: "bot", inputType: "status" });

        // send to API
        const lang = sessionStorage.getItem("saca_language") || "arr+english";
        const mode = "voice";
        try {
          const res = await fetch("http://localhost:5000/chat", {
            method: "POST",
            headers: {
              "Accept": "application/json, text/plain;q=0.9,*/*;q=0.8",
              "Content-Type": "application/json",
              "X-Language": lang,
              "X-Mode": mode
            },
            body: JSON.stringify({
              message: transcript,
              inputType: "voice",
              _context: { language: lang, mode: mode }
            })
          });

          if (!res.ok) throw new Error(`HTTP ${res.status}`);

          let data;
          const contentType = res.headers.get("content-type") || "";
          if (contentType.includes("application/json")) {
            data = await res.json();
          } else {
            const txt = await res.text();
            data = { reply: txt };
          }

          const botReply = extractReply(data) || "Sorry, I didn’t get that.";
          replaceMessage(placeholderId, { content: botReply, type: "bot", inputType: "text" });
        } catch (err) {
          console.error("Voice chat failed:", err);
          replaceMessage(placeholderId, { content: "Server ileme-irre. Please try again.", type: "bot" });
        }
      };
      rec.onerror = () => setIsRecording(false);
      rec.onend = () => setIsRecording(false);
      recognitionRef.current = rec;
      setIsRecording(true);
      rec.start();
    } catch {
      setIsRecording(false);
      addMessage({ content: "Microphone ileme-irre. Mic permission itele mapeke.", type: "bot" });
    }
  }

  // Image button: go to your ImageInput page
  function goToImagePage() {
    navigate("/image"); // ensure <Route path="/image" .../> exists
  }

  function onKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div style={page}>
      <div style={chatShell}>
        <header style={header}>
          <div style={{display:"flex", alignItems:"baseline", gap:8}}>
            <h1 style={{margin:0, fontSize:18}}>SwinSACA Angkentye Chat</h1>
          </div>
          <small style={{opacity:.75}}>
            Nhenhe app anthurre-arenye. Emergency-werne irrtyeme, local services-werne atnyeme.
          </small>
        </header>

        {/* messages */}
        <div style={messagesBox}>
          <AnimatePresence>
            {messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                style={{
                  display: "flex",
                  gap: 12,
                  justifyContent: m.type === "user" ? "flex-end" : "flex-start"
                }}
              >
                {m.type === "bot" && (
                  <div style={avatar("#3b82f6")}><Bot size={16} color="#fff" /></div>
                )}

                <div style={{
                  ...bubbleBase,
                  background: m.type === "user" ? "#174EB2" : "#eef2ff",
                  color: m.type === "user" ? "#fff" : "#0b1220",
                }}>
                  {m.imageUrl && (
                    <img
                      src={m.imageUrl}
                      alt="shared"
                      style={{ width: "100%", maxWidth: 300, height: "auto", borderRadius: 12, marginBottom: 8 }}
                    />
                  )}
                  <div style={{whiteSpace:"pre-wrap"}}>{m.content}</div>

                  {m.inputType && m.type === "user" && (
                    <div style={{opacity:.7, fontSize:12, marginTop:6}}>
                      {m.inputType === "voice" ? "🎤 altyerrenge" : m.inputType === "image" ? "🖼 anteme" : "⌨️ atnkwerene"}
                    </div>
                  )}
                </div>

                {m.type === "user" && (
                  <div style={avatar("#6b7280")}><User size={16} color="#fff" /></div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          <div ref={messagesEndRef} />
        </div>

        {/* composer */}
        <footer style={composer}>
          {/* Mic */}
          <button
            onClick={toggleVoice}
            title={isRecording ? "Stop" : "Speak"}
            style={iconBtn(isRecording ? "#ef4444" : "#0b1020")}
          >
            {isRecording ? <MicOff size={18} color="#fff" /> : <Mic size={18} color="#fff" />}
          </button>

          {/* Image → /image */}
          <button
            onClick={goToImagePage}
            title="Choose image"
            style={iconBtn("#0b1020")}
          >
            <ImageIcon size={18} color="#fff" />
          </button>

          {/* Text */}
          <textarea
            value={currentInput}
            onChange={(e)=>setCurrentInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Angkentye-werne atnyeme… (Enter)"
            rows={2}
            style={textArea}
          />

          {/* Send */}
          <button
            onClick={handleSend}
            disabled={!currentInput.trim()}
            style={sendBtn}
          >
            <Send size={16} color="#fff" />
            <span style={{marginLeft:8}}>Send</span>
          </button>
        </footer>
      </div>
    </div>
  );
}

/* tiny typing dots (kept for future use if you add a live typing state) */
function Dot({ delay="0s" }) {
  return (
    <div
      style={{
        width: 8, height: 8, borderRadius: 9999, background:"#9ca3af",
        animation: `saca-bounce 1s ${delay} infinite`,
      }}
    />
  );
}

/* ---------------- styles (unchanged) ---------------- */
const page = {
  minHeight: "100vh",
  background: "linear-gradient(135deg, #fff7ed, #fef3c7, #fee2e2)",
  display: "grid",
  placeItems: "center",
  padding: 20,
};

const chatShell = {
  width: "min(900px, 96vw)",
  background: "#fff",
  borderRadius: 16,
  boxShadow: "0 18px 48px rgba(20,30,80,.12)",
  display: "grid",
  gridTemplateRows: "auto 1fr auto",
  overflow: "hidden",
};

const header = {
  padding: "14px 16px",
  borderBottom: "1px solid #fde68a",
  background: "rgba(255,255,255,.95)",
  backdropFilter: "blur(6px)",
};

const messagesBox = {
  padding: 16,
  height: "70vh",
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: 12,
  background: "linear-gradient(#fff,#fafcff)",
};

const composer = {
  padding: 12,
  borderTop: "1px solid #fde68a",
  background: "rgba(255,255,255,.95)",
  backdropFilter: "blur(6px)",
  display: "grid",
  gridTemplateColumns: "auto auto 1fr auto",
  gap: 10,
  alignItems: "end",
};

const textArea = {
  resize: "none",
  borderRadius: 12,
  border: "1px solid #cbd5e1",
  padding: "10px 12px",
  fontSize: 16,
  outline: "none",
  minHeight: 44,
  maxHeight: 120,
};

const iconBtn = (bg) => ({
  width: 42, height: 42,
  borderRadius: 12,
  border: "none",
  background: bg,
  color: "#fff",
  cursor: "pointer",
  display: "grid", placeItems: "center",
});

const sendBtn = {
  padding: "10px 14px",
  borderRadius: 12,
  background: "#174EB2",
  color: "#fff",
  border: "none",
  fontWeight: 700,
  cursor: "pointer",
  display: "inline-flex",
  alignItems: "center",
};

const bubbleBase = {
  maxWidth: "75%",
  borderRadius: 14,
  padding: "10px 12px",
  boxShadow: "0 8px 22px rgba(12,25,64,.06)",
};

const avatar = (bg) => ({
  width: 32, height: 32,
  borderRadius: 9999,
  background: bg,
  display: "grid",
  placeItems: "center",
});

/* keyframes for typing dots */
if (typeof document !== "undefined" && !document.getElementById("saca-bounce-arr")) {
  const style = document.createElement("style");
  style.id = "saca-bounce-arr";
  style.textContent = `
@keyframes saca-bounce {
  0%, 80%, 100% { transform: scale(0); opacity:.6; }
  40% { transform: scale(1); opacity:1; }
}`;
  document.head.appendChild(style);
}
