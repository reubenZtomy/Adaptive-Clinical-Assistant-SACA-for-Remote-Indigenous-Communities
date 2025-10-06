import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
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
import ImageChatbot from "./pages/ImageChatbot"; // Keep this as it represents image-based symptom selection
import './index.css';
import ArrernteCommunityHomepage from './pages/ArrernteCommunityHomepage';  // adjust path as necessary

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/language" element={<LanguageSelection />} />
        <Route path="/navbar" element={<Home />} />

        {/* English paths */}
        <Route path="/services" element={<ServicesPage />} />
        <Route path="/voice" element={<VoiceChatbot />} />
        <Route path="/chat" element={<SwinsacaChatbot />} />
        <Route path="/image" element={<ImageChatbot />} /> {/* Image selection route */}
        
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