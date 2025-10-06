import React, { useEffect, useRef, useState } from "react";
import "./image-chat.css";
import { Mic, MicOff, Send } from "lucide-react";

export default function ImageChatbot() {
  const [messages, setMessages] = useState(() => ([
    {
      id: "welcome",
      role: "bot",
      text:
        "Werte, akweke SwinsACA-nge! 👋\nAthelhe-nge mpwerrenge artitye itye-irre mape. Nhenhe arrkweme apurte nhenhe akaltye itye-irre?",
    },
  ]));
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [recording, setRecording] = useState(false);
  const listRef = useRef(null);

  // Scroll to last item when messages change
  useEffect(() => {
    // page scroll (no inner scroll container)
    const el = document.getElementById("imgchat-end");
    el?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // After welcome, show image selector prompt
  useEffect(() => {
    setIsTyping(true);
    const t = setTimeout(() => {
      pushBot(
        "Please select the image that best matches what you’re feeling:",
        { options: SYMPTOMS }
      );
      setIsTyping(false);
    }, 600);
    return () => clearTimeout(t);
  }, []);

  function pushBot(text, extras = {}) {
    setMessages((prev) => [
      ...prev,
      { id: String(Date.now() + Math.random()), role: "bot", text, ...extras },
    ]);
  }

  function pushUser(text, payload) {
    setMessages((prev) => [
      ...prev,
      {
        id: String(Date.now() + Math.random()),
        role: "user",
        text,
        selected: payload ?? null, // {title, image, desc}
      },
    ]);
  }

  function onPick(symptom) {
    // Right-aligned card
    pushUser(symptom.title, symptom);

    // Bot follow-up
    setIsTyping(true);
    setTimeout(() => {
      pushBot(
        `I understand you have **${symptom.title}**. Can you tell me:\n• How severe is the pain (1–10)?\n• When did it start?\n• Does light or sound make it worse?`
      );
      setIsTyping(false);
    }, 750);
  }

  function sendText() {
    const t = input.trim();
    if (!t) return;
    pushUser(t);
    setInput("");

    setIsTyping(true);
    setTimeout(() => {
      const reply = FOLLOWUPS[Math.floor(Math.random() * FOLLOWUPS.length)];
      pushBot(reply);
      setIsTyping(false);
    }, 600);
  }

  // Demo mic (you can wire to STT later)
  function toggleMic() {
    setRecording((v) => !v);
    if (!recording) {
      setTimeout(() => {
        pushUser("Voice: sore throat and cough.");
        setIsTyping(true);
        setTimeout(() => {
          pushBot("Thanks. When did it start? Any fever?");
          setIsTyping(false);
        }, 700);
      }, 1200);
    }
  }

  return (
    <div className="imgchat-page">
      {/* Page header (outside the card) */}
      <header className="imgchat-header">
        <h1 className="h-title">SwinSACA Mpwerrenge Arlkweme</h1>
        <p className="h-sub">Uterne apurte mapeke nhenhe arrkweme anthurre kwatye arlkweme</p>
      </header>

      {/* Chat card (inside the dotted background) */}
      <main className="imgchat-card">
        {/* Welcome + conversation */}
        <section className="conv" ref={listRef}>
          {messages.map((m) =>
            m.role === "bot" ? (
              <div key={m.id} className="row row-left">
                <div className="av av-bot"><span className="av-dot" /></div>
                <div className="bubble bubble-bot">
                  <p className="btext" dangerouslySetInnerHTML={{ __html: toHtml(m.text) }} />
                  {m.options && (
                    <div className="opt-grid">
                      {m.options.map((opt) => (
                        <button
                          key={opt.id}
                          className="opt-card"
                          onClick={() => onPick(opt)}
                        >
                          <img src={opt.image} alt={opt.title} />
                          <div className="opt-title">{opt.title}</div>
                          <div className="opt-desc">{opt.desc}</div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div key={m.id} className="row row-right">
                <div className="bubble bubble-user">
                  {m.selected ? (
                    <div className="user-card">
                      <img src={m.selected.image} alt={m.selected.title} />
                      <div>
                        <div className="user-card-title">{m.selected.title}</div>
                        <div className="user-card-desc">{m.selected.desc}</div>
                        <div className="user-card-tag">Selected Selection</div>
                      </div>
                    </div>
                  ) : (
                    <p className="btext">{m.text}</p>
                  )}
                </div>
                <div className="av av-user"><span className="av-dot" /></div>
              </div>
            )
          )}

          {isTyping && (
            <div className="row row-left">
              <div className="av av-bot"><span className="av-dot" /></div>
              <div className="bubble bubble-bot">
                <div className="typing">
                  <span/><span/><span/>
                </div>
              </div>
            </div>
          )}
          <div id="imgchat-end" />
        </section>
      </main>

      {/* Sticky composer across the page bottom */}
      <footer className="imgchat-composer">
        <button
          className={`mic ${recording ? "on" : ""}`}
          onClick={toggleMic}
          title="Speak"
          aria-label="Mic"
        >
          {recording ? <MicOff size={18} /> : <Mic size={18} />}
        </button>

        <input
          className="input"
          placeholder="Type your message.. (Enter to send)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              sendText();
            }
          }}
        />

        <button
          className="send"
          onClick={sendText}
          disabled={!input.trim()}
          title="Send"
        >
          <Send size={16} />
          <span>Send</span>
        </button>
      </footer>
    </div>
  );
}

/* ---- data ---- */
const SYMPTOMS = [
  { id: "body", title: "Body Symptoms",
    image: "https://images.unsplash.com/photo-1520975954732-35dd22c1573a?q=80&w=900&auto=format&fit=crop"},
   
  { id: "headache", title: "Angkentye irreme",
    image: "https://images.unsplash.com/photo-1619694108677-8a4dc3bd9875?q=80&w=900&auto=format&fit=crop"},
    
  { id: "eye", title: "ayele angkentye",
    image: "https://images.unsplash.com/photo-1631042000681-8638445d15ef?q=80&w=900&auto=format&fit=crop"},
    
  { id: "ear", title: "wertye irreme",
    image: "https://images.unsplash.com/photo-1484515991647-c5760fcecfc7?q=80&w=900&auto=format&fit=crop",
     },

  { id: "tooth", title: "Aratye irreme",
    image: "https://images.unsplash.com/photo-1525072124541-6237cc0b2355?q=80&w=900&auto=format&fit=crop"},
   
  { id: "throat", title: "kwementye irreme",
    image: "https://images.unsplash.com/photo-1603398938378-e54eab446dde?q=80&w=900&auto=format&fit=crop"},
    
  { id: "breathing", title: "Breathing Problems",
    image: "https://images.unsplash.com/photo-1526253038957-bce54e05968f?q=80&w=900&auto=format&fit=crop",
   },
  { id: "chest", title: "ngkwerre irreme",
    image: "https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?q=80&w=900&auto=format&fit=crop",
    },

  { id: "skin", title: "akweke angkentye",
    image: "https://images.unsplash.com/photo-1535930749574-1399327ce78f?q=80&w=900&auto=format&fit=crop",
    },
  { id: "fever", title: "Fever",
    image: "https://images.unsplash.com/photo-1628510136492-6b0d927081e0?q=80&w=900&auto=format&fit=crop",
    desc: "High temperature or feeling hot" },
  { id: "dizzy", title: "antye angkentye",
    image: "https://images.unsplash.com/photo-1588392382834-a891154bca4d?q=80&w=900&auto=format&fit=crop",
     },
];

const FOLLOWUPS = [
  "Thanks! When did this start?",
  "Got it. Could you rate the severity (1–10)?",
  "Understood. Are there other symptoms?",
];

function toHtml(text) {
  return (text || "")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}
