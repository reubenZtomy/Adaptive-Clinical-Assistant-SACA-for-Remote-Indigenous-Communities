import "./banner.css";
import { useNavigate } from "react-router-dom";
import ellipse from "../../assets/images/ellipse.png";
import doctor from "../../assets/images/banner-doctor.png";

const Banner = () => {
  const navigate = useNavigate();   // ⬅️ hook for navigation

  return (
    <div className="banner-container">
      <div className="banner-content">
        <div className="banner-heading">
          <h2>
            Every voice matters,<br />
            every life deserves<br />
            care
          </h2>
        </div>

        <div className="banner-subheading">
          <p>
           At Swin SACA, we put people first — combining intelligence and compassion to transform patient voices into personalized insights that drive smarter healthcare decisions and improve quality of life.
          </p>
        </div>

        <div className="banner-buttons">
          <button
            className="banner-appointment-button"
            onClick={() => navigate("/services")}   // ⬅️ navigate to /services
          >
            Start assessment
          </button>
          
        </div>
      </div>

      <div className="banner-graphic">
        <img src={ellipse} alt="ellipse" />
        <img src={doctor} alt="doctor" />
      </div>
    </div>
  );
};

export default Banner;
