import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import Navbar from "../components/navbar/Navbar";

export default function VoiceInput() {
  const [recording, setRecording] = useState(false);
  const [error, setError] = useState("");
  const mediaRef = useRef(null);
  const recorderRef = useRef(null);
  const chunksRef = useRef([]);

  useEffect(() => {
    return () => {
      try { recorderRef.current?.stop(); } catch {}
      mediaRef.current?.getTracks()?.forEach(t => t.stop());
    };
  }, []);

  const start = async () => {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRef.current = stream;
      const rec = new MediaRecorder(stream);
      recorderRef.current = rec;
      chunksRef.current = [];

      rec.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      rec.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        // TODO: upload blob to backend for transcription
        console.log("Recorded blob:", blob);
      };

      rec.start();
      setRecording(true);
    } catch (e) {
      setError("Microphone access denied or unavailable.");
    }
  };

  const stop = () => {
    try { recorderRef.current?.stop(); } catch {}
    mediaRef.current?.getTracks()?.forEach(t => t.stop());
    setRecording(false);
  };

  return (
    <>
      <Navbar />
      <div style={{ maxWidth: 920, margin: "24px auto", padding: 16 }}>
        <div style={{
          border: "1px solid #e5e7eb", borderRadius: 16, padding: 24, background: "#fff"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
            <span role="img" aria-label="speaker">🔊</span>
            <h3 style={{ margin: 0 }}>Voice Input</h3>
          </div>
          <p style={{ color: "#6b7280", marginTop: 0 }}>
            Record patient symptoms and medical notes using voice commands
          </p>

          <div style={{ display: "flex", justifyContent: "center", padding: "24px 0" }}>
            <button
              onClick={recording ? stop : start}
              aria-label={recording ? "Stop recording" : "Start recording"}
              style={{
                width: 96, height: 96, borderRadius: "50%", border: "none",
                background: recording ? "#ef4444" : "#0b1020", color: "#fff",
                fontSize: 28, cursor: "pointer"
              }}
            >
              {recording ? "■" : "🎤"}
            </button>
          </div>

          <p style={{ textAlign: "center", color: "#6b7280" }}>
            {recording ? "Recording… click to stop" : "Click the microphone to start recording"}
          </p>
          {error && <p style={{ color: "#dc2626", textAlign: "center" }}>{error}</p>}
        </div>

        <div style={{ marginTop: 16 }}>
          <Link to="/services" style={{ color: "#174EB2" }}>← Back to Services</Link>
        </div>
      </div>
    </>
  );
}
