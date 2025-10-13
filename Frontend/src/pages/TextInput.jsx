import { Link } from "react-router-dom";
import Navbar from "../components/navbar/Navbar";
import { useState } from "react";

export default function TextInput() {
  const [notes, setNotes] = useState("");

  const insert = (text) => {
    setNotes((v) => (v ? v + "\n\n" + text : text));
  };

  const save = () => {
    // TODO: send `notes` to backend
    alert("Notes saved (demo).");
  };

  return (
    <>
      <Navbar />
      <div style={{ maxWidth: 920, margin: "24px auto", padding: 16 }}>
        <div style={{
          border: "1px solid #e5e7eb", borderRadius: 16, padding: 24, background: "#fff"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span role="img" aria-label="doc">📄</span>
            <h3 style={{ margin: 0 }}>Text Input</h3>
          </div>
          <p style={{ color: "#6b7280", marginTop: 0 }}>
            Enter patient information, symptoms, and medical observations
          </p>

          <label style={{ display: "block", marginTop: 12, marginBottom: 8, fontWeight: 600 }}>
            Medical Notes
          </label>
          <textarea
            rows={10}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Enter patient symptoms, vital signs, observations, treatment plans..."
            style={{
              width: "100%", padding: 14, borderRadius: 12,
              border: "1px solid #e5e7eb", background: "#f7f7fb"
            }}
          />

          <button
            onClick={save}
            style={{
              marginTop: 16, width: "100%", padding: 14, borderRadius: 12,
              background: "#6b7280", color: "#fff", border: "none", fontWeight: 700,
              cursor: "pointer"
            }}
          >
            💾  Save Notes
          </button>

          <div style={{ marginTop: 12, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, color: "#6b7280" }}>Quick templates:</span>
            <button onClick={() => insert("Chief Complaint: ")} style={chipStyle}>Chief Complaint</button>
            <button onClick={() => insert("Vital Signs: HR , BP , Temp , SpO₂ ")} style={chipStyle}>Vital Signs</button>
            <button onClick={() => insert("Assessment: ")} style={chipStyle}>Assessment</button>
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <Link to="/services" style={{ color: "#174EB2" }}>← Back to Services</Link>
        </div>
      </div>
    </>
  );
}

const chipStyle = {
  border: "1px solid #e5e7eb",
  borderRadius: 8,
  padding: "6px 10px",
  background: "#eef2ff",
  cursor: "pointer"
};
