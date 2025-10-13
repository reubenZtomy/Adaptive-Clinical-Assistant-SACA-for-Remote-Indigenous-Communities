import { useRef, useState, useEffect } from "react";
import { Mic, Square, Image as ImageIcon, Bot, User, Send } from "lucide-react";
import RecordingVisualization from "../components/RecordingVisualization";

export default function VoiceChat() {
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      type: "bot",
      content:
        "Hi, welcome to SwinSACA 👋\nTell me your main symptom or tap the mic/image to begin.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordSecs, setRecordSecs] = useState(0);
  const recordTimer = useRef(null);
  const fileInputRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const addMessage = (content, type, extra = {}) => {
    setMessages(prev => [...prev, { id: Date.now().toString(), type, content, ...extra }]);
  };

  const botReply = (userText, hint) => {
    setIsTyping(true);
    setTimeout(() => {
      let reply = "";
      if (hint === "voice") {
        reply =
          "Thanks, I heard you. When did this start and how severe is it (1–10)?";
      } else if (hint === "image") {
        reply =
          "Thanks for the image. Which area are you most worried about and since when?";
      } else {
        const l = userText.toLowerCase();
        if (l.includes("fever")) reply = "Have you checked your temperature? Any headache or body aches?";
        else if (l.includes("cough")) reply = "Is the cough dry or with phlegm? How long have you had it?";
        else if (l.includes("pain")) reply = "Where is the pain located? Please rate it from 1–10.";
        else reply = "Got it. Please share when it started and any other symptoms.";
      }
      addMessage(reply, "bot");
      setIsTyping(false);
    }, 900 + Math.random() * 700);
  };

  const onSend = () => {
    const text = input.trim();
    if (!text) return;
    addMessage(text, "user", { inputType: "text" });
    setInput("");
    botReply(text, "text");
  };

  const startRec = () => {
    setIsRecording(true);
    setRecordSecs(0);
    recordTimer.current = setInterval(() => setRecordSecs(s => s + 1), 1000);
  };

  const stopRec = () => {
    setIsRecording(false);
    clearInterval(recordTimer.current);
    // mock transcription
    const mock = "I have a headache since yesterday and feel nauseous.";
    addMessage(mock, "user", { inputType: "voice" });
    botReply(mock, "voice");
    setRecordSecs(0);
  };

  const onImagePicked = e => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      addMessage("I uploaded an image showing my concern.", "user", {
        inputType: "image",
        imageUrl: ev.target.result,
      });
      botReply("", "image");
    };
    reader.readAsDataURL(file);
    e.target.value = ""; // reset
  };

  const bubble = (msg) => (
    <div
      key={msg.id}
      style={{
        display: "flex",
        gap: 12,
        justifyContent: msg.type === "user" ? "flex-end" : "flex-start",
      }}
    >
      {msg.type === "bot" && (
        <div style={{
          width: 36, height: 36, borderRadius: 999, background: "#0b1020",
          display: "grid", placeItems: "center", color: "#fff", flexShrink: 0, marginTop: 4
        }}>
          <Bot size={18}/>
        </div>
      )}

      <div style={{
        maxWidth: 620, padding: "12px 14px",
        background: msg.type === "user" ? "#0b63ff" : "#eaf1ff",
        color: msg.type === "user" ? "#fff" : "#0b1220",
        borderRadius: 16,
        boxShadow: "0 8px 30px rgba(12,20,54,.08)",
        whiteSpace: "pre-wrap",
      }}>
        {msg.imageUrl && (
          <img
            src={msg.imageUrl}
            alt="upload"
            style={{ width: "100%", maxHeight: 220, objectFit: "cover", borderRadius: 12, marginBottom: 8 }}
          />
        )}
        {msg.content}
        {msg.inputType && msg.type === "user" && (
          <div style={{ opacity: .7, fontSize: 12, marginTop: 6, display: "flex", alignItems: "center", gap: 6 }}>
            {msg.inputType === "voice" && <Mic size={14}/>}
            {msg.inputType === "image" && <ImageIcon size={14}/>}
            <span style={{ textTransform: "capitalize" }}>{msg.inputType}</span>
          </div>
        )}
      </div>

      {msg.type === "user" && (
        <div style={{
          width: 36, height: 36, borderRadius: 999, background: "#94a3b8",
          display: "grid", placeItems: "center", color: "#fff", flexShrink: 0, marginTop: 4
        }}>
          <User size={18}/>
        </div>
      )}
    </div>
  );

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(180deg,#fff7e6,#fde4cf)",
      padding: 24,
      display: "flex", justifyContent: "center"
    }}>
      <div style={{
        width: "min(1020px, 100%)",
        background: "#fff",
        borderRadius: 14,
        boxShadow: "0 14px 50px rgba(12,25,64,.12)",
        display: "flex", flexDirection: "column",
        overflow: "hidden"
      }}>
        {/* Header */}
        <div style={{ padding: 16, borderBottom: "1px solid #e5e7eb" }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: "#0b1220" }}>SwinSACA Chat</div>
          <div style={{ fontSize: 13, color: "#6b7280" }}>
            This tool does not replace a clinician. In an emergency, call local services.
          </div>
        </div>

        {/* Messages */}
        <div style={{ flex: 1, padding: 20, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12 }}>
          {messages.map(bubble)}
          {isTyping && (
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 999, background: "#0b1020",
                display: "grid", placeItems: "center", color: "#fff", flexShrink: 0, marginTop: 4
              }}>
                <Bot size={18}/>
              </div>
              <div style={{
                padding: "10px 12px", background: "#eaf1ff", borderRadius: 16,
                display: "inline-flex", gap: 6
              }}>
                <span className="dot" />
                <span className="dot" style={{ animationDelay: ".12s" }}/>
                <span className="dot" style={{ animationDelay: ".24s" }}/>
              </div>
            </div>
          )}
          <div ref={endRef}/>
        </div>

        {/* Recording panel */}
        {isRecording && (
          <div style={{ padding: 14, borderTop: "1px solid #c7d2fe", background: "#eef2ff" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
              <RecordingVisualization isRecording={isRecording}/>
              <div style={{ color: "#1d4ed8", fontWeight: 600 }}>Recording: {Math.floor(recordSecs/60)}:{String(recordSecs%60).padStart(2,"0")}</div>
              <button
                onClick={stopRec}
                style={{
                  display: "inline-flex", alignItems: "center", gap: 8,
                  background: "#ef4444", color: "#fff", border: 0,
                  padding: "10px 14px", borderRadius: 12, cursor: "pointer"
                }}>
                <Square size={16}/> Stop
              </button>
            </div>
          </div>
        )}

        {/* Input area */}
        <div style={{ padding: 14, borderTop: "1px solid #e5e7eb", background: "#fff" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* Mic */}
            <button
              onClick={isRecording ? stopRec : startRec}
              aria-label={isRecording ? "Stop recording" : "Start recording"}
              style={{
                width: 48, height: 48, borderRadius: 12, border: 0,
                background: isRecording ? "#ef4444" : "#0b1020", color: "#fff",
                display: "grid", placeItems: "center", cursor: "pointer"
              }}
            >
              {isRecording ? <Square size={18}/> : <Mic size={18}/>}
            </button>

            {/* Image */}
            <button
              onClick={() => fileInputRef.current?.click()}
              aria-label="Upload image"
              style={{
                width: 48, height: 48, borderRadius: 12, border: 0,
                background: "#0b1020", color: "#fff",
                display: "grid", placeItems: "center", cursor: "pointer"
              }}
            >
              <ImageIcon size={18}/>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={onImagePicked}
              style={{ display: "none" }}
            />

            {/* Text input */}
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onSend()}
              placeholder="Type your message… (Enter to send)"
              style={{
                flex: 1, height: 48, borderRadius: 12, border: "1px solid #e5e7eb",
                padding: "0 14px", outline: "none"
              }}
            />

            {/* Send */}
            <button
              onClick={onSend}
              disabled={!input.trim()}
              style={{
                height: 48, padding: "0 18px", borderRadius: 12, border: 0,
                background: "#0b63ff", color: "#fff", display: "inline-flex",
                alignItems: "center", gap: 8, cursor: input.trim() ? "pointer" : "not-allowed",
                opacity: input.trim() ? 1 : .55
              }}
            >
              <Send size={18}/> Send
            </button>
          </div>
        </div>
      </div>

      {/* typing dots css */}
      <style>{`
        .dot{ width:8px; height:8px; border-radius:999px; background:#64748b; display:inline-block; animation: b 1.1s infinite ease-in-out; }
        @keyframes b { 0%,80%,100%{transform:scale(0)} 40%{transform:scale(1)} }
      `}</style>
    </div>
  );
}
