import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Button } from "./ui/button";
import { Heart, Stethoscope, Activity, Shield, Users } from "lucide-react";
import logo from "../assets/images/logo.png";
import "./welcome.css";

export default function Welcome() {
  const navigate = useNavigate();
  const handleEnter = () => navigate("/language"); // ✅ only one definition

  const [displayText, setDisplayText] = useState("");
  const [phase, setPhase] = useState("typing-welcome");
  const [showContent, setShowContent] = useState(false);

  const welcomeText = "WELCOME";
  const werteText = "WERTE";

  useEffect(() => {
    const typeText = (text, onDone) => {
      let i = 0;
      const id = setInterval(() => {
        if (i <= text.length) {
          setDisplayText(text.slice(0, i));
          i++;
        } else {
          clearInterval(id);
          setTimeout(onDone, 800);
        }
      }, 150);
    };
    const backspaceText = (fromLength, onDone) => {
      let len = fromLength;
      const id = setInterval(() => {
        if (len >= 0) {
          setDisplayText(welcomeText.slice(0, len));
          len--;
        } else {
          clearInterval(id);
          setTimeout(onDone, 400);
        }
      }, 90);
    };

    if (phase === "typing-welcome") {
      typeText(welcomeText, () => setPhase("backspacing"));
    } else if (phase === "backspacing") {
      backspaceText(welcomeText.length - 1, () => setPhase("typing-werte"));
    } else if (phase === "typing-werte") {
      typeText(werteText, () => {
        setPhase("complete");
        setTimeout(() => setShowContent(true), 400);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  const medicalIcons = [
    { icon: Heart,        colorClass: "icon-red",    delay: 0.2, left: "18%", top: "28%" },
    { icon: Stethoscope,  colorClass: "icon-blue",   delay: 0.4, left: "34%", top: "70%" },
    { icon: Activity,     colorClass: "icon-green",  delay: 0.6, left: "55%", top: "30%" },
    { icon: Shield,       colorClass: "icon-purple", delay: 0.8, left: "72%", top: "68%" },
    { icon: Users,        colorClass: "icon-indigo", delay: 1.0, left: "82%", top: "40%" },
  ];

  return (
    <div className="welcome-screen">
      <div className="welcome-bg" aria-hidden="true" />

      <div className="welcome-icons" aria-hidden="true">
        {medicalIcons.map((item, idx) => {
          const Icon = item.icon;
          return (
            <motion.div
              key={idx}
              initial={{ opacity: 0, scale: 0, rotate: 0 }}
              animate={{
                opacity: showContent ? 0.14 : 0,
                scale: showContent ? 1 : 0,
                rotate: 360,
              }}
              transition={{
                delay: item.delay,
                duration: 2,
                rotate: { duration: 20, repeat: Infinity, ease: "linear" },
              }}
              className={`icon ${item.colorClass}`}
              style={{ left: item.left, top: item.top }}
            >
              <Icon className="icon-svg" />
            </motion.div>
          );
        })}
      </div>

      {/* Center card */}
      <div className="welcome-card">
        {/* Logo above text */}
        <img src={logo} alt="SwinSACA logo" className="welcome-logo" />

        {/* Typing text */}
        <div className="type-wrap">
          <motion.h1
            className="type-title"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
          >
            {displayText}
            <motion.span
              className="type-caret"
              animate={{ opacity: [1, 0] }}
              transition={{ duration: 0.8, repeat: Infinity }}
            />
          </motion.h1>
        </div>

        {/* Subtitle + Button */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: showContent ? 1 : 0, y: showContent ? 0 : 24 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          className="below-content"
        >
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: showContent ? 1 : 0 }}
            transition={{ delay: 0.35 }}
            className="subtitle"
          >
            Smart Adaptive Clinical Assistant
          </motion.p>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: showContent ? 1 : 0, scale: showContent ? 1 : 0.95 }}
            transition={{ delay: 0.6, duration: 0.5 }}
          >
            <Button onClick={handleEnter}>Enter SwinSACA</Button>
          </motion.div>
        </motion.div>

        {/* Pulse cross */}
        <motion.div
          className="pulse"
          initial={{ scale: 0 }}
          animate={{ scale: phase === "complete" ? [0, 1.2, 0] : 0 }}
          transition={{ duration: 2, delay: 0.5, ease: "easeInOut" }}
          aria-hidden="true"
        >
          <div className="pulse-v" />
          <div className="pulse-h" />
        </motion.div>
      </div>
    </div>
  );
}
