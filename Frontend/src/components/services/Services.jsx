import { useNavigate } from "react-router-dom";

export default function Services() {
  const navigate = useNavigate();

  // 👇 place the function here inside your component
  const onSelect = (id) => {
    if (id === "text") navigate("/chat");
    else if (id === "voice") navigate("/voice");
    else if (id === "image") navigate("/image");
  };

  return (
    <div className="services-container">
      <h3>Choose Input Mode</h3>

      <div className="services-wrapper">
        <div className="service-card" onClick={() => onSelect("voice")}>
          <h4>Voice</h4>
          <p>Speak your symptoms</p>
        </div>

        <div className="service-card" onClick={() => onSelect("text")}>
          <h4>Text</h4>
          <p>Chat with SwinSACA</p>
        </div>

        <div className="service-card" onClick={() => onSelect("image")}>
          <h4>Image</h4>
          <p>Select from symptom images</p>
        </div>
      </div>
    </div>
  );
}
