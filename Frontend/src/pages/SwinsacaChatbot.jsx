import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useNavigate } from "react-router-dom";
import { Send, Mic, MicOff, Image as ImageIcon, Bot, User } from "lucide-react";

export default function SwinsacaChatbot() {
  const navigate = useNavigate();

  const [messages, setMessages] = useState(() => ([
    {
      id: "welcome",
      type: "bot",
      content: "Hi, welcome to SwinSACA 👋\nTell me your main symptom or tap the mic/image to begin.",
      timestamp: new Date(),
    },
  ]));

  const [currentInput, setCurrentInput] = useState("");
  const [isRecording, setIsRecording] = useState(false);

  const Rec = typeof window !== "undefined"
    ? (window.SpeechRecognition || window.webkitSpeechRecognition)
    : null;
  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 🛠️ Keep provided id if present so we can replace placeholders later
  function addMessage({ id, content, type, inputType, imageUrl }) {
    const m = {
      id: id ?? String(Date.now() + Math.random()), // 🛠️
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

  // 🛠️ Normalize arbitrary API response shapes to a single reply string
  function extractReply(payload) {
    if (!payload) return null;

    // common top-level keys
    const direct = payload.reply ?? payload.response ?? payload.message ?? payload.text ?? payload.answer;
    if (typeof direct === "string" && direct.trim()) return direct.trim();

    // alt shapes (e.g., STT/translation or wrapped)
    if (typeof payload.translated_text === "string" && payload.translated_text.trim()) {
      return payload.translated_text.trim();
    }
    if (payload.data) {
      const fromData = payload.data.reply ?? payload.data.response ?? payload.data.message ?? payload.data.text;
      if (typeof fromData === "string" && fromData.trim()) return fromData.trim();
    }

    // arrays like {messages:[{role:'assistant', content:'...'}]}
    if (Array.isArray(payload.messages)) {
      const assistant = payload.messages.find(m => (m.role === "assistant" || m.type === "bot") && m.content);
      if (assistant?.content) return String(assistant.content).trim();
    }

    // last resort: stringify a safe subset
    try {
      return JSON.stringify(payload);
    } catch {
      return "Sorry, I didn’t get that.";
    }
  }

  async function handleSend() {
    const text = currentInput.trim();
    if (!text) return;

    const lang = sessionStorage.getItem("saca_language") || "english";
    const mode = sessionStorage.getItem("saca_mode") || "text";

    // user message
    addMessage({ content: text, type: "user", inputType: "text" });
    setCurrentInput("");

    // status placeholder
    const thinkingMessages = [
      "Analyzing your text...",
      "Please wait while I think...",
      "Processing your request...",
      "Let me check that for you...",
      "Working on your answer..."
    ];
    const randomThinking =
      thinkingMessages[Math.floor(Math.random() * thinkingMessages.length)];

    const placeholderId = `ph-${Date.now()}`; // 🛠️ stable id
    addMessage({
      id: placeholderId, // 🛠️ keep the id
      content: randomThinking,
      type: "bot",
      inputType: "status"
    });

    try {
      const res = await fetch("http://localhost:5000/chat", {
        method: "POST",
        headers: {
          "Accept": "application/json, text/plain;q=0.9,*/*;q=0.8", // 🛠️ accept text fallback
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

      // handle non-2xx
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      // 🛠️ Try JSON first; if it fails, fall back to text
      let data;
      const contentType = res.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        data = await res.json();
      } else {
        const txt = await res.text();
        data = { reply: txt };
      }

      const botReply = extractReply(data) || "Sorry, I didn’t get that.";

      // replace placeholder with real reply
      replaceMessage(placeholderId, {
        content: botReply,
        type: "bot",
        inputType: "text"
      });
    } catch (err) {
      console.error("Chat send failed:", err);
      replaceMessage(placeholderId, {
        content: "There was a problem contacting the server.",
        type: "bot",
        inputType: "text"
      });
    }
  }

  function toggleVoice() {
    if (isRecording) {
      try { recognitionRef.current?.stop(); } catch {}
      setIsRecording(false);
      return;
    }
    if (!Rec) {
      addMessage({ content: "Voice recognition not supported in this browser. Please type.", type: "bot" });
      return;
    }
    try {
      const rec = new Rec();
      rec.lang = "en-AU";
      rec.interimResults = false;
      rec.maxAlternatives = 1;
      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript.trim();
        if (transcript) {
          addMessage({ content: transcript, type: "user", inputType: "voice" });
        }
      };
      rec.onerror = () => setIsRecording(false);
      rec.onend = () => setIsRecording(false);
      recognitionRef.current = rec;
      setIsRecording(true);
      rec.start();
    } catch {
      setIsRecording(false);
      addMessage({ content: "Couldn’t access microphone. Please allow mic permission.", type: "bot" });
    }
  }

  function goToImagePage() { navigate("/image"); }
  function onKeyDown(e) { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }

  return (
    <div style={page}>
      <div style={chatShell}>
        <header style={header}>
          <div style={{display:"flex", alignItems:"baseline", gap:8}}>
            <h1 style={{margin:0, fontSize:18}}>SwinSACA Chat</h1>
          </div>
          <small style={{opacity:.75}}>
            This tool does not replace a clinician. In an emergency, call local services.
          </small>
        </header>

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
                      {m.inputType === "voice" ? "🎤 voice" : m.inputType === "image" ? "🖼 image" : "⌨️ text"}
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

        <footer style={composer}>
          <button
            onClick={toggleVoice}
            title={isRecording ? "Stop" : "Speak"}
            style={iconBtn(isRecording ? "#ef4444" : "#0b1020")}
          >
            {isRecording ? <MicOff size={18} color="#fff" /> : <Mic size={18} color="#fff" />}
          </button>

          <button
            onClick={goToImagePage}
            title="Choose image"
            style={iconBtn("#0b1020")}
          >
            <ImageIcon size={18} color="#fff" />
          </button>

          <textarea
            value={currentInput}
            onChange={(e)=>setCurrentInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Type your message… (Enter to send)"
            rows={2}
            style={textArea}
          />

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

/* ---------------- styles ---------------- */
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

const style = document.createElement("style");
style.textContent = `
@keyframes saca-bounce {
  0%, 80%, 100% { transform: scale(0); opacity:.6; }
  40% { transform: scale(1); opacity:1; }
}`;
document.head.appendChild(style);
