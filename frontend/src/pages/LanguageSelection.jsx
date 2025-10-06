import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Globe, Users } from "lucide-react";
import { Button } from "../components/ui/button"; // adjust if your Button path differs
import "./language.css";

export default function LanguageSelection() {
  const navigate = useNavigate();

  const onLanguageSelect = useCallback((lang) => {
    try {
      localStorage.setItem("saca_language", lang);
    } catch {}
    if (lang === "english") {
    navigate("/services"); // English version
  } else if (lang === "arrernte") {
    navigate("/arr-services"); // Arrernte version
  }
}, [navigate]);

  return (
    <div 
      className="lang-root"
      style={{
        backgroundImage: `
          linear-gradient(rgba(0,0,0,0.45), rgba(0,0,0,0.45)),
          url('https://images.unsplash.com/photo-1465057174976-39931c6308c9?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1600')
        `
      }}
    >
      {/* subtle overlay pattern */}
      <div 
        className="lang-overlay"
        style={{
          backgroundImage: `
            url('https://images.unsplash.com/photo-1696252908959-04aa7a03a97e?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&q=80&w=1080')
          `
        }}
      />

      <div className="lang-wrap">
        {/* Title */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="lang-hero"
        >
          <div className="lang-hero-icon">
            <Globe className="icon-hero" />
          </div>

          <h1 className="lang-title">Choose Language</h1>
          <h2 className="lang-subtitle">Arrernenge Artenge</h2>
          <p className="lang-desc">Select your preferred language to continue</p>
        </motion.div>

        {/* Cards */}
        <div className="lang-grid">
          {/* English */}
          <motion.div
            initial={{ opacity: 0, x: -50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.98 }}
          >
            <div 
              className="lang-card lang-card--blue"
              onClick={() => onLanguageSelect("english")}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onLanguageSelect("english")}
            >
              <div className="lang-card-body">
                <div className="lang-card-badge lang-badge--blue">🇬🇧</div>
                <h3 className="lang-card-title">English</h3>
                <p className="lang-card-text">Continue in English</p>
                <Button className="lang-btn lang-btn--blue">Select English</Button>
              </div>
            </div>
          </motion.div>

          {/* Arrernte */}
          <motion.div
            initial={{ opacity: 0, x: 50 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.5 }}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.98 }}
          >
            <div 
              className="lang-card lang-card--orange"
              onClick={() => onLanguageSelect("arrernte")}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onLanguageSelect("arrernte")}
            >
              <div className="lang-card-body">
                <div className="lang-card-badge lang-badge--orange">
                  <Users className="icon-users" />
                </div>
                <h3 className="lang-card-title">Arrernte</h3>
                <h4 className="lang-card-local">Arrernenge Artenge</h4>
                <p className="lang-card-text">Continue in Arrernte language</p>
                <Button className="lang-btn lang-btn--orange">Arrernte-ketye</Button>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Cultural note */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.7 }}
          className="lang-note"
        >
          <div className="lang-note-box">
            <p className="lang-note-line">
              Welcome to country. This app respects and honors Arrernte culture.
            </p>
            <p className="lang-note-aux">
              Arrernte anenhe-kenhe arrerne mape-ante.
            </p>
          </div>
        </motion.div>

        {/* Decorative pulses */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2, delay: 1 }}
          className="pulse pulse--lg"
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2, delay: 1.2 }}
          className="pulse pulse--md"
        />
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 2, delay: 1.4 }}
          className="pulse pulse--sm"
        />
      </div>
    </div>
  );
}