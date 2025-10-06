import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Mic, MessageSquare, Image as ImageIcon } from "lucide-react";
import React from "react";

export default function ServicePage() {
  const navigate = useNavigate();

  const services = [
    {
      id: "voice",
      title: "Voice Input",
      description:
        "Speak your symptoms in your language and we’ll guide you step by step.",
      Icon: Mic,
      gradient: "linear-gradient(135deg,#a855f7,#7c3aed,#4338ca)", // purple → indigo
      softBg: "rgba(168,85,247,0.10)",
      border: "rgba(168,85,247,0.30)",
    },
    {
      id: "text",
      title: "Text Input",
      description:
        "Type your concerns and chat with SwinSACA for a quick triage.",
      Icon: MessageSquare,
      gradient: "linear-gradient(135deg,#3b82f6,#2563eb,#0891b2)", // blue → cyan
      softBg: "rgba(59,130,246,0.10)",
      border: "rgba(59,130,246,0.30)",
    },
    {
      id: "image",
      title: "Image Input",
      description:
        "Choose from symptom images if speaking or typing is difficult.",
      Icon: ImageIcon,
      gradient: "linear-gradient(135deg,#22c55e,#059669,#0f766e)", // green → teal
      softBg: "rgba(34,197,94,0.10)",
      border: "rgba(34,197,94,0.30)",
    },
  ];

  const onServiceSelected = (service) => {
    if (service === "text") navigate("/chat");
    else if (service === "voice") navigate("/voice");
    else if (service === "image") navigate("/image");
  };

  return (
    <div style={page}>
      {/* subtle decorative bits */}
      <div style={decCircle1} />
      <div style={decSquare} />
      <div style={decCircle2} />

      <div style={container}>
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ display: "flex", justifyContent: "center", marginBottom: 20 }}>
            <div style={logoOrb}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                <path d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" stroke="#fff" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
          </div>

          <h1 style={title}>Our Services</h1>
          <div style={divider} />
          <p style={subtitle}>
            Choose how you’d like to share your symptoms.
          </p>
        </div>

        {/* Cards */}
        <div style={grid}>
          {services.map((svc, idx) => (
            <motion.div
              key={svc.id}
              initial={{ opacity: 0, y: 20, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ duration: 0.5, delay: idx * 0.12 }}
              whileHover={{ y: -10, scale: 1.02 }}
            >
              <div style={{
                ...card,
                background: "rgba(255,255,255,0.95)",
                border: `2px solid ${svc.border}`,
                boxShadow: "0 18px 40px rgba(0,0,0,0.08)",
              }}>
                <div style={{ padding: "26px 22px 10px", textAlign: "center" }}>
                  <div style={{ display: "flex", justifyContent: "center", marginBottom: 18 }}>
                    <div style={{
                      width: 80, height: 80, borderRadius: "9999px",
                      background: svc.gradient,
                      boxShadow: "0 14px 30px rgba(0,0,0,.2)",
                      display: "grid", placeItems: "center",
                      position: "relative",
                    }}>
                      <svc.Icon color="#fff" size={36} />
                      <div style={{
                        position: "absolute", inset: 0, borderRadius: "9999px",
                        background: "rgba(255,255,255,.24)", opacity: 0,
                        transition: "opacity .3s",
                      }}
                      className="svc-glow"
                      />
                    </div>
                  </div>

                  <h3 style={cardTitle}>{svc.title}</h3>
                  <p style={cardDesc}>{svc.description}</p>
                </div>

                <div style={{ padding: "0 22px 24px" }}>
                  <button
                    onClick={() => onServiceSelected(svc.id)}
                    style={{
                      width: "100%", padding: "14px 16px",
                      borderRadius: 14, border: "2px solid rgba(255,255,255,.18)",
                      color: "#fff", fontWeight: 600, fontSize: 16, cursor: "pointer",
                      background: svc.gradient, boxShadow: "0 12px 30px rgba(0,0,0,.15)",
                      transition: "transform .25s, box-shadow .25s",
                    }}
                    onMouseEnter={(e)=>{ e.currentTarget.style.boxShadow="0 18px 40px rgba(0,0,0,.25)"; e.currentTarget.style.transform="scale(1.02)"; }}
                    onMouseLeave={(e)=>{ e.currentTarget.style.boxShadow="0 12px 30px rgba(0,0,0,.15)"; e.currentTarget.style.transform="scale(1)"; }}
                  >
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
                      <svc.Icon color="#fff" size={20} />
                      {svc.title}
                    </span>
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        <div style={{ textAlign: "center", marginTop: 28 }}>
          <p style={{ color: "rgba(55,65,81,.8)", marginBottom: 10 }}>
            Choose the method that works best for you
          </p>
          <div style={{ display:"flex", justifyContent:"center", gap: 8 }}>
            <div style={{...dot, background:"#fb923c"}} />
            <div style={{...dot, background:"#f87171"}} />
            <div style={{...dot, background:"#facc15"}} />
          </div>
        </div>
      </div>
    </div>
  );
}

/* ------------ styles (inline objects) ------------ */

const page = {
  minHeight: "100vh",
  position: "relative",
  padding: 16,
  // background image layer + soft overlay similar to your Figma
  backgroundImage:
    "linear-gradient(rgba(244,241,235,0.95), rgba(250,247,242,0.95)), url('https://images.unsplash.com/photo-1652355069631-2bc25d4138cc?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxhYm9yaWdpbmFsJTIwYXJ0JTIwcGF0dGVybnMlMjBpbmRpZ2Vub3VzfGVufDF8fHx8MTc1OTM3Nzk5Mnww&ixlib=rb-4.1.0&q=80&w=1080')",
  backgroundSize: "cover",
  backgroundPosition: "center",
  backgroundAttachment: "fixed",
};

const container = {
  maxWidth: 1150,
  margin: "0 auto",
  padding: "48px 0",
};

const logoOrb = {
  width: 80, height: 80, borderRadius: "9999px",
  background: "linear-gradient(135deg,#fb923c,#ef4444,#f59e0b)",
  display: "grid", placeItems: "center",
  boxShadow: "0 18px 40px rgba(0,0,0,.25)",
};

const title = {
  fontSize: 42,
  color: "#0b1220",
  margin: "16px 0 12px",
  textShadow: "0 2px 0 rgba(255,255,255,.6)",
};

const divider = {
  width: 120, height: 6,
  borderRadius: 999,
  background: "linear-gradient(90deg,#fb923c,#ef4444)",
  margin: "0 auto 18px",
};

const subtitle = {
  fontSize: 18,
  color: "rgba(17,24,39,.8)",
  margin: "0 auto",
  maxWidth: 760,
  lineHeight: 1.6,
};

const grid = {
  display: "grid",
  gridTemplateColumns: "repeat(1, minmax(0, 1fr))",
  gap: 22,
  maxWidth: 1000,
  margin: "0 auto",
};

if (typeof window !== "undefined") {
  const mq = window.matchMedia("(min-width: 992px)");
  if (mq.matches) {
    grid.gridTemplateColumns = "repeat(3, minmax(0, 1fr))";
  }
}

const card = {
  borderRadius: 18,
  overflow: "hidden",
  backdropFilter: "blur(6px)",
};

const cardTitle = {
  fontSize: 22,
  margin: "4px 0 8px",
  color: "#0b1220",
};

const cardDesc = {
  fontSize: 16,
  color: "rgba(31,41,55,.8)",
  lineHeight: 1.6,
};

const dot = {
  width: 10, height: 10, borderRadius: "9999px",
  animation: "saca-pulse 1.5s infinite",
  opacity: 0.9,
};

/* decorative shapes */
const decCircle1 = {
  position: "absolute", top: 64, left: 64,
  width: 48, height: 48, borderRadius: "9999px",
  border: "4px solid rgba(251,146,60,.6)",
  opacity: 0.5, animation: "saca-pulse 2s infinite",
};
const decSquare = {
  position: "absolute", bottom: 84, left: 56,
  width: 64, height: 64, transform: "rotate(45deg)",
  border: "4px solid rgba(250,204,21,.6)",
  opacity: 0.4, animation: "saca-spin 12s linear infinite",
};
const decCircle2 = {
  position: "absolute", bottom: 96, right: 64,
  width: 40, height: 40, borderRadius: "9999px",
  background: "rgba(249,115,22,.6)",
  opacity: 0.5, animation: "saca-pulse 2s .3s infinite",
};

/* inject keyframes once */
if (typeof document !== "undefined" && !document.getElementById("saca-services-kf")) {
  const style = document.createElement("style");
  style.id = "saca-services-kf";
  style.textContent = `
  @keyframes saca-pulse { 
    0%,100%{ transform: scale(.95); opacity:.8 } 
    50%{ transform: scale(1.05); opacity:1 } 
  }
  @keyframes saca-spin { 
    0%{ transform: rotate(0deg) } 
    100%{ transform: rotate(360deg) } 
  }
  `;
  document.head.appendChild(style);
}
