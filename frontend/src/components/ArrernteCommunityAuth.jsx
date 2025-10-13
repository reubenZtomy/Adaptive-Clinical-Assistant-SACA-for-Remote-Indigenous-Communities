import React, { useState } from "react";
import { motion } from "motion/react";
import {
  Heart,
  Globe,
  Users,
  User,
  UserPlus,
  Home,
  ChevronRight,
  Shield,
} from "lucide-react";
import "./auth.css";
import bgImage from "../assets/images/sunset.jpg";

// CRA uses REACT_APP_* env vars
const API_BASE =
  process.env.REACT_APP_API_BASE ||           // ← CRA .env
  (import.meta?.env?.VITE_API_BASE) ||        // harmless fallback if copied from Vite guides
  'http://localhost:4000';                    // default



export default function ArrernteCommunityAuth({ onLoginSuccess }) {
  const [selectedLanguage, setSelectedLanguage] = useState("english");
  const [authMode, setAuthMode] = useState("login");
  const [formData, setFormData] = useState({
    firstName: "",
    lastName: "",
    email: "",
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const canSubmit =
    formData.firstName.trim() &&
    formData.lastName.trim() &&
    formData.email.trim() &&
    !isLoading;

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    const payload = {
      firstName: formData.firstName.trim(),
      lastName: formData.lastName.trim(),
      email: formData.email.trim(),
    };
    if (!payload.firstName || !payload.lastName || !payload.email) {
      setError("Please enter first name, last name and email.");
      return;
    }

    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/auth/${authMode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error || "Something went wrong");

      localStorage.setItem("swinsaca_user", JSON.stringify(data.user));
      onLoginSuccess &&
        onLoginSuccess({
          firstName: data.user.firstName,
          lastName: data.user.lastName,
        });
    } catch (err) {
      setError(err.message || "Network error");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="auth-root auth-page">
      {/* background */}
      <div className="auth-bg fixed inset-0 -z-10">
        <img src={bgImage} alt="Arrernte Community" className="auth-bg-img" />
        <div className="auth-bg-glaze auth-bg-glaze--light" />
        <div className="auth-bg-dots" />
        <div className="auth-embers">
          {[...Array(10)].map((_, i) => (
            <motion.span
              key={i}
              className="ember"
              style={{ left: `${7 + i * 8}%`, top: `${14 + i * 5.2}%` }}
              animate={{ y: [0, -20, 0], opacity: [0.15, 0.5, 0.15], scale: [1, 1.15, 1] }}
              transition={{
                duration: 5.5 + i * 0.35,
                repeat: Infinity,
                delay: i * 0.22,
                ease: "easeInOut",
              }}
            />
          ))}
        </div>
      </div>

      {/* header */}
      <header className="auth-header">
        <div className="auth-header-inner">
          <div className="auth-brand">
            <div className="ic-circle ic-circle--logo ic-circle-56">
              <Heart className="ic ic--white ic-24" strokeWidth={2.4} />
            </div>
            <div>
              <h1 className="auth-brand-title">SwinSACA</h1>
              <p className="auth-brand-sub">Community Healthcare for Everyone</p>
            </div>
          </div>

          <div className="auth-lang">
            <button
              onClick={() => setSelectedLanguage("english")}
              className={`lang-pill ${selectedLanguage === "english" ? "lang-pill--active" : ""}`}
            >
              <Globe className="ic ic-16" />
              English
            </button>
            <button
              onClick={() => setSelectedLanguage("arrernte")}
              className={`lang-pill ${selectedLanguage === "arrernte" ? "lang-pill--active" : ""}`}
            >
              <Globe className="ic ic-16" />
              Arrernte
            </button>
          </div>
        </div>
      </header>

      {/* main */}
      <main className="auth-main nopad">
        <div className="auth-card card-compact">
          <div className="auth-card-inner">
            {/* ===== scrollable BODY ===== */}
            <div className="auth-body">
              {/* top icon fully inside card */}
              <div className="auth-topicon-wrap">
                <div className="ic-circle ic-circle--users ic-circle-64">
                  <Users className="ic ic--white ic-32" strokeWidth={2.4} />
                </div>
              </div>

              <h2 className="auth-h2">Werte! Welcome</h2>
              <p className="auth-lede lede-compact">
                Join the SwinsACA community for culturally respectful healthcare services.
              </p>

              {/* tabs */}
              <div className="auth-tabs tabs-compact">
                <button
                  onClick={() => setAuthMode("login")}
                  className={`auth-tab ${authMode === "login" ? "auth-tab--active" : ""}`}
                >
                  <User className="ic ic-16" />
                  Sign In
                </button>
                <button
                  onClick={() => setAuthMode("signup")}
                  className={`auth-tab ${authMode === "signup" ? "auth-tab--active" : ""}`}
                >
                  <UserPlus className="ic ic-16" />
                  Join Us
                </button>
              </div>

              {/* form */}
              <form onSubmit={handleSubmit} className="auth-form form-compact">
                <div className="field">
                  <div className="field-title">First name</div>
                  <input
                    type="text"
                    value={formData.firstName}
                    onChange={(e) => setFormData((p) => ({ ...p, firstName: e.target.value }))}
                    placeholder="Enter your first name"
                    className="auth-input auth-input--wide"
                    required
                  />
                </div>

                <div className="field">
                  <div className="field-title">Last name</div>
                  <input
                    type="text"
                    value={formData.lastName}
                    onChange={(e) => setFormData((p) => ({ ...p, lastName: e.target.value }))}
                    placeholder="Enter your last name"
                    className="auth-input auth-input--wide"
                    required
                  />
                </div>

                <div className="field">
                  <div className="field-title">Email</div>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
                    placeholder="you@example.com"
                    className="auth-input auth-input--wide"
                    required
                  />
                </div>

                {error && <div className="auth-error">{error}</div>}

                <button type="submit" disabled={!canSubmit} className="btn-cta auth-cta cta-compact">
                  {isLoading ? (
                    <div className="auth-cta-inner">
                      <span className="auth-spinner" />
                      {authMode === "login" ? "Signing in..." : "Creating account..."}
                    </div>
                  ) : (
                    <div className="auth-cta-inner">
                      <Home className="ic ic-20" />
                      {authMode === "login" ? "Access Healthcare" : "Join Community"}
                      <ChevronRight className="ic ic-18" />
                    </div>
                  )}
                </button>
              </form>
            </div>
            {/* ===== end BODY ===== */}

            {/* ===== pinned FOOTER ===== */}
            <div className="auth-footer">
              <div className="auth-trust trust-compact">
                <div className="auth-trust-row">
                  <Shield className="ic ic-18 ic--green" />
                  <span>We keep your info private & secure</span>
                </div>
                <div className="auth-trust-row">
                  <Heart className="ic ic-20 ic--red" />
                  <span>Culturally respectful healthcare for everyone</span>
                </div>
              </div>

              <div className="ack-inline">
                SwinsACA operates on Arrernte country and acknowledges the Traditional Owners.
              </div>
            </div>
            {/* ===== end FOOTER ===== */}
          </div>
        </div>
      </main>
    </div>
  );
}
