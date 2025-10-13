// src/components/navbar/Navbar.jsx
import "./navbar.css";
import logo from "../../assets/images/logo.png";
import search from "../../assets/images/search.png";

export default function Navbar() {
  return (
    <div className="navbar-container">
      <div className="logo">
        <img src={logo} alt="logo" />
      </div>

      <div className="nav-items">
        <h3>About SACA</h3>
        <h3>Services</h3>
        <h3>Home</h3>
        <h3>Contact</h3>
        
      </div>

      {/* <div className="side-nav-items">
        <h3>Login</h3>
        <img src={search} alt="search" />
      </div> */}
    </div>
  );
}
