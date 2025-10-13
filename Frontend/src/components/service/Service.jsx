import "./service.css";
import services from "../../assets/services";
import { Link } from "react-router-dom";

export default function Service() {
  return (
    <>
      {services.map((svc) => (
        <Link to={svc.path} className="service-container" key={svc.id}>
          <div className="service-icon">
            {svc.image ? <img src={svc.image} alt="" /> : "🩺"}
          </div>
          <div className="service-head"><h5>{svc.name}</h5></div>
          <div className="service-body"><p>{svc.body}</p></div>
        </Link>
      ))}
    </>
  );
}

