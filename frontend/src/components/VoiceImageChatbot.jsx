// src/components/VoiceImageChatbot.jsx
import { useEffect, useRef, useState } from "react";

// Minimal icon fallbacks (remove if you install lucide-react and swap them)
const Icon = {
  Mic:   (p) => (<svg viewBox="0 0 24 24" width="20" height="20" {...p}><path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" stroke="currentColor" fill="none"/><path d="M19 11a7 7 0 0 1-14 0" stroke="currentColor" fill="none"/><path d="M12 19v3" stroke="currentColor"/></svg>),
  MicOff:(p) => (<svg viewBox="0 0 24 24" width="20" height="20" {...p}><path d="M1 1l22 22" stroke="currentColor"/><path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-5.12-2.1" stroke="currentColor" fill="none"/><path d="M19 11a7 7 0 0 1-11.17 5.52" stroke="currentColor" fill="none"/></svg>),
  Image: (p) => (<svg viewBox="0 0 24 24" width="20" height="20" {...p}><rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" fill="none"/><circle cx="8.5" cy="8.5" r="2" stroke="currentColor" fill="none"/><path d="M21 16l-5-5-6 6-2-2-5 5" stroke="currentColor" fill="none"/></svg>),
  Send:  (p) => (<svg viewBox="0 0 24 24" width="20" height="20" {...p}><path d="M22 2L11 13" stroke="currentColor"/><path d="M22 2l-7 20-4-9-9-4 20-7Z" stroke="currentColor" fill="none"/></svg>),
  X:     (p) => (<svg viewBox="0 0 24 24" width="18" height="18" {...p}><path d="M18 6 6 18M6 6l12 12" stroke="currentColor"/></svg>),
  Bot:   (p) => (<svg viewBox="0 0 24 24" width="18" height="18" {...p}><rect x="4" y="7" width="16" height="12" rx="2" stroke="currentColor" fill="none"/><path d="M12 3v4" stroke="currentColor"/><circle cx="9" cy="13" r="1" fill="currentColor"/><circle cx="15" cy="13" r="1" fill="currentColor"/></svg>),
  User:  (p) => (<svg viewBox="0 0 24 24" width="18" height="18" {...p}><circle cx="12" cy="8" r="4" stroke="currentColor" fill="none"/><path d="M4 21a8 8 0 0 1 16 0" stroke="currentColor" fill="none"/></svg>),
};

function Bubble({ role, text }) {
  const isUser = role === "user";
  return (
    <div className={`w-full flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm shadow-sm ${
        isUser ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-900"
      }`}>
        <div className="flex items-center gap-2 mb-1 opacity-70">
          <span className="inline-flex items-center justify-center rounded-full bg-black/5 text-gray-700 p-1">
            {isUser ? <Icon.User /> : <Icon.Bot />}
          </span>
          <span className="text-xs font-medium">{isUser ? "You" : "Assistant"}</span>
        </div>
        <p className="leading-relaxed whitespace-pre-wrap">{text}</p>
      </div>
    </div>
  );
}

function VoiceBars({ active=false }) {
  const bars = new Array(16).fill(0);
  return (
    <div className="flex items-end gap-[3px] h-8 overflow-hidden">
      {bars.map((_, i) => (
        <span
          key={i}
          className={`w-[3px] rounded-full bg-current inline-block ${active ? "animate-pulse" : "opacity-40"}`}
          style={{ height: active ? `${8 + ((i*7)%24)}px` : "10px" }}
        />
      ))}
    </div>
  );
}

function ImagePicker({ open, onClose, onPick, images=[] }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-3xl rounded-2xl bg-white p-4 shadow-xl">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Choose an image</h3>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-gray-100">
            <Icon.X />
          </button>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {images.map((src, idx) => (
            <button
              key={idx}
              onClick={() => onPick?.(src)}
              className="group relative overflow-hidden rounded-xl border bg-gray-50 hover:shadow-md"
            >
              <img src={src} alt={`option-${idx}`} className="aspect-square w-full object-cover" />
              <span className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 bg-black/20 transition" />
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function VoiceImageChatbot({
  title = "SwinSACA Chat",
  subtitle = "This tool does not replace a clinician. In an emergency, call local services.",
  onSend, onPickImage, onStartRecording, onStopRecording,
  placeholder = "Type your message… (Enter to send)",
  initialMessages = [
    { role: "assistant", text: "Hi, welcome to SwinSACA 👋\nTell me your main symptom or tap the mic/image to begin." }
  ],
  sampleImages = [
    "https://images.unsplash.com/photo-1504439468489-c8920d796a29?q=80&w=640&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1516574187841-cb9cc2ca948b?q=80&w=640&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1559102877-4a2cc0a5356f?q=80&w=640&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1537368910025-700350fe46c7?q=80&w=640&auto=format&fit=crop",
  ],
  className = ""
}) {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [showPicker, setShowPicker] = useState(false);
  const [recording, setRecording] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages.length]);

  function handleSend() {
    const text = input.trim();
    if (!text) return;
    setMessages((prev) => [...prev, { role: "user", text }]);
    setInput("");
    onSend?.(text);
  }

  function handlePick(url) {
    setShowPicker(false);
    setMessages((prev) => [...prev, { role: "user", text: `[Image selected] ${url}` }]);
    onPickImage?.(url);
  }

  function toggleRecord() {
    if (!recording) {
      setRecording(true);
      onStartRecording?.();
    } else {
      setRecording(false);
      onStopRecording?.();
    }
  }

  return (
    <div className={`w-full h-screen flex flex-col bg-gradient-to-br from-orange-50 via-yellow-50 to-red-50`}>
      {/* Header */}
      <div className="bg-white/95 backdrop-blur-sm border-b border-orange-200 p-4">
        <h1 className="text-xl font-semibold text-gray-900 mb-1">{title}</h1>
        <p className="text-sm text-gray-600">{subtitle}</p>
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-3">
        {messages.map((m, i) => <Bubble key={i} role={m.role} text={m.text} />)}
      </div>

      {/* Input Row */}
      <div className="bg-white/95 backdrop-blur-sm border-t border-orange-200 p-4">
        <div className="flex items-end gap-2">
          <button
            type="button"
            onClick={toggleRecord}
            className={`shrink-0 inline-flex items-center justify-center rounded-2xl border px-3 py-2 text-sm hover:bg-gray-50 transition ${recording ? "border-red-500 text-red-600" : "border-gray-200 text-gray-700"}`}
            aria-pressed={recording}
          >
            {recording ? <Icon.MicOff className="mr-2" /> : <Icon.Mic className="mr-2" />}
            {recording ? "Stop" : "Voice"}
          </button>

          <div className="flex-1 rounded-2xl border border-gray-200 px-3 py-2">
            <textarea
              rows={1}
              className="block w-full resize-none bg-transparent outline-none text-sm placeholder:text-gray-400"
              placeholder={placeholder}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
            />
            {recording && (
              <div className="mt-2 flex items-center gap-2 text-blue-600">
                <VoiceBars active />
                <span className="text-xs">Recording… speak clearly</span>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={() => setShowPicker(true)}
            className="shrink-0 inline-flex items-center justify-center rounded-2xl border border-gray-200 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            <Icon.Image className="mr-2" />
            Image
          </button>

          <button
            type="button"
            onClick={handleSend}
            className="shrink-0 inline-flex items-center justify-center rounded-2xl bg-blue-500 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-600"
          >
            <Icon.Send className="mr-2" />
            Send
          </button>
        </div>

        <p className="mt-2 text-[11px] text-center text-yellow-700 bg-yellow-50 border border-yellow-200 rounded-xl px-3 py-1">
          ⚠️ For information only. Always consult healthcare professionals for medical advice.
        </p>
      </div>

      {/* Image picker overlay */}
      <ImagePicker open={showPicker} onClose={() => setShowPicker(false)} onPick={handlePick} images={sampleImages} />
    </div>
  );
}
