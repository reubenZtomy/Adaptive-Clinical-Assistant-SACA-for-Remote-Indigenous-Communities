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
  const [isTyping, setIsTyping] = useState(false);

  // Voice
  const Rec = typeof window !== "undefined"
    ? (window.SpeechRecognition || window.webkitSpeechRecognition)
    : null;
  const recognitionRef = useRef(null);
  const [isRecording, setIsRecording] = useState(false);

  const messagesEndRef = useRef(null);

  // autoscroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  function addMessage({ content, type, inputType, imageUrl }) {
    const m = {
      id: String(Date.now() + Math.random()),
      type,
      content,
      timestamp: new Date(),
      inputType,
      imageUrl,
    };
    setMessages((prev) => [...prev, m]);

    // simulate bot replying to user text/voice
    if (type === "user") {
      setIsTyping(true);
      setTimeout(() => {
        const reply = generateBotReply(content, inputType);
        setMessages((prev) => [
          ...prev,
          {
            id: String(Date.now() + Math.random()),
            type: "bot",
            content: reply,
            timestamp: new Date(),
          },
        ]);
        setIsTyping(false);
      }, 900);
    }
  }

  function generateBotReply(userInput, inputType) {
    if (inputType === "voice") {
      return "Altyerrenge itye-irre. Nyente itele mape-ante? Severity 0–10-nge atnyeme.";
    }
    if (inputType === "image") {
      return "Anteme itye-irre. Which body area or symptom itele mape-ante?";
    }

    const t = (userInput || "").toLowerCase();
    if (t.includes("chest")) return "Shortness of breath werne heavy sweating itye-irre? (yes/no)";
    if (t.includes("cough")) return "Cough dry-irre kwerte phlegm-irre? Fever itye-irre? (yes/no)";
    if (t.includes("headache")) return "Sudden, severe ‘thunderclap’ itye-irre? (yes/no)";
    if (t.includes("fever")) return "Other symptoms itye-irre? (cough, sore throat, rash)";
    if (t.includes("stomach") || t.includes("nausea")) return "Nyente itele atnyeme? Vomiting werne blood itye-irre? (yes/no)";

    const fallbacks = [
      "Urre. Nyente re atnyeme?",
      "Please severity 0–10-werne atnyeme.",
      "Other symptoms atnyeme?",
      "Nyente itele iperretyeke werne itele mernteke?"
    ];
    return fallbacks[Math.floor(Math.random() * fallbacks.length)];
  }

  function handleSend() {
    const text = currentInput.trim();
    if (!text) return;
    addMessage({ content: text, type: "user", inputType: "text" });
    setCurrentInput("");
  }

  // Voice: start/stop
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

            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ display:"flex", gap:12, justifyContent:"flex-start" }}
              >
                <div style={avatar("#3b82f6")}><Bot size={16} color="#fff" /></div>
                <div style={{...bubbleBase, background:"#eef2ff", color:"#0b1220"}}>
                  <div style={{ display:"flex", gap:6 }}>
                    <Dot /><Dot delay=".12s" /><Dot delay=".24s" />
                  </div>
                </div>
              </motion.div>
            )}
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

/* tiny typing dots */
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
