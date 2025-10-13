import { BrowserRouter as Router, Routes, Route, useNavigate } from "react-router-dom";
import Welcome from "./components/Welcome";
import Home from "./pages/Home";
import LanguageSelection from "./pages/LanguageSelection";
import ServicesPage from "./pages/ServicesPage";
import ServicesArrernte from "./pages/ServicesArrernte";
import VoiceChatbot from "./pages/VoiceChatbot";
import VoiceChatbotArrernte from "./pages/VoiceChatbotArrernte";
import TextInput from "./pages/TextInput";
import SwinsacaChatbot from "./pages/SwinsacaChatbot";
import SwinsacaChatbotArrernte from "./pages/SwinsacaChatbotArrernte";
import ImageChatbot from "./pages/ImageChatbot";
import ArrernteCommunityHomepage from "./pages/ArrernteCommunityHomepage";
import ArrernteCommunityAuth from "./components/ArrernteCommunityAuth"; // ← NEW
import "./index.css";

/** Wrapper so we can call navigate('/services') on success */
function AuthPageWrapper() {
  const navigate = useNavigate();
  const handleLoginSuccess = (user) => {
    // Optionally keep in state/localStorage here if you need it globally
    // localStorage.setItem('swinsaca_user', JSON.stringify(user));  // already done inside component
    navigate("/services");
  };
  return <ArrernteCommunityAuth onLoginSuccess={handleLoginSuccess} />;
}

export default function App() {
  return (
    <Router>
      <Routes>
        {/* Auth (login/signup) */}
        <Route path="/auth" element={<AuthPageWrapper />} />  {/* ← NEW ROUTE */}

        {/* Existing routes */}
        <Route path="/" element={<Welcome />} />
        <Route path="/language" element={<LanguageSelection />} />
        <Route path="/navbar" element={<Home />} />

        {/* English paths */}
        <Route path="/services" element={<ServicesPage />} />
        <Route path="/voice" element={<VoiceChatbot />} />
        <Route path="/chat" element={<SwinsacaChatbot />} />
        <Route path="/image" element={<ImageChatbot />} />

        {/* Arrernte paths */}
        <Route path="/arr-services" element={<ServicesArrernte />} />
        <Route path="/voice-arr" element={<VoiceChatbotArrernte />} />
        <Route path="/text-arr" element={<SwinsacaChatbotArrernte />} />
        <Route path="/arrernte-homepage" element={<ArrernteCommunityHomepage />} />

        {/* Common inputs */}
        <Route path="/text" element={<TextInput />} />
      </Routes>
    </Router>
  );
}
