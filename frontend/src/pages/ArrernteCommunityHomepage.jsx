import React from "react";
import "./ArrernteCommunityHomepage.css"; // Import CSS for styling

function ArrernteCommunityHomepage() {
  return (
    <div className="ArrernteCommunityHomepage">
      {/* Header Section */}
      <header className="header">
        <div className="container">
          <h1>"Every voice matters, every life deserves care"</h1>
          <p>Welcome! Get Healthcare Help Your Way</p>
          <p>
            At SwinSACA, we put people first — combining intelligence and
            compassion to transform patient voices into personalized insights that
            drive smarter healthcare decisions and improve quality of life.
          </p>
        </div>
      </header>

      {/* Communication Options Section */}
      <section className="communication">
        <h2>How Would You Like to Communicate?</h2>
        <div className="input-options">
          <div className="option">
            <button>Voice Input</button>
            <p>Speak in your language - we understand both English and Arrernte</p>
          </div>
          <div className="option">
            <button>Text Input</button>
            <p>Type your symptoms or health concerns in simple words</p>
          </div>
          <div className="option">
            <button>Image Input</button>
            <p>Show us pictures of your symptoms or point to body areas</p>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="benefits">
        <div className="benefit">
          <h3>Safe & Private</h3>
          <p>Your health information is kept private and secure</p>
        </div>
        <div className="benefit">
          <h3>24/7 Available</h3>
          <p>Get help anytime, day or night</p>
        </div>
        <div className="benefit">
          <h3>Cultural Respect</h3>
          <p>Healthcare that understands and respects Arrernte culture</p>
        </div>
      </section>

     
{/* Footer Section */}
<footer className="footer">
  <div className="container">
    <div className="footer-content">
      <div className="footer-left">
        <h1>SwinSACA</h1>
        <p>Community Healthcare</p>
        <p className="footer-description">
          SwinSACA provides culturally sensitive healthcare services for the Arrernte community. We combine traditional wisdom with modern healthcare, respecting culture and delivering quality care.
        </p>
        <div className="footer-socials">
          <div className="footer-socials">
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
    <a href="#" aria-label="LinkedIn" className="ft-social-btn">
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 448 512">
      <path d="M100.28 448H7.4V148.9h92.88zm-46.44-338a53.67 53.67 0 1 1 53.67-53.67 53.67 53.67 0 0 1-53.67 53.67zM447.9 448h-92.4V304.1c0-34.3-12.3-57.7-43.2-57.7-23.5 0-37.6 15.8-43.8 31.1-2.2 5.4-2.7 12.9-2.7 20.5V448h-92.4s1.2-268.2 0-296.1h92.4v41.9c12.3-19 34.4-46.1 83.9-46.1 61.3 0 107.2 39.9 107.2 125.5z"/>
    </svg>
  </a>
        </div>
        </div>
      </div>
      <div className="footer-right">
        <p><strong>Contact Us:</strong></p>
        <p>Alice Springs, NT</p>
        <p>hello@swinsaca.org.au</p>
        <p>Traditional</p>
      </div>
    </div>
    <div className="footer-bottom">
      <p>&copy; 2024 SwinsACA. All rights reserved.</p>
      <div className="footer-icons">
        <a href="#" className="footer-icon">🔒</a>
        <a href="#" className="footer-icon">📜</a>
        <a href="#" className="footer-icon">🌏</a>
      </div>
    </div>
  </div>
</footer>


    </div>
  );
}

export default ArrernteCommunityHomepage;
