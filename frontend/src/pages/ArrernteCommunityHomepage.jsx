import React from "react";
import {
  Globe,
  Mic,
  Type,
  Camera,
  Shield,
  Clock,
  Star,
  MapPin,
  Mail,
  Send,
  Facebook,
  Twitter,
  Instagram,
  Heart,
} from "lucide-react";
import outbackImg from "../assets/images/outback.jpg";
import "./ArrernteCommunityHomepage.css";

export default function ArrernteCommunityHomepage() {
  return (
    <div className="aca-root">
      {/* Top Bar */}
      <div className="aca-topbar">
        <div className="aca-topbar-left">
          <div className="aca-logo">
            <Heart size={22} strokeWidth={2.5} />
          </div>
          <div className="aca-brand">
            <div className="aca-brand-title">SwinSACA</div>
            <div className="aca-brand-sub">Community Healthcare for Everyone</div>
          </div>
        </div>

        <div className="aca-lang">
          <button className="aca-lang-btn">
            <Globe size={16} className="aca-globe" />
            <span>English</span>
          </button>
          <button className="aca-lang-btn outline">
            <Globe size={16} className="aca-globe" />
            <span>Arrernte</span>
          </button>
        </div>
      </div>

      {/* Hero Section */}
      <header className="aca-hero">
        <div className="aca-hero-overlay" />
        <div className="aca-hero-inner">
          <h1 className="aca-quote">
            <span className="q-orange">"Every voice matters,</span>
            <br />
            <span className="q-red">every life deserves care"</span>
          </h1>

          <h2 className="aca-welcome">Welcome! Get Healthcare Help Your Way</h2>

          <p className="aca-lede">
            At SwinSACA, we put people first — combining intelligence and compassion
            to transform patient voices into personalized insights that drive smarter
            healthcare decisions and improve quality of life.
          </p>

          <p className="aca-sublede">
            Communicate with us using voice, text, or images — whatever works best
            for you. Culturally respectful healthcare services for the Arrernte community.
          </p>
        </div>
      </header>

      {/* Communication Options */}
      <section
        className="aca-communicate"
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.7), rgba(255,255,255,0.7)), url(${outbackImg})`,
          backgroundSize: "cover",
          backgroundPosition: "center",
          backgroundAttachment: "fixed",
          backgroundRepeat: "no-repeat",
        }}
      >
        <h3 className="aca-comm-title">How Would You Like to Communicate?</h3>

        <div className="aca-card-grid">
          <article className="aca-card">
            <div className="aca-icon-circle">
              <Mic size={48} />
            </div>
            <h4 className="aca-card-title">Voice Input</h4>
            <p className="aca-card-text">
              Speak in your language — we understand both English and Arrernte.
            </p>
          </article>

          <article className="aca-card">
            <div className="aca-icon-circle green">
              <Type size={48} />
            </div>
            <h4 className="aca-card-title">Text Input</h4>
            <p className="aca-card-text">
              Type your symptoms or health concerns in simple words.
            </p>
          </article>

          <article className="aca-card">
            <div className="aca-icon-circle purple">
              <Camera size={48} />
            </div>
            <h4 className="aca-card-title">Image Input</h4>
            <p className="aca-card-text">
              Show us pictures of your symptoms or point to body areas.
            </p>
          </article>
        </div>
      </section>

      {/* Features */}
      <section className="aca-features">
        <div className="aca-feature">
          <div className="aca-badge">
            <Shield size={32} />
          </div>
          <h5 className="aca-feature-title">Safe & Private</h5>
          <p className="aca-feature-text">
            Your health information is kept private and secure.
          </p>
        </div>

        <div className="aca-feature">
          <div className="aca-badge">
            <Clock size={32} />
          </div>
          <h5 className="aca-feature-title">24/7 Available</h5>
          <p className="aca-feature-text">
            Get help anytime, day or night.
          </p>
        </div>

        <div className="aca-feature">
          <div className="aca-badge">
            <Star size={32} />
          </div>
          <h5 className="aca-feature-title">Cultural Respect</h5>
          <p className="aca-feature-text">
            Healthcare that understands and respects Arrernte culture.
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="aca-footer">
        <div className="aca-footer-inner">
          <div className="aca-foot-left">
            <div className="aca-footer-brand">
              <div className="aca-footer-logo">
                <Heart size={22} strokeWidth={2.5} />
              </div>
              <div>
                <div className="aca-foot-title">SwinSACA</div>
                <div className="aca-foot-sub">Community Healthcare</div>
              </div>
            </div>

            <p className="aca-foot-desc">
              SwinSACA provides culturally sensitive healthcare services for the
              Arrernte community. We combine traditional wisdom with modern healthcare,
              respecting culture and delivering quality care.
            </p>

            <div className="aca-socials">
              <a href="#" className="aca-social">
                <Facebook size={18} />
              </a>
              <a href="#" className="aca-social">
                <Twitter size={18} />
              </a>
              <a href="#" className="aca-social">
                <Instagram size={18} />
              </a>
            </div>

            <div className="aca-copy">© 2024 SwinSACA. All rights reserved.</div>
          </div>

          <div className="aca-foot-right">
            <h6 className="aca-contact-title">Contact</h6>

            <div className="aca-contact-row">
              <MapPin size={18} />
              <span>Alice Springs, NT</span>
            </div>

            <div className="aca-contact-row">
              <Mail size={18} />
              <span>hello@swinsaca.org.au</span>
            </div>

            <div className="aca-contact-row">
              <Send size={18} />
              <span>Traditional Arrernte Land</span>
            </div>

            <div className="aca-legal">
              <a href="#">Privacy Policy</a>
              <a href="#">Terms of Service</a>
              <a href="#">Cultural Acknowledgment</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
