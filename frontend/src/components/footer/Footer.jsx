import "./footer.css";
import logo from "../../assets/images/logo.png"; // update if your path differs
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="ft-root">
      <div className="ft-wrap">
        {/* Brand */}
        <div className="ft-col ft-brand">
          <img src={logo} alt="Medic logo" className="ft-logo" />
          <p className="ft-tagline">
            Swin Smart Adaptive Clinical Assistant
          </p>
          <div className="ft-social">
  <a href="#" aria-label="Facebook" className="ft-social-btn">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 320 512">
      <path d="M279.14 288l14.22-92.66h-88.91V127.41c0-25.35 12.42-50.06 52.24-50.06H293V6.26S259.5 0 225.36 0c-73.51 0-121.36 44.38-121.36 124.72V195.3H22.89V288h81.11v224h100.17V288z"/>
    </svg>
  </a>

  <a href="#" aria-label="Twitter" className="ft-social-btn">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 512 512">
      <path d="M459.4 151.7c.3 4.5 .3 9.1 .3 13.6 0 138.7-105.6 298.5-298.5 298.5-59.5 0-114.9-17.2-161.5-47.1 8.4 .9 16.8 1.3 25.6 1.3 49.1 0 94.2-16.8 130-45.6-46-1-84.8-31.1-98.1-72.7 6.5 1 13 1.6 20 1.6 9.4 0 18.7-1.3 27.4-3.6-48.1-9.7-84.2-52.1-84.2-103.1v-1.3c14.1 7.8 30.3 12.6 47.5 13.3-28.3-18.9-47-51.1-47-87.7 0-19.4 5.2-37.1 14.1-52.4 51.6 63.3 129.1 104.5 216 108.9-1.6-7.8-2.6-16.1-2.6-24.4 0-58.7 47.5-106.2 106.2-106.2 30.6 0 58.4 12.6 77.7 33 24.2-4.5 47.2-13.6 67.8-25.8-7.8 24.5-24.4 45.5-46 58.7 21.6-2.3 42.3-8.1 61.3-16.2-14.3 21.3-32.2 39.9-52.6 54.7z"/>
    </svg>
  </a>

  <a href="#" aria-label="YouTube" className="ft-social-btn">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 576 512">
      <path d="M549.7 124.1c-6.3-23.7-24.9-42.3-48.6-48.6C464.6 64 288 64 288 64S111.4 64 74.9 75.5c-23.7 6.3-42.3 24.9-48.6 48.6C16 161.4 16 256 16 256s0 94.6 10.3 131.9c6.3 23.7 24.9 42.3 48.6 48.6C111.4 448 288 448 288 448s176.6 0 213.1-11.5c23.7-6.3 42.3-24.9 48.6-48.6C560 350.6 560 256 560 256s0-94.6-10.3-131.9zM232 336V176l142.1 80L232 336z"/>
    </svg>
  </a>

  <a href="#" aria-label="LinkedIn" className="ft-social-btn">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 448 512">
      <path d="M100.28 448H7.4V148.9h92.88zm-46.44-338a53.67 53.67 0 1 1 53.67-53.67 53.67 53.67 0 0 1-53.67 53.67zM447.9 448h-92.4V304.1c0-34.3-12.3-57.7-43.2-57.7-23.5 0-37.6 15.8-43.8 31.1-2.2 5.4-2.7 12.9-2.7 20.5V448h-92.4s1.2-268.2 0-296.1h92.4v41.9c12.3-19 34.4-46.1 83.9-46.1 61.3 0 107.2 39.9 107.2 125.5z"/>
    </svg>
  </a>
</div>

        </div>

        {/* Quick Links */}
        <div className="ft-col">
          <h5 className="ft-title">Quick Links</h5>
          <ul className="ft-list">
            <li><Link to="/navbar">Home</Link></li>
            <li><a href="#about">About</a></li>
            <li><Link to="/services">Services</Link></li>
            <li><a href="#faq">FAQ</a></li>
          </ul>
        </div>

        {/* Services */}
        <div className="ft-col">
          <h5 className="ft-title">Services</h5>
          <ul className="ft-list">
            <li><Link to="/voice">Voice Input</Link></li>
            <li><Link to="/text">Text Input</Link></li>
            <li><Link to="/image">Image Input</Link></li>
          </ul>
        </div>

        {/* Contact */}
        <div className="ft-col">
          <h5 className="ft-title">Contact</h5>
          <ul className="ft-list">
            <li>📍 Alice Springs, NT</li>
            <li>✉️ hello@saca.example</li>
            <li>☎️ (08) 12345678</li>
           
          </ul>
          <button className="ft-cta" onClick={() => window.scrollTo({top:0, behavior:"smooth"})}>
            Back to top
          </button>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="ft-bar">
        <p>© {new Date().getFullYear()} SACA · All rights reserved</p>
        <div className="ft-legal">
          <a href="#privacy">Privacy</a>
          <span>•</span>
          <a href="#terms">Terms</a>
        </div>
      </div>
    </footer>
  );
}
