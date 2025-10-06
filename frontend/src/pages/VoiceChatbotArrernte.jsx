import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useNavigate } from "react-router-dom";
import { Send, Mic, MicOff, Image as ImageIcon, Bot, User, Volume2, VolumeX } from "lucide-react";

export default function VoiceChatbotArrernte() {
  const navigate = useNavigate();

  // ---------- UI STATE ----------
  const [messages, setMessages] = useState(() => ([
    {
      id: "welcome",
      type: "bot",
      content:
        "Werte! Welcome to SwinSACA 👋\nIwerre angkentye-arenhe atyenge. Nhenhe altyerrenge arlkweme akaltye, atherrke image nyente or type-werne.",
      timestamp: new Date(),
    },
  ]));
  const [currentInput, setCurrentInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [speakBot, setSpeakBot] = useState(true);

  const messagesEndRef = useRef(null);
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // ---------- SPEECH ----------
  const Rec =
    typeof window !== "undefined"
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : null;
  const recognitionRef = useRef(null);

  const addMessage = ({ content, type, inputType, imageUrl }) => {
    const m = {
      id: String(Date.now() + Math.random()),
      type,
      content,
      timestamp: new Date(),
      inputType,
      imageUrl,
    };
    setMessages((prev) => [...prev, m]);

    if (type === "user") {
      setIsTyping(true);
      setTimeout(() => {
        const reply = generateBotReply(content, inputType);
        pushBot(reply);
      }, 900);
    }
  };

  const pushBot = (text) => {
    const botMsg = {
      id: String(Date.now() + Math.random()),
      type: "bot",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, botMsg]);
    setIsTyping(false);

    if (speakBot && "speechSynthesis" in window) {
      const utter = new SpeechSynthesisUtterance(text.replace(/\n/g, " "));
      utter.lang = "en-AU";
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utter);
    }
  };

  const generateBotReply = (userInput, inputType) => {
    if (inputType === "voice") {
      return "Atyenge altyerrenge-arenhe. Areme nhenhe atyenge alheme? Arlkweme severity (0–10)?";
    }
    if (inputType === "image") {
      return "Thanks for the image. Nhenhe ateme anthurre apwerte-arenhe?";
    }
    const t = (userInput || "").toLowerCase();
    if (t.includes("chest")) return "Urre nhenhe anthurre apwerte arratyeye? (aye/urle)";
    if (t.includes("cough")) return "Cough atyenge dry nhenhe? Fever atyenge? (aye/urle)";
    if (t.includes("headache")) return "Headache atyenge sudden akaltye? (aye/urle)";
    if (t.includes("fever")) return "Any other atyenge cough, sore throat, or rash?";
    if (t.includes("stomach") || t.includes("nausea")) return "Areme atyenge ateme? Vomiting atyenge? (aye/urle)";
    const fallbacks = [
      "Thanks. Areme nhenhe atyenge-arenhe?",
      "Please arlkweme severity (0–10).",
      "Any other atyenge arratyeye?",
      "Nhenhe areme atnyeneme, atnyengetyele?"
    ];
    return fallbacks[Math.floor(Math.random() * fallbacks.length)];
  };

  // ---------- SEND ----------
  const handleSend = () => {
    const text = currentInput.trim();
    if (!text) return;
    addMessage({ content: text, type: "user", inputType: "text" });
    setCurrentInput("");
  };
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ---------- VOICE ----------
  const toggleVoice = () => {
    if (isRecording) {
      try { recognitionRef.current?.stop(); } catch {}
      setIsRecording(false);
      return;
    }
    if (!Rec) {
      addMessage({ content: "Voice recognition not supported in this browser.", type: "bot" });
      return;
    }
    try {
      const rec = new Rec();
      rec.lang = "en-AU";
      rec.interimResults = false;
      rec.maxAlternatives = 1;

      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript.trim();
        if (transcript) addMessage({ content: transcript, type: "user", inputType: "voice" });
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
  };

  const goToImagePage = () => navigate("/image");

  return (
    <div style={page}>
      <div style={chatShell}>
        {/* Header */}
        <header style={header}>
          <div style={{ display: "flex", alignItems: "center", justifyContent:"space-between" }}>
            <div>
              <h1 style={{ margin: 0, fontSize: 18 }}>SwinSACA Altyerrenge Chat</h1>
              <small style={{ opacity: .75 }}>
                Nhenhe app areme clinician-arenhe. Emergency atyenge apwerte nhenhe, call-werne local services.
              </small>
            </div>

            {/* TTS toggle */}
            <button
              onClick={() => setSpeakBot(v => !v)}
              title={speakBot ? "Mute bot speech" : "Enable bot speech"}
              style={iconBtn(speakBot ? "#2563eb" : "#0b1020")}
            >
              {speakBot ? <Volume2 size={18} color="#fff" /> : <VolumeX size={18} color="#fff" />}
            </button>
          </div>
        </header>

        {/* Messages */}
        <div style={messagesBox}>
          <AnimatePresence>
            {messages.map((m) => (
              <motion.div
                key={m.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -16 }}
                style={{ display: "flex", gap: 12, justifyContent: m.type === "user" ? "flex-end" : "flex-start" }}
              >
                {m.type === "bot" && <div style={avatar("#3b82f6")}><Bot size={16} color="#fff" /></div>}

                <div
                  style={{
                    ...bubbleBase,
                    background: m.type === "user" ? "#174EB2" : "#eef2ff",
                    color: m.type === "user" ? "#fff" : "#0b1220",
                  }}
                >
                  {m.imageUrl && (
                    <img
                      src={m.imageUrl}
                      alt="shared"
                      style={{ width: "100%", maxWidth: 300, height: "auto", borderRadius: 12, marginBottom: 8 }}
                    />
                  )}
                  <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
                  {m.inputType && m.type === "user" && (
                    <div style={{ opacity: .7, fontSize: 12, marginTop: 6 }}>
                      {m.inputType === "voice" ? "🎤 altyerrenge" : m.inputType === "image" ? "🖼 ateme" : "⌨️ text"}
                    </div>
                  )}
                </div>

                {m.type === "user" && <div style={avatar("#6b7280")}><User size={16} color="#fff" /></div>}
              </motion.div>
            ))}

            {isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ display: "flex", gap: 12, justifyContent: "flex-start" }}
              >
                <div style={avatar("#3b82f6")}><Bot size={16} color="#fff" /></div>
                <div style={{ ...bubbleBase, background: "#eef2ff", color: "#0b1220" }}>
                  <div style={{ display: "flex", gap: 6 }}>
                    <Dot /><Dot delay=".12s" /><Dot delay=".24s" />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div ref={messagesEndRef} />
        </div>

        {/* Composer */}
        <footer style={composer}>
          <button
            onClick={toggleVoice}
            title={isRecording ? "Stop" : "Speak"}
            style={iconBtn(isRecording ? "#ef4444" : "#0b1020")}
          >
            {isRecording ? <MicOff size={18} color="#fff" /> : <Mic size={18} color="#fff" />}
          </button>

          <button onClick={goToImagePage} title="Choose image" style={iconBtn("#0b1020")}>
            <ImageIcon size={18} color="#fff" />
          </button>

          <textarea
            value={currentInput}
            onChange={(e) => setCurrentInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Atnkwerene nhenhe… (Enter send-werne)"
            rows={2}
            style={textArea}
          />

          <button onClick={handleSend} disabled={!currentInput.trim()} style={sendBtn}>
            <Send size={16} color="#fff" />
            <span style={{ marginLeft: 8 }}>Send</span>
          </button>

          <div style={disclaimer}>
            ⚠️ Nhenhe app information-only. Always consult clinician for medical advice.
          </div>
        </footer>
      </div>
    </div>
  );
}

/* Typing Dots */
function Dot({ delay = "0s" }) {
  return (
    <div
      style={{
        width: 8, height: 8, borderRadius: 9999, background: "#9ca3af",
        animation: `saca-bounce 1s ${delay} infinite`,
      }}
    />
  );
}

/* ---- reuse same styles ---- */
const page = { minHeight: "100vh", background: "linear-gradient(135deg, #fff7ed, #fef3c7, #fee2e2)", display: "grid", placeItems: "center", padding: 20 };
const chatShell = { width: "min(900px, 96vw)", background: "#fff", borderRadius: 16, boxShadow: "0 18px 48px rgba(20,30,80,.12)", display: "grid", gridTemplateRows: "auto 1fr auto", overflow: "hidden" };
const header = { padding: "14px 16px", borderBottom: "1px solid #fde68a", background: "rgba(255,255,255,.95)", backdropFilter: "blur(6px)" };
const messagesBox = { padding: 16, height: "70vh", overflowY: "auto", display: "flex", flexDirection: "column", gap: 12, background: "linear-gradient(#fff,#fafcff)" };
const composer = { padding: 12, borderTop: "1px solid #fde68a", background: "rgba(255,255,255,.95)", backdropFilter: "blur(6px)", display: "grid", gridTemplateColumns: "auto auto 1fr auto", gap: 10, alignItems: "end" };
const textArea = { resize: "none", borderRadius: 12, border: "1px solid #cbd5e1", padding: "10px 12px", fontSize: 16, outline: "none", minHeight: 44, maxHeight: 120 };
const iconBtn = (bg) => ({ width: 42, height: 42, borderRadius: 12, border: "none", background: bg, color: "#fff", cursor: "pointer", display: "grid", placeItems: "center" });
const sendBtn = { padding: "10px 14px", borderRadius: 12, background: "#174EB2", color: "#fff", border: "none", fontWeight: 700, cursor: "pointer", display: "inline-flex", alignItems: "center" };
const bubbleBase = { maxWidth: "75%", borderRadius: 14, padding: "10px 12px", boxShadow: "0 8px 22px rgba(12,25,64,.06)" };
const avatar = (bg) => ({ width: 32, height: 32, borderRadius: 9999, background: bg, display: "grid", placeItems: "center" });
const disclaimer = { gridColumn: "1 / -1", marginTop: 10, fontSize: 12, color: "#7c6a1d", background: "#fff7d6", border: "1px solid #f4e2a3", padding: "8px 10px", borderRadius: 10, textAlign: "center" };

if (typeof document !== "undefined" && !document.getElementById("saca-voice-bounce-arr")) {
  const style = document.createElement("style");
  style.id = "saca-voice-bounce-arr";
  style.textContent = `
  @keyframes saca-bounce {
    0%, 80%, 100% { transform: scale(0); opacity:.6; }
    40% { transform: scale(1); opacity:1; }
  }`;
  document.head.appendChild(style);
}
