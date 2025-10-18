import { Box, Button, Container, Flex, Heading, IconButton, Input, Stack, Text, VStack, HStack, Badge } from "@chakra-ui/react";
import React, { useEffect, useRef, useState } from "react";
import { useLocation } from "react-router";
import { FaUserCircle, FaMicrophone, FaPause, FaPlay, FaExclamationTriangle, FaCheckCircle, FaInfoCircle, FaTimes, FaComments, FaHeart, FaGithub, FaLanguage, FaUserAlt, FaEye, FaDeaf, FaTooth, FaHeartbeat, FaStethoscope, FaHandPaper, FaShoePrints, FaBone, FaUserInjured, FaCheck, FaRobot, FaThumbtack } from "react-icons/fa";
import logoLight from "../welcome/logo-light.svg";
import { speakText, playAudioFeedback } from "../utils/tts";

export function meta() {
  return [
    { title: "Chat - SwinSACA" },
  ];
}

type Message = { id: number; role: "user" | "assistant"; content: string; timestamp: string; audioUrl?: string };

export default function Chat() {
  const location = useLocation();
  
  // Initialize with default values to avoid SSR issues
  const [lang, setLang] = useState("english");
  const [mode, setMode] = useState("text");
  const [isDark, setIsDark] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [mounted, setMounted] = useState(false);
  const [input, setInput] = useState("");

  const listRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const rafIdRef = useRef<number | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const isRecordingRef = useRef(false);
  const isPausedRef = useRef(false);
  const [fontSize, setFontSize] = useState("normal");
  const [highContrast, setHighContrast] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [showTriageModal, setShowTriageModal] = useState(false);
  const [triageData, setTriageData] = useState<any>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackText, setFeedbackText] = useState("");
  const [feedbackType, setFeedbackType] = useState<"bug" | "feature" | "general">("general");
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  
  // Progress bar states for disease prediction
  const [showProgressBar, setShowProgressBar] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [diseasePrediction, setDiseasePrediction] = useState<any>(null);
  const [showKeyboardShortcuts, setShowKeyboardShortcuts] = useState(false);

  // Images mode inline selection flow state
  const [imageFlowStep, setImageFlowStep] = useState<number>(0);
  const [selectedBodyPart, setSelectedBodyPart] = useState<string>("");
  const [selectedBodyParts, setSelectedBodyParts] = useState<string[]>([]);
  const [finishedImagesFlow, setFinishedImagesFlow] = useState<boolean>(false);
  const [currentBodyPartIndex, setCurrentBodyPartIndex] = useState<number>(0);
  const [selectedCondition, setSelectedCondition] = useState<string>("");
  const [symptomIntensity, setSymptomIntensity] = useState<number>(5);
  const [selectedDuration, setSelectedDuration] = useState<string>("");
  const [welcomeAudioPlayed, setWelcomeAudioPlayed] = useState(false);
  const [showAudioPrompt, setShowAudioPrompt] = useState(false);
  const isPlayingWelcomeAudio = useRef(false);

  // Images mode: inline selectable palette appended to chat
  const addUserMessage = (text: string) => {
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg: Message = { id: Date.now(), role: "user", content: text, timestamp: time };
    const reply: Message = { id: Date.now() + 1, role: "assistant", content: "Noted. You can select more, or say 'summary' when done.", timestamp: time };
    setMessages((m) => [...m, userMsg, reply]);
  };

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  useEffect(() => { isRecordingRef.current = isRecording; }, [isRecording]);
  useEffect(() => { isPausedRef.current = isPaused; }, [isPaused]);
  
  // Load settings from session storage on mount
  useEffect(() => {
    const storedLang = sessionStorage.getItem('swinsaca_language');
    const storedMode = sessionStorage.getItem('swinsaca_mode');
    if (storedLang) setLang(storedLang);
    if (storedMode) setMode(storedMode);
  }, []);
  
  // Save language and mode to session storage whenever they change
  useEffect(() => {
    sessionStorage.setItem('swinsaca_language', lang);
    sessionStorage.setItem('swinsaca_mode', mode);
    
    // If switching to Arrernte voice mode, update the welcome message and play audio
    if (lang === "arrernte" && mode === "voice" && messages.length > 0) {
      const welcomeMessage = "Werte! Ayenge SwinSACA, your AI medical assistant akaltye. Ayenge here to help arrantherre with health-related questions and give guidance arlke. How arrantherre feeling today nhenhe? What symptoms or concerns anwerne want to ileme atyenge akaltye?";
      const welcomeAudioUrl = "http://localhost:5000/static/audio/welcomeMessage_arrernte.mp3";
      
      // Update the first message (welcome message)
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[0] && updatedMessages[0].role === "assistant") {
          updatedMessages[0] = {
            ...updatedMessages[0],
            content: welcomeMessage,
            audioUrl: welcomeAudioUrl
          };
        }
        return updatedMessages;
      });
      
      // Try to play welcome audio immediately when switching to Arrernte voice mode
      if (welcomeAudioUrl && !isPlayingWelcomeAudio.current) {
        isPlayingWelcomeAudio.current = true;
        setTimeout(() => {
          const audio = new Audio(welcomeAudioUrl);
          audio.play()
            .then(() => {
              console.log('🎵 Welcome audio played successfully on language switch');
              setWelcomeAudioPlayed(true);
              isPlayingWelcomeAudio.current = false;
            })
            .catch((error) => {
              console.log('🎵 Welcome audio blocked by browser, will play on first interaction:', error);
              setShowAudioPrompt(true);
              isPlayingWelcomeAudio.current = false;
              // Hide the prompt after 5 seconds
              setTimeout(() => setShowAudioPrompt(false), 5000);
            });
        }, 300);
      }
    } else if (lang === "english" && mode === "voice" && messages.length > 0) {
      // If switching to English voice mode, update to English welcome message
      const welcomeMessage = "Hello! I'm SwinSACA, your AI medical assistant. I'm here to help you with health-related questions and provide guidance. How are you feeling today? What symptoms or concerns would you like to discuss?";
      
      setMessages(prevMessages => {
        const updatedMessages = [...prevMessages];
        if (updatedMessages[0] && updatedMessages[0].role === "assistant") {
          updatedMessages[0] = {
            ...updatedMessages[0],
            content: welcomeMessage,
            audioUrl: undefined
          };
        }
        return updatedMessages;
      });
    }
  }, [lang, mode]);
  
  // Handle settings from location state (when navigating from selection pages)
  useEffect(() => {
    if (location.state) {
      const { lang: newLang, mode: newMode } = location.state as any;
      if (newLang) {
        setLang(newLang);
      }
      if (newMode) {
        setMode(newMode);
      }
    }
  }, [location.state]);
  
  // Function to clear session storage (useful for resetting settings)
  const clearSessionSettings = () => {
    sessionStorage.removeItem('swinsaca_language');
    sessionStorage.removeItem('swinsaca_mode');
  };
  useEffect(() => {
    setMounted(true);
    // Add initial assistant greeting after mount to avoid SSR hydration issues
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    
    if (mode === "images") {
      setMessages([{ 
        id: Date.now(), 
        role: "assistant", 
        content: "Images mode: Select from the options below to describe your symptoms. You can add multiple selections.", 
        timestamp: time 
      }]);
      setImageFlowStep(0);
      setSelectedBodyPart("");
      setSelectedBodyParts([]);
      setCurrentBodyPartIndex(0);
      setSelectedCondition("");
      setSymptomIntensity(5);
      setSelectedDuration("");
    } else {
      // Set welcome message based on language and mode
      let welcomeMessage = "Hello! I'm SwinSACA, your AI medical assistant. I'm here to help you with health-related questions and provide guidance. How are you feeling today? What symptoms or concerns would you like to discuss?";
      let welcomeAudioUrl: string | undefined = undefined;
      
      if (lang === "arrernte" && mode === "voice") {
        welcomeMessage = "Werte! Ayenge SwinSACA, your AI medical assistant akaltye. Ayenge here to help arrantherre with health-related questions and give guidance arlke. How arrantherre feeling today nhenhe? What symptoms or concerns anwerne want to ileme atyenge akaltye?";
        welcomeAudioUrl = "http://localhost:5000/static/audio/welcomeMessage_arrernte.mp3";
      }
      
      setMessages([{
        id: Date.now(), 
        role: "assistant", 
        content: welcomeMessage, 
        timestamp: time,
        audioUrl: welcomeAudioUrl
      }]);
      
      // Try to play welcome audio immediately for Arrernte voice mode
      if (lang === "arrernte" && mode === "voice" && welcomeAudioUrl && !isPlayingWelcomeAudio.current) {
        isPlayingWelcomeAudio.current = true;
        setTimeout(() => {
          const audio = new Audio(welcomeAudioUrl);
          audio.play()
            .then(() => {
              console.log('🎵 Welcome audio played successfully on page load');
              setWelcomeAudioPlayed(true);
              isPlayingWelcomeAudio.current = false;
            })
            .catch((error) => {
              console.log('🎵 Welcome audio blocked by browser, will play on first interaction:', error);
              setShowAudioPrompt(true);
              isPlayingWelcomeAudio.current = false;
              // Hide the prompt after 5 seconds
              setTimeout(() => setShowAudioPrompt(false), 5000);
            });
        }, 500); // Small delay to ensure the message is rendered
      }
    }
    
    // Test backend connection
    const testConnection = async () => {
      try {
        const response = await fetch('http://localhost:5000/health');
        if (response.ok) {
          console.log('✅ Backend connection successful');
        } else {
          console.log('❌ Backend connection failed:', response.status);
        }
      } catch (error) {
        console.log('❌ Backend connection error:', error);
      }
    };
    
    testConnection();
    
    // Log current session storage values
    console.log('📱 Current session settings:', {
      language: sessionStorage.getItem('swinsaca_language'),
      mode: sessionStorage.getItem('swinsaca_mode'),
      currentLang: lang,
      currentMode: mode
    });
    
    // Note: Removed automatic mode/language announcement to avoid audio conflicts
  }, [mode]);

  useEffect(() => {
    try {
      // Preloader: if replying to last assistant message and non-image mode, show a short loader
      const lastMsg = messages[messages.length - 1];
      if (mode !== "images" && lastMsg && lastMsg.role === "assistant") {
        startTimedLoader(4000);
      }
      const root = document.documentElement as HTMLElement;
      root.style.setProperty("--app-bg", isDark ? "#0f172a" : "#f9fafb");
      root.style.setProperty("--app-fg", isDark ? "#f8fafc" : "#1f2937");
      document.body.style.backgroundColor = getComputedStyle(root).getPropertyValue("--app-bg");
      document.body.style.color = getComputedStyle(root).getPropertyValue("--app-fg");
    } catch {}
  }, [isDark]);

  const startRecording = async () => {
    // Play welcome audio on first interaction for Arrernte voice mode (only if not already played)
    if (lang === "arrernte" && mode === "voice" && !welcomeAudioPlayed && !isPlayingWelcomeAudio.current) {
      isPlayingWelcomeAudio.current = true;
      const welcomeAudioUrl = "http://localhost:5000/static/audio/welcomeMessage_arrernte.mp3";
      try {
        const audio = new Audio(welcomeAudioUrl);
        await audio.play();
        setWelcomeAudioPlayed(true);
        setShowAudioPrompt(false);
        isPlayingWelcomeAudio.current = false;
        console.log('🎵 Welcome audio played successfully on first interaction');
      } catch (error) {
        console.log('🎵 Welcome audio play failed:', error);
        isPlayingWelcomeAudio.current = false;
      }
    }
    
    try {
      console.log('🎙️ Requesting microphone access...');
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      console.log('🎙️ Microphone access granted:', {
        streamActive: stream.active,
        tracks: stream.getTracks().length,
        trackDetails: stream.getTracks().map(track => ({
          kind: track.kind,
          enabled: track.enabled,
          muted: track.muted,
          readyState: track.readyState,
          label: track.label
        }))
      });
      mediaStreamRef.current = stream;
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      audioContextRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      const canvas = canvasRef.current;
      const setupCanvas = () => {
        if (!canvas) return;
        const dpr = window.devicePixelRatio || 1;
        const cssWidth = canvas.clientWidth || canvas.parentElement?.clientWidth || 600;
        const cssHeight = 100;
        canvas.width = Math.floor(cssWidth * dpr);
        canvas.height = Math.floor(cssHeight * dpr);
      };
      setupCanvas();
      const onResize = () => setupCanvas();
      window.addEventListener("resize", onResize);

      const loop = () => {
        if (!canvas || !analyserRef.current) return;
        const ctx2d = canvas.getContext("2d");
        if (!ctx2d) return;
        // Clear background
        ctx2d.clearRect(0, 0, canvas.width, canvas.height);
        ctx2d.fillStyle = isDark ? "#0b1220" : "#e5e7eb";
        ctx2d.fillRect(0, 0, canvas.width, canvas.height);

        if (!isRecordingRef.current) {
          rafIdRef.current = requestAnimationFrame(loop);
          return;
        }
        const bufferLength = analyserRef.current.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        analyserRef.current.getByteTimeDomainData(dataArray);
        ctx2d.lineWidth = 2;
        ctx2d.strokeStyle = "#14b8a6";
        ctx2d.beginPath();
        const sliceWidth = canvas.width / bufferLength;
        let x = 0;
        for (let i = 0; i < bufferLength; i++) {
          const v = dataArray[i] / 128.0;
          const y = (v * canvas.height) / 2;
          if (i === 0) ctx2d.moveTo(x, y);
          else ctx2d.lineTo(x, y);
          x += sliceWidth;
        }
        ctx2d.lineTo(canvas.width, canvas.height / 2);
        ctx2d.stroke();
        rafIdRef.current = requestAnimationFrame(loop);
      };
      rafIdRef.current = requestAnimationFrame(loop);

      // Check for supported MIME types
      let mimeType = 'audio/webm';
      if (!MediaRecorder.isTypeSupported('audio/webm')) {
        if (MediaRecorder.isTypeSupported('audio/mp4')) {
          mimeType = 'audio/mp4';
        } else if (MediaRecorder.isTypeSupported('audio/wav')) {
          mimeType = 'audio/wav';
        } else {
          mimeType = ''; // Let browser choose
        }
      }
      
      console.log('Using MIME type:', mimeType);
      const recorder = new MediaRecorder(stream, { mimeType });
      mediaRecorderRef.current = recorder;
      const chunks: BlobPart[] = [];
      recorder.ondataavailable = (e) => { 
        console.log('Data available:', e.data.size, 'bytes', 'Type:', e.data.type);
        console.log('Chunk details:', {
          size: e.data.size,
          type: e.data.type,
          chunksSoFar: chunks.length
        });
        if (e.data && e.data.size > 0) {
          chunks.push(e.data);
          console.log('Added chunk, total chunks:', chunks.length);
        } else {
          console.warn('Empty or invalid chunk received');
        }
      };
      
      recorder.onerror = (e) => {
        console.error('MediaRecorder error:', e);
        setErrorMessage("Error occurred while recording audio.");
        setTimeout(() => setErrorMessage(null), 5000);
      };
      recorder.onstop = async () => {
        const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        
        console.log('🎤 Recording stopped. Processing audio...');
        console.log('📊 Chunks collected:', {
          totalChunks: chunks.length,
          chunksDetails: chunks.map((chunk, i) => ({
            index: i,
            size: chunk instanceof Blob ? chunk.size : 'unknown',
            type: chunk instanceof Blob ? chunk.type : 'unknown'
          }))
        });
        
        // Create audio blob from chunks with the correct MIME type
        const actualMimeType = recorder.mimeType || 'audio/webm';
        const audioBlob = new Blob(chunks, { type: actualMimeType });
        
        console.log('🎵 Audio blob created:', {
          size: audioBlob.size,
          type: audioBlob.type,
          chunks: chunks.length,
          actualMimeType: actualMimeType
        });
        
        // Check if audio blob is empty or too small
        if (audioBlob.size === 0) {
          console.error('Audio blob is empty!');
          const errorReply: Message = { 
            id: Date.now() + 1, 
            role: "assistant", 
            content: "I'm sorry, the audio recording was empty. Please try recording again and speak for at least 2-3 seconds.", 
            timestamp: time 
          };
          setMessages((m) => [...m, errorReply]);
          return;
        }
        
        if (audioBlob.size < 1000) { // Less than 1KB is likely too short
          console.warn('Audio blob is very small:', audioBlob.size, 'bytes');
          const errorReply: Message = { 
            id: Date.now() + 1, 
            role: "assistant", 
            content: "The recording seems too short. Please try recording again and speak for at least 2-3 seconds.", 
            timestamp: time 
          };
          setMessages((m) => [...m, errorReply]);
          return;
        }
        
        // Add user message immediately (will be updated with transcribed text later)
        const userMsg = { id: Date.now(), role: "user" as const, content: "[Voice message]", timestamp: time };
        setMessages((m) => [...m, userMsg]);
        
        // Send audio to backend for transcription and processing
        try {
          const formData = new FormData();
          const fileExtension = actualMimeType.includes('mp4') ? 'mp4' : 
                               actualMimeType.includes('wav') ? 'wav' : 'webm';
          formData.append('audio', audioBlob, `voice_message.${fileExtension}`);
          formData.append('language', lang);
          formData.append('mode', mode);
          
          console.log('Sending voice message to backend...', {
            url: 'http://localhost:5000/api/chat/',
            language: lang,
            mode: mode,
            audioSize: audioBlob.size,
            formDataKeys: Array.from(formData.keys())
          });
          
          const response = await fetch('http://localhost:5000/api/chat/', {
            method: 'POST',
            headers: {
              'X-Language': lang,
              'X-Mode': mode,
            },
            body: formData
          });
          
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          
          const data = await response.json();
          
          // Log the transcription and response for testing
          console.log('🎤 Voice Chat Response:', {
            transcribedText: data.transcribed_text, // What you actually said
            botResponse: data.reply, // What the bot replied
            audioUrl: data.audio_url,
            isFinalMessage: data.is_final_message,
            context: data.context,
            bot: data.bot
          });
          
          // Also log just the transcription for easy reading
          console.log('📝 Transcribed Text:', data.transcribed_text);
          
          // Update the user message with the actual transcribed text
          if (data.transcribed_text) {
            setMessages((m) => m.map(msg => 
              msg.id === userMsg.id 
                ? { ...msg, content: data.transcribed_text }
                : msg
            ));
          }
          
          // Preloader: if replying to last assistant message and non-image mode, show a short loader
          const lastMsg = messages[messages.length - 1];
          if (mode !== "images" && lastMsg && lastMsg.role === "assistant") {
            startTimedLoader(4000);
          }

          // Check if this is a final message for disease prediction
          const isFinalMessage = data.is_final_message || false;
          
          let reply: Message;
          if (isFinalMessage) {
            // Store the disease prediction data
            if (data.disease_prediction) {
              setDiseasePrediction(data.disease_prediction);
            }

            if (mode === "images") {
              // Images mode: no loader, show summary immediately
              reply = { 
                id: Date.now() + 1, 
                role: "assistant", 
                content: data.reply, 
                timestamp: time,
                audioUrl: data.audio_url // Store audio URL for replay
              };
              const triage = generateTriageSummary([...messages, userMsg], data.disease_prediction);
              setTriageData(triage);
              setShowTriageModal(true);
              setShowProgressBar(false);
              setIsAnalyzing(false);
            } else {
              // Voice/Text modes: show loader and delay summary to match progress
              setShowProgressBar(true);
              setIsAnalyzing(true);
              setProgressStep(0);
              setProgressMessage("Analyzing symptoms...");
              simulateProgressBar();

              reply = { 
                id: Date.now() + 1, 
                role: "assistant", 
                content: data.reply, 
                timestamp: time,
                audioUrl: data.audio_url // Store audio URL for replay
              };

              setTimeout(() => {
                const triage = generateTriageSummary([...messages, userMsg], data.disease_prediction);
                setTriageData(triage);
                setShowTriageModal(true);
              }, 6000);
            }

            // Voice announcements for assessment results
            if (mode === "voice") {
              // First announce that summary is ready
              speakText("Medical triage summary is ready. Please review the assessment results.");
              // Then announce the assessment result after a delay
              setTimeout(() => {
                if (data.disease_prediction && data.disease_prediction.diagnosis) {
                  speakText(`Assessment result: ${data.disease_prediction.diagnosis}`);
                }
              }, 3000);
              // Then announce doctor visit recommendation
              setTimeout(() => {
                speakText("Please visit a doctor for proper medical evaluation.");
              }, 6000);
              // Finally announce the disclaimer
              setTimeout(() => {
                speakText("This is just a preliminary diagnosis. If symptoms persist or worsen, seek immediate medical attention.");
              }, 9000);
            } else if (mode !== "images") {
              // For text mode, just announce summary is ready
              speakText("Medical triage summary is ready. Please review the assessment results.");
            }

          } else {
            reply = { 
              id: Date.now() + 1, 
              role: "assistant", 
              content: data.reply, 
              timestamp: time,
              audioUrl: data.audio_url // Store audio URL for replay
            };
          }
          
          setMessages((m) => [...m, reply]);
          
          // Play audio for follow-up questions or speak the response if in voice mode
          if (mode === "voice") {
            // Check if this is a follow-up question and has an audio URL
            if (data.audio_url && (data.reply.includes('?') || 
                data.reply.toLowerCase().includes('where') || 
                data.reply.toLowerCase().includes('how') || 
                data.reply.toLowerCase().includes('what') || 
                data.reply.toLowerCase().includes('when') || 
                data.reply.toLowerCase().includes('do you') || 
                data.reply.toLowerCase().includes('are you') || 
                data.reply.toLowerCase().includes('have you'))) {
              // This is a follow-up question with audio, play the audio file
              console.log('🎵 Playing follow-up question audio:', data.audio_url);
              const audio = new Audio(data.audio_url);
              audio.play()
                .then(() => {
                  console.log('🎵 Follow-up question audio played successfully');
                })
                .catch((error) => {
                  console.log('🎵 Follow-up question audio play failed, falling back to TTS:', error);
                  speakText(data.reply);
                });
            } else {
              // Regular response, use TTS
              speakText(data.reply);
            }
          }
          
        } catch (error) {
          console.error('Error processing voice message:', error);
          const errorReply: Message = { 
            id: Date.now() + 1, 
            role: "assistant", 
            content: "I'm sorry, I'm having trouble processing your voice message right now. Please try again later.", 
            timestamp: time 
          };
          setMessages((m) => [...m, errorReply]);
          setErrorMessage("Failed to process voice message. Please try again.");
          setTimeout(() => setErrorMessage(null), 5000);
        }
        
        window.removeEventListener("resize", onResize);
      };
      
      console.log('🎤 Starting MediaRecorder...', {
        mimeType: mimeType,
        streamActive: stream.active,
        streamTracks: stream.getTracks().length,
        recorderState: recorder.state
      });
      
      recorder.start(1000); // Record in 1-second chunks
      
      console.log('🎤 MediaRecorder started:', {
        state: recorder.state,
        mimeType: recorder.mimeType
      });
      
      setIsRecording(true); isRecordingRef.current = true;
      setIsPaused(false); isPausedRef.current = false;
      playAudioFeedback('success');
      speakText("Recording started");
    } catch (e) {
      console.error(e);
      setErrorMessage("Unable to start recording. Please check your microphone permissions.");
      playAudioFeedback('error');
      speakText("Error: Unable to start recording. Please check your microphone permissions.");
      setTimeout(() => setErrorMessage(null), 5000);
    }
  };

  const stopRecording = async () => {
    try {
      console.log('🛑 Stopping recording...', {
        recorderState: mediaRecorderRef.current?.state,
        streamActive: mediaStreamRef.current?.active,
        audioContextState: audioContextRef.current?.state
      });
      
      mediaRecorderRef.current?.stop();
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
      if (audioContextRef.current && audioContextRef.current.state !== "closed") audioContextRef.current.close();
      if (rafIdRef.current) cancelAnimationFrame(rafIdRef.current);
      
      console.log('🛑 Recording stopped successfully');
    } finally {
      setIsRecording(false); isRecordingRef.current = false;
      setIsPaused(false); isPausedRef.current = false;
      playAudioFeedback('success');
      speakText("Recording stopped");
    }
  };

  const togglePause = () => {
    try {
      if (!mediaRecorderRef.current) return;
      if (!isPausedRef.current) {
        mediaRecorderRef.current.pause();
        setIsPaused(true); isPausedRef.current = true;
        playAudioFeedback('click');
        speakText("Recording paused");
      } else {
        mediaRecorderRef.current.resume();
        setIsPaused(false); isPausedRef.current = false;
        playAudioFeedback('click');
        speakText("Recording resumed");
      }
    } catch (e) {
      console.error(e);
      setErrorMessage("Error occurred while pausing/resuming recording.");
      playAudioFeedback('error');
      speakText("Error occurred while pausing or resuming recording.");
      setTimeout(() => setErrorMessage(null), 5000);
    }
  };

  useEffect(() => {
    return () => { 
      try { 
        // Only stop recording if it's actually running
        if (isRecordingRef.current) {
          stopRecording(); 
        }
      } catch {} 
    };
  }, []);

  // Keyboard navigation support
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Space bar to start/stop recording in voice mode
      if (mode === "voice" && e.code === "Space" && !e.target?.closest("input")) {
        e.preventDefault();
        if (isRecording) {
          stopRecording();
        } else {
          startRecording();
        }
      }
      // Enter to pause/resume recording
      if (mode === "voice" && isRecording && e.code === "Enter" && !e.target?.closest("input")) {
        e.preventDefault();
        togglePause();
      }
      // Escape to stop recording
      if (mode === "voice" && isRecording && e.code === "Escape") {
        e.preventDefault();
        stopRecording();
      }
      // Ctrl/Cmd + D for dark mode toggle
      if ((e.ctrlKey || e.metaKey) && e.code === "KeyD") {
        e.preventDefault();
        setIsDark(prev => !prev);
        playAudioFeedback('click');
        speakText(isDark ? "Light mode activated" : "Dark mode activated");
      }
      // Ctrl/Cmd + + for font size increase
      if ((e.ctrlKey || e.metaKey) && e.code === "Equal") {
        e.preventDefault();
        setFontSize(prev => prev === "small" ? "normal" : prev === "normal" ? "large" : "xlarge");
      }
      // Ctrl/Cmd + - for font size decrease
      if ((e.ctrlKey || e.metaKey) && e.code === "Minus") {
        e.preventDefault();
        setFontSize(prev => prev === "xlarge" ? "large" : prev === "large" ? "normal" : "small");
      }
      // Ctrl/Cmd + H for high contrast toggle
      if ((e.ctrlKey || e.metaKey) && e.code === "KeyH") {
        e.preventDefault();
        setHighContrast(prev => !prev);
        playAudioFeedback('click');
        speakText(highContrast ? "High contrast disabled" : "High contrast enabled");
      }
      // Escape to close triage modal
      if (e.code === "Escape" && showTriageModal) {
        e.preventDefault();
        setShowTriageModal(false);
        speakText("Triage summary closed");
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [mode, isRecording, isPaused, showTriageModal]);

  // Medical triage assessment function
  const assessSeverity = (chatHistory: Message[]): { level: number; label: string; color: string; description: string } => {
    const userMessages = chatHistory.filter(m => m.role === "user").map(m => m.content.toLowerCase());
    const allText = userMessages.join(" ");
    
    // Emergency keywords (Level 5 - Critical)
    const emergencyKeywords = ["chest pain", "heart attack", "stroke", "unconscious", "bleeding heavily", "can't breathe", "severe pain", "emergency"];
    if (emergencyKeywords.some(keyword => allText.includes(keyword))) {
      return { level: 5, label: "CRITICAL", color: "red", description: "Immediate emergency care required" };
    }
    
    // High severity keywords (Level 4 - Urgent)
    const urgentKeywords = ["severe", "intense pain", "high fever", "difficulty breathing", "vomiting blood", "severe headache"];
    if (urgentKeywords.some(keyword => allText.includes(keyword))) {
      return { level: 4, label: "URGENT", color: "orange", description: "Seek medical attention within hours" };
    }
    
    // Moderate severity keywords (Level 3 - Moderate)
    const moderateKeywords = ["pain", "fever", "nausea", "dizzy", "tired", "ache", "sore"];
    if (moderateKeywords.some(keyword => allText.includes(keyword))) {
      return { level: 3, label: "MODERATE", color: "yellow", description: "Schedule appointment within 24-48 hours" };
    }
    
    // Low severity keywords (Level 2 - Mild)
    const mildKeywords = ["mild", "slight", "minor", "uncomfortable", "annoying"];
    if (mildKeywords.some(keyword => allText.includes(keyword))) {
      return { level: 2, label: "MILD", color: "green", description: "Monitor symptoms, consider self-care" };
    }
    
    // Default (Level 1 - Minimal)
    return { level: 1, label: "MINIMAL", color: "blue", description: "Continue monitoring, no immediate action needed" };
  };

  const handleFeedbackSubmit = () => {
    if (!feedbackText.trim()) return;
    
    // In a real app, you would send this to your backend
    console.log("Feedback submitted:", {
      type: feedbackType,
      text: feedbackText,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      mode: mode,
      language: lang
    });
    
    setFeedbackSubmitted(true);
    playAudioFeedback('success');
    speakText("Thank you for your feedback! We appreciate your input.");
    
    // Reset form after 3 seconds
    setTimeout(() => {
      setFeedbackSubmitted(false);
      setFeedbackText("");
      setFeedbackType("general");
      setShowDropdown(false);
      setShowFeedbackModal(false);
    }, 3000);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
        const target = event.target as HTMLElement;
      
      if (showDropdown && !target.closest('[data-dropdown]')) {
          setShowDropdown(false);
        }
      
      if (showKeyboardShortcuts && !target.closest('[data-keyboard-shortcuts]')) {
        setShowKeyboardShortcuts(false);
      }
    };

    if (showFeedbackModal || showDropdown || showKeyboardShortcuts) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showDropdown, showFeedbackModal, showKeyboardShortcuts]);

  // Progress bar component for disease prediction
  const renderProgressBar = () => {
    if (!showProgressBar) return null;

    const steps = [
      { message: "Analyzing symptoms...", progress: 20 },
      { message: "Processing medical data...", progress: 40 },
      { message: "Running prediction model...", progress: 60 },
      { message: "Generating recommendations...", progress: 80 },
      { message: "Finalizing assessment...", progress: 100 }
    ];

    const currentStep = steps[progressStep] || steps[steps.length - 1];

    return (
      <Box
        position="fixed"
        top="50%"
        left="50%"
        transform="translate(-50%, -50%)"
        zIndex={900}
        bg={isDark ? "gray.800" : "white"}
        p={8}
        borderRadius="lg"
        shadow="2xl"
        border="1px solid"
        borderColor={isDark ? "gray.600" : "gray.200"}
        minW="400px"
        textAlign="center"
      >
        <VStack spacing={6}>
          <Heading size="md" color={isDark ? "gray.100" : "gray.800"}>
            Analyzing Your Symptoms
          </Heading>
          
          <Box position="relative" display="inline-block">
            <Box
              w="120px"
              h="120px"
              borderRadius="50%"
              border="8px solid"
              borderColor={isDark ? "gray.600" : "gray.200"}
              position="relative"
              display="flex"
              alignItems="center"
              justifyContent="center"
            >
              <Box
                position="absolute"
                top="0"
                left="0"
                w="100%"
                h="100%"
                borderRadius="50%"
                border="8px solid"
                borderColor="teal.500"
                borderTopColor="transparent"
                borderRightColor="transparent"
                transform={`rotate(${(currentStep.progress / 100) * 360}deg)`}
                transition="transform 0.5s ease"
              />
              <Text
                color={isDark ? "gray.100" : "gray.800"}
                fontSize="xl"
                fontWeight="bold"
                zIndex={1}
              >
                {currentStep.progress}%
              </Text>
            </Box>
          </Box>
          
          <Text fontSize="lg" color={isDark ? "gray.300" : "gray.600"}>
            {progressMessage}
          </Text>
          
          <Box
            w="100%"
            h="8px"
            bg={isDark ? "gray.600" : "gray.200"}
            borderRadius="full"
            overflow="hidden"
          >
            <Box
              h="100%"
              bg="teal.500"
              w={`${currentStep.progress}%`}
              transition="width 0.5s ease"
              borderRadius="full"
            />
          </Box>
        </VStack>
      </Box>
    );
  };

  // Function to simulate progress bar animation
  const simulateProgressBar = async () => {
    const steps = [
      { message: "Analyzing symptoms...", progress: 20 },
      { message: "Processing medical data...", progress: 40 },
      { message: "Running prediction model...", progress: 60 },
      { message: "Generating recommendations...", progress: 80 },
      { message: "Finalizing assessment...", progress: 100 }
    ];

    for (let i = 0; i < steps.length; i++) {
      setProgressStep(i);
      setProgressMessage(steps[i].message);
      await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second between steps
    }

    // Hide progress bar after completion
    setTimeout(() => {
      setShowProgressBar(false);
      setIsAnalyzing(false);
    }, 500);
  };

  // Start a short, timed loader with animated progress over the given duration
  const startTimedLoader = (durationMs: number) => {
    setShowProgressBar(true);
    setIsAnalyzing(true);
    // There are 5 steps in renderProgressBar; advance evenly across duration
    const steps = [
      { message: "Analyzing symptoms...", index: 0 },
      { message: "Processing medical data...", index: 1 },
      { message: "Running prediction model...", index: 2 },
      { message: "Generating recommendations...", index: 3 },
      { message: "Finalizing assessment...", index: 4 }
    ];
    const interval = Math.max(50, Math.floor(durationMs / steps.length));
    steps.forEach((s, i) => {
      setTimeout(() => {
        setProgressStep(s.index);
        setProgressMessage(s.message);
      }, i * interval);
    });
    setTimeout(() => {
      setShowProgressBar(false);
      setIsAnalyzing(false);
    }, durationMs);
  };

  const generateTriageSummary = (chatHistory: Message[], mlApiData?: any) => {
    const userMessages = chatHistory.filter(m => m.role === "user");
    
    // Use ML API data if available, otherwise fall back to basic assessment
    let severity, possibleConditions, nextSteps, mlResults;
    
    if (mlApiData && !mlApiData.error) {
      // Use ML API results for enhanced assessment
      const { ml1, ml2, final } = mlApiData;
      
      // Map ML severity to our severity system
      const severityMapping = {
        'mild': { level: 1, color: 'green', label: 'Mild', description: 'Low priority - monitor symptoms' },
        'moderate': { level: 3, color: 'yellow', label: 'Moderate', description: 'Medium priority - seek medical advice' },
        'severe': { level: 5, color: 'red', label: 'Severe', description: 'High priority - immediate medical attention needed' }
      };
      
      severity = severityMapping[final.severity as keyof typeof severityMapping] || 
                { level: 2, color: 'orange', label: 'Unknown', description: 'Assessment in progress' };
      
      // Use ML1 disease predictions as possible conditions (names only, no confidence)
      possibleConditions = (ml1.disease_topk?.length
        ? ml1.disease_topk.map((d: any) => d.disease)
        : (ml2.top?.length
            ? ml2.top.map((t: any) => `Label ${t.label}`)
            : ["Assessment in progress"])) as string[];
      
      // Generate next steps based on ML severity
      nextSteps = [];
      if (severity.level >= 4) {
        nextSteps.push("🚨 Call emergency services (000) immediately");
        nextSteps.push("🏥 Go to nearest emergency department");
        nextSteps.push("📋 Bring this assessment summary to medical staff");
      } else if (severity.level === 3) {
        nextSteps.push("📞 Contact your GP or healthcare provider within 24 hours");
        nextSteps.push("🏥 Consider urgent care center if symptoms worsen");
        nextSteps.push("📋 Share this AI assessment with your doctor");
      } else if (severity.level === 2) {
        nextSteps.push("📅 Schedule appointment with healthcare provider");
        nextSteps.push("💊 Consider over-the-counter medications if appropriate");
        nextSteps.push("👀 Monitor symptoms closely");
      } else {
        nextSteps.push("👀 Continue monitoring symptoms");
        nextSteps.push("📚 Research self-care options");
        nextSteps.push("📋 Keep this assessment for future reference");
      }
      
      // Store ML results for display
      mlResults = {
        ml1: {
          severity: ml1.severity,
          confidence: Math.round(ml1.confidence * 100),
          diseases: ml1.disease_topk || []
        },
        ml2: {
          predictedLabel: ml2.predicted_label,
          probability: Math.round(ml2.probability * 100),
          alternatives: ml2.top || []
        },
        fusion: {
          finalDiagnosis: final.disease_label,
          finalProbability: Math.round(final.probability * 100),
          source: final.source,
          policy: final.policy
        }
      };
      
    } else {
      // Fallback to basic assessment
      severity = assessSeverity(chatHistory);
      
      // Generate possible conditions based on symptoms mentioned
      const allText = userMessages.map(m => m.content.toLowerCase()).join(" ");
      possibleConditions = [];
      
      if (allText.includes("chest") && allText.includes("pain")) possibleConditions.push("Cardiac issues, Angina, Heart attack");
      if (allText.includes("head") && allText.includes("pain")) possibleConditions.push("Migraine, Tension headache, Sinusitis");
      if (allText.includes("fever") || allText.includes("temperature")) possibleConditions.push("Viral infection, Bacterial infection, Flu");
      if (allText.includes("stomach") || allText.includes("abdominal")) possibleConditions.push("Gastritis, Food poisoning, Indigestion");
      if (allText.includes("breathing") || allText.includes("cough")) possibleConditions.push("Respiratory infection, Asthma, Bronchitis");
      
      if (possibleConditions.length === 0) {
        possibleConditions.push("General consultation needed");
      }
      
      // Generate next steps based on severity
      nextSteps = [];
      if (severity.level >= 4) {
        nextSteps.push("🚨 Call emergency services (000) immediately");
        nextSteps.push("🏥 Go to nearest emergency department");
      } else if (severity.level === 3) {
        nextSteps.push("📞 Contact your GP or healthcare provider");
        nextSteps.push("🏥 Consider urgent care center if symptoms worsen");
      } else if (severity.level === 2) {
        nextSteps.push("📅 Schedule appointment with healthcare provider");
        nextSteps.push("💊 Consider over-the-counter medications if appropriate");
      } else {
        nextSteps.push("👀 Continue monitoring symptoms");
        nextSteps.push("📚 Research self-care options");
      }
      
      mlResults = null;
    }
    
    return {
      chatSummary: userMessages.map(m => m.content).join(" | "),
      severity,
      possibleConditions,
      nextSteps,
      timestamp: new Date().toLocaleString(),
      mlResults // Include ML API results if available
    };
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userMsg: Message = { id: Date.now(), role: "user", content: input.trim(), timestamp: time };
    
    // Add user message immediately
    setMessages((m) => [...m, userMsg]);
    setInput("");
    playAudioFeedback('success');
    speakText("Message sent");
    
    try {
      console.log('Sending request to backend...', {
        url: 'http://localhost:5000/api/chat/',
        message: input.trim(),
        language: lang,
        mode: mode
      });
      
      // Call the backend chat API
      const response = await fetch('http://localhost:5000/api/chat/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Language': lang,
          'X-Mode': mode,
        },
        body: JSON.stringify({
          message: input.trim(),
          reset: false,
          _context: {
            language: lang,
            mode: mode
          },
          conversation_history: messages // Include complete conversation history
        })
      });
      
      console.log('Response received:', response.status, response.statusText);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Check if this is a final message for disease prediction
      const isFinalMessage = data.is_final_message || false;
    
    let reply: Message;
    if (isFinalMessage) {
        // Store the disease prediction data
        if (data.disease_prediction) {
          setDiseasePrediction(data.disease_prediction);
        }

        if (mode === "images") {
          // Images mode: no loader, show summary immediately
          reply = { 
            id: Date.now() + 1, 
            role: "assistant", 
            content: data.reply, 
            timestamp: time 
          };
          const triage = generateTriageSummary([...messages, userMsg], data.disease_prediction);
          setTriageData(triage);
          setShowTriageModal(true);
          setShowProgressBar(false);
          setIsAnalyzing(false);
          speakText("Medical triage summary is ready. Please review the assessment results.");
        } else {
          // Voice/Text modes: show loader and delay summary to match progress
          setShowProgressBar(true);
          setIsAnalyzing(true);
          setProgressStep(0);
          setProgressMessage("Analyzing symptoms...");
          simulateProgressBar();
          reply = { 
            id: Date.now() + 1, 
            role: "assistant", 
            content: data.reply, 
            timestamp: time 
          };
          setTimeout(() => {
            const triage = generateTriageSummary([...messages, userMsg], data.disease_prediction);
            setTriageData(triage);
            setShowTriageModal(true);
          }, 6000);
        }
        
    } else {
        reply = { 
          id: Date.now() + 1, 
          role: "assistant", 
          content: data.reply, 
          timestamp: time 
        };
      }
      
      setMessages((m) => [...m, reply]);
      
      // Play audio for follow-up questions or speak the response if in voice mode
      if (mode === "voice") {
        // Check if this is a follow-up question and has an audio URL
        if (data.audio_url && (data.reply.includes('?') || 
            data.reply.toLowerCase().includes('where') || 
            data.reply.toLowerCase().includes('how') || 
            data.reply.toLowerCase().includes('what') || 
            data.reply.toLowerCase().includes('when') || 
            data.reply.toLowerCase().includes('do you') || 
            data.reply.toLowerCase().includes('are you') || 
            data.reply.toLowerCase().includes('have you'))) {
          // This is a follow-up question with audio, play the audio file
          console.log('🎵 Playing follow-up question audio:', data.audio_url);
          const audio = new Audio(data.audio_url);
          audio.play()
            .then(() => {
              console.log('🎵 Follow-up question audio played successfully');
            })
            .catch((error) => {
              console.log('🎵 Follow-up question audio play failed, falling back to TTS:', error);
              speakText(data.reply);
            });
        } else {
          // Regular response, use TTS
          speakText(data.reply);
        }
      }
      
    } catch (error) {
      console.error('Error calling chat API:', error);
      const errorReply: Message = { 
        id: Date.now() + 1, 
        role: "assistant", 
        content: "I'm sorry, I'm having trouble connecting to the server right now. Please try again later.", 
        timestamp: time 
      };
      setMessages((m) => [...m, errorReply]);
      setErrorMessage("Failed to connect to chat service. Please check your connection and try again.");
      setTimeout(() => setErrorMessage(null), 5000);
    }
  };

  // Font size styles
  const fontSizeStyles = {
    small: { fontSize: "sm" },
    normal: { fontSize: "md" },
    large: { fontSize: "lg" },
    xlarge: { fontSize: "xl" }
  };

  // High contrast styles
  const contrastStyles = highContrast ? {
    bg: isDark ? "#000000" : "#ffffff",
    color: isDark ? "#ffffff" : "#000000",
    borderColor: isDark ? "#ffffff" : "#000000"
  } : {};

  // Images mode: options and flow rendering
  const bodyParts = [
    { id: "head", name: "Head", en: "Head", arr: "Ulpe" },
    { id: "eyes", name: "Eyes", en: "Eyes", arr: "Irlperle" },
    { id: "ears", name: "Ears", en: "Ears", arr: "Areye" },
    { id: "mouth", name: "Mouth", en: "Mouth", arr: "Alkwe" },
    { id: "chest", name: "Chest", en: "Chest", arr: "Inwenge" },
    { id: "stomach", name: "Stomach", en: "Stomach", arr: "Atnerte" },
    { id: "arms", name: "Arms", en: "Arms", arr: "Alyerre" },
    { id: "legs", name: "Legs", en: "Legs", arr: "Ampe" },
    { id: "back", name: "Back", en: "Back", arr: "Angwerre" },
    { id: "general", name: "General", en: "General", arr: "Arrantherre" },
  ];
  

  const conditions: Record<string, { id: string; en: string; arr: string }[]> = {
    head: [
      { id: "headache", en: "Headache", arr: "arnterre atnyeneme" }, // head pain
      { id: "dizziness", en: "Dizziness", arr: "tyerre-irreme" },
      { id: "confusion", en: "Confusion", arr: "arrantherre aneme" },
      { id: "fever", en: "Fever", arr: "arnterre arrkayeye" }
    ],
    eyes: [
      { id: "blurry", en: "Blurry Vision", arr: "irlperle arrpenhe atnyeneme" },
      { id: "pain", en: "Eye Pain", arr: "irlperle atnyeneme" },
      { id: "dry", en: "Dry Eyes", arr: "irlperle arlenye" },
      { id: "red", en: "Red Eyes", arr: "irlperle rertwe" }
    ],
    ears: [
      { id: "pain", en: "Ear Pain", arr: "areye atnyeneme" },
      { id: "ringing", en: "Ringing", arr: "areye irrpeme" },
      { id: "hearing", en: "Hearing Loss", arr: "areye mapeme" },
      { id: "pressure", en: "Pressure", arr: "areye ilpepe" }
    ],
    mouth: [
      { id: "toothache", en: "Toothache", arr: "alkwe atnyeneme" },
      { id: "sore", en: "Sore Throat", arr: "alkwe angkeme atnyeneme" },
      { id: "dry", en: "Dry Mouth", arr: "alkwe arlenye" },
      { id: "taste", en: "Taste Loss", arr: "alkwe mapeme" }
    ],
    chest: [
      { id: "chest_pain", en: "Chest Pain", arr: "inwenge atnyeneme" },
      { id: "breathing", en: "Breathing Issues", arr: "inwenge ilpemeye" },
      { id: "cough", en: "Cough", arr: "akngetyeme" },
      { id: "heartbeat", en: "Irregular Heartbeat", arr: "inwenge arntarneme" }
    ],
    stomach: [
      { id: "stomach_pain", en: "Stomach Pain", arr: "atnerte atnyeneme" },
      { id: "nausea", en: "Nausea", arr: "atnerte artwe-irre" },
      { id: "diarrhea", en: "Diarrhea", arr: "atnerte akaltyeme" },
      { id: "constipation", en: "Constipation", arr: "atnerte aneme akaltye" }
    ],
    arms: [
      { id: "pain", en: "Arm Pain", arr: "alyerre atnyeneme" },
      { id: "numbness", en: "Numbness", arr: "alyerre mpwareke" },
      { id: "weakness", en: "Weakness", arr: "alyerre tyerrtye" },
      { id: "swelling", en: "Swelling", arr: "alyerre aperrne" }
    ],
    legs: [
      { id: "pain", en: "Leg Pain", arr: "ampe atnyeneme" },
      { id: "numbness", en: "Numbness", arr: "ampe mpwareke" },
      { id: "weakness", en: "Weakness", arr: "ampe tyerrtye" },
      { id: "swelling", en: "Swelling", arr: "ampe aperrne" }
    ],
    back: [
      { id: "back_pain", en: "Back Pain", arr: "angwerre atnyeneme" },
      { id: "stiffness", en: "Stiffness", arr: "angwerre apetyewarre" },
      { id: "spasm", en: "Muscle Spasm", arr: "angwerre artetye" },
      { id: "limited", en: "Limited Movement", arr: "angwerre mpwareke-irreme" }
    ],
    general: [
      { id: "fatigue", en: "Fatigue", arr: "arrantherre akaltyeme" },
      { id: "weakness", en: "Weakness", arr: "arrantherre tyerrtye" },
      { id: "fever", en: "Fever", arr: "arnterre arrkayeye" },
      { id: "chills", en: "Chills", arr: "arrantherre arrkwethe" }
    ],
  };
  

  const durations = [
    { id: "today", en: "Today", arr: "Alheme nhenhe" },             // today / now
    { id: "1-2", en: "1-2 days", arr: "Uterne mpwareke 1–2" },      // 1–2 days
    { id: "3-7", en: "3-7 days", arr: "Uterne mpwareke 3–7" },      // 3–7 days
    { id: "1-2weeks", en: "1-2 weeks", arr: "Uterne mpeke 1–2" },   // 1–2 weeks
    { id: "2-4weeks", en: "2-4 weeks", arr: "Uterne mpeke 2–4" },   // 2–4 weeks
    { id: "1month+", en: "1+ months", arr: "Uterne mpeke atnyeme 1+" } // 1+ months / long time
  ];


  // ---------- Images for tiles (body parts / conditions / durations) ----------
  const getImageSrc = (kind: 'part' | 'condition' | 'duration', id: string) => {
    // Place your assets in Frontend/public/images/chat/{kind}/{id}.jpg
    // Example: /images/chat/part/head.jpg, /images/chat/condition/headache.jpg, /images/chat/duration/today.jpg
    const safeId = encodeURIComponent(id);
    return `/images/chat/${kind}/${safeId}.jpg`;
  };

  const ImageBox = ({ src, alt, height }: { src: string; alt: string; height: any }) => (
    <Box bg={isDark ? "gray.600" : "gray.300"} h={height} display="flex" alignItems="center" justifyContent="center" position="relative" overflow="hidden">
      <img
        src={src}
        alt={alt}
        style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
        onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }}
      />
    </Box>
  );

  // Auto-finalize images flow: when last step is reached for last selected part,
  // automatically send summary to backend and show progress/popup
  useEffect(() => {
    const shouldAutoFinalize =
      mode === "images" &&
      !finishedImagesFlow &&
      imageFlowStep === 4 &&
      (currentBodyPartIndex + 1 >= selectedBodyParts.length);

    if (!shouldAutoFinalize) return;

    const currentPartId = selectedBodyParts[currentBodyPartIndex] || selectedBodyPart;
    const partName = bodyParts.find(b => b.id === currentPartId)?.en || currentPartId;
    const condName = (conditions[selectedBodyPart] || []).find(c => c.id === selectedCondition)?.name || selectedCondition;
    const durName = durations.find(d => d.id === selectedDuration)?.name || selectedDuration;
    const summary = `${partName} - ${condName} (Intensity: ${symptomIntensity}/10, Duration: ${durName})`;

    const finalize = async () => {
      setFinishedImagesFlow(true);
      addUserMessage(`Symptom: ${summary}`);
      try {
        // Images mode: show short loader before API call (5s)
        startTimedLoader(5000);

        const response = await fetch('http://localhost:5000/api/chat/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Language': 'english',
            'X-Mode': 'images'
          },
          body: JSON.stringify({
            message: '',
            selections: selectedBodyParts.map(id => bodyParts.find(b => b.id === id)?.en || id),
            final: true,
            _context: { language: 'english', mode: 'images' }
          })
        });
        const data = await response.json();
        console.log('🧪 Images auto-finalize: raw API data', data);
        const triageSource = data?.fused_result ?? data?.disease_prediction;
        if (data?.is_final_message && triageSource) {
          console.log('🧪 Images auto-finalize: API success payload', {
            fused_result: data.fused_result,
            disease_prediction: data.disease_prediction
          });
          if (data.disease_prediction) setDiseasePrediction(data.disease_prediction);
          const triage = generateTriageSummary(
            [...messages, { id: Date.now(), role: 'assistant', content: 'Images summary', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }],
            triageSource
          );
          console.log('🧪 Images auto-finalize: triage generated', triage);
          setTriageData(triage);
          setShowTriageModal(true);
          console.log('🧪 Images auto-finalize: triage modal shown');
        } else {
          console.log('🧪 Images auto-finalize: no triageSource found or not final message', {
            is_final_message: data?.is_final_message,
            has_fused_result: Boolean(data?.fused_result),
            has_disease_prediction: Boolean(data?.disease_prediction)
          });
        }
        // Timed loader will stop itself
      } catch (e) {
        console.error('Images mode auto-finalize error', e);
        setShowProgressBar(false);
        setIsAnalyzing(false);
      }
    };

    finalize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageFlowStep, currentBodyPartIndex, selectedBodyParts.length, finishedImagesFlow, mode]);

  const renderImagesFlow = () => {
    if (finishedImagesFlow) {
      return <Text>Assessment generated. Please check the popup.</Text>;
    }
    if (imageFlowStep === 0) {
      return (
        <>
          <Text fontWeight="semibold" mb={3}>Select body part</Text>
          <Flex wrap="wrap" gap={3}>
            {bodyParts.map(({ id, name, en, arr }) => {
              const selected = selectedBodyParts.includes(id);
              return (
              <Box key={id} role="button" onClick={() => {
                  setSelectedBodyParts(prev => selected ? prev.filter(x => x !== id) : [...prev, id]);
                }}
                borderWidth="1px" borderRadius="lg" overflow="hidden" bg={isDark ? "gray.700" : "white"} _hover={{ shadow: "md" }}
                w={{ base: "130px", md: "160px" }} borderColor={selected ? "teal.500" : undefined}>
                <Box position="relative">
                  <ImageBox src={getImageSrc('part', id)} alt={en} height={{ base: "90px", md: "110px" }} />
                  {selected && (
                    <Box position="absolute" top={2} right={2} bg="teal.500" color="white" px={2} py={1} borderRadius="md" fontSize="xs">Selected</Box>
                  )}
                </Box>
                <Box p={2} textAlign="center">
                  <Text fontWeight="semibold">{en}</Text>
                  <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>{lang === "arrernte" ? arr : en}</Text>
                </Box>
              </Box>
            );})}
          </Flex>
          <Flex mt={4} gap={3} align="center">
          <Button
  aria-label="Proceed"
  borderRadius="full"
  size="lg"
  disabled={selectedBodyParts.length === 0}
  style={{
    backgroundColor: "green",
    color: "white",
    width: "48px",
    height: "48px",
    padding: 0,
    minWidth: "48px",
    border: "none",
    cursor: selectedBodyParts.length === 0 ? "not-allowed" : "pointer",
  }}
  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "darkgreen")}
  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "green")}
  onClick={() => {
    setCurrentBodyPartIndex(0);
    setSelectedBodyPart(selectedBodyParts[0]);
    setImageFlowStep(1);
    addUserMessage(
      `Selected parts: ${selectedBodyParts
        .map((id) => bodyParts.find((b) => b.id === id)?.name)
        .join(", ")}`
    );
  }}
>
  <FaCheck />
</Button>

            {selectedBodyParts.length > 0 && (
              <Text fontSize="sm" color={isDark ? "gray.300" : "gray.600"}>{selectedBodyParts.length} selected</Text>
            )}
          </Flex>
        </>
      );
    }
    if (imageFlowStep === 1) {
      const currentPartId = selectedBodyParts[currentBodyPartIndex] || selectedBodyPart;
      const currentPartName = bodyParts.find(b => b.id === currentPartId)?.en || currentPartId;
      const opts = conditions[currentPartId] || [];
      return (
        <>
          <Text fontWeight="semibold" mb={3}>Select condition for</Text>
          <Box mb={3} borderWidth="1px" borderRadius="lg" overflow="hidden" bg={isDark ? "gray.700" : "white"} w={{ base: "180px", md: "220px" }}>
            <ImageBox src={getImageSrc('part', currentPartId)} alt={currentPartName} height={{ base: "80px", md: "100px" }} />
            <Box p={2} textAlign="center">
              <Text fontWeight="semibold">{currentPartName}</Text>
              <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>{lang === "arrernte" ? `Arrernte ${currentPartName}` : currentPartName}</Text>
            </Box>
          </Box>
          <Flex wrap="wrap" gap={3}>
            {opts.map(({ id, en, arr }) => (
              <Box key={id} role="button" onClick={() => { setSelectedCondition(id); setImageFlowStep(2); addUserMessage(`Condition: ${en}`); }}
                borderWidth="1px" borderRadius="lg" overflow="hidden" bg={isDark ? "gray.700" : "white"} _hover={{ shadow: "md" }}
                w={{ base: "180px", md: "220px" }}>
                <ImageBox src={getImageSrc('condition', id)} alt={en} height={{ base: "80px", md: "100px" }} />
                <Box p={2} textAlign="center">
                  <Text fontWeight="semibold">{en}</Text>
                  <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>{lang === "arrernte" ? arr : en}</Text>
                </Box>
              </Box>
            ))}
          </Flex>
        </>
      );
    }
    if (imageFlowStep === 2) {
      return (
        <>
          <Text fontWeight="semibold" mb={3}>Select intensity (1-10)</Text>
          <Box mb={3} borderWidth="1px" borderRadius="lg" overflow="hidden" bg={isDark ? "gray.700" : "white"} w={{ base: "180px", md: "220px" }}>
            <ImageBox src={getImageSrc('part', (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))} alt={bodyParts.find(b => b.id === (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))?.en || ''} height={{ base: "80px", md: "100px" }} />
                <Box p={2} textAlign="center">
                  <Text fontWeight="semibold">{bodyParts.find(b => b.id === (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))?.en}</Text>
                  <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>
                    {lang === "arrernte"
                      ? `Arrernte ${bodyParts.find(b => b.id === (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))?.en}`
                      : bodyParts.find(b => b.id === (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))?.en}
                  </Text>
                </Box>
          </Box>
          <Flex wrap="wrap" gap={3}>
            {Array.from({ length: 10 }).map((_, idx) => {
              const v = idx + 1;
              return (
                <Box key={v} role="button" onClick={() => { setSymptomIntensity(v); setImageFlowStep(3); addUserMessage(`Intensity: ${v}/10`); }}
                  borderWidth="1px" borderRadius="lg" overflow="hidden" bg={isDark ? "gray.700" : "white"} _hover={{ shadow: "md" }}
                  w={{ base: "70px", md: "90px" }}>
                  <Box bg={v <= 3 ? (isDark ? "green.900" : "green.200") : v <= 7 ? (isDark ? "yellow.900" : "yellow.200") : (isDark ? "red.900" : "red.200")}
                       h={{ base: "60px", md: "70px" }} display="flex" alignItems="center" justifyContent="center">
                    <Text fontWeight="bold">{v}</Text>
                  </Box>
                  
                </Box>
              );
            })}
          </Flex>
        </>
      );
    }
    if (imageFlowStep === 3) {
      return (
        <>
          <Text fontWeight="semibold" mb={3}>How long has this been happening?</Text>
          <Box mb={3} borderWidth="1px" borderRadius="lg" overflow="hidden" bg={isDark ? "gray.700" : "white"} w={{ base: "180px", md: "220px" }}>
            <ImageBox src={getImageSrc('part', (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))} alt={bodyParts.find(b => b.id === (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))?.en || ''} height={{ base: "80px", md: "100px" }} />
            <Box p={2} textAlign="center">
              <Text fontWeight="semibold">{bodyParts.find(b => b.id === (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))?.en}</Text>
              <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>Arrernte {bodyParts.find(b => b.id === (selectedBodyParts[currentBodyPartIndex] || selectedBodyPart))?.en}</Text>
            </Box>
          </Box>
          <Flex wrap="wrap" gap={3}>
            {durations.map(({ id, en, arr }) => (
              <Box key={id} role="button" onClick={() => { setSelectedDuration(id); setImageFlowStep(4); addUserMessage(`Duration: ${en}`); }}
                borderWidth="1px" borderRadius="lg" overflow="hidden" bg={isDark ? "gray.700" : "white"} _hover={{ shadow: "md" }}
                w={{ base: "180px", md: "220px" }}>
                <ImageBox src={getImageSrc('duration', id)} alt={en} height={{ base: "80px", md: "100px" }} />
                <Box p={2} textAlign="center">
                  <Text fontWeight="semibold">{en}</Text>
                  <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>{lang === "arrernte" ? arr : en}</Text>
                </Box>
              </Box>
            ))}
          </Flex>
        </>
      );
    }
    // Step 4: review and add another or finish
    const currentPartId = selectedBodyParts[currentBodyPartIndex] || selectedBodyPart;
    const partName = bodyParts.find(b => b.id === currentPartId)?.en || currentPartId;
    const condName = (conditions[selectedBodyPart] || []).find(c => c.id === selectedCondition)?.name || selectedCondition;
    const durName = durations.find(d => d.id === selectedDuration)?.name || selectedDuration;
    const summary = `${partName} - ${condName} (Intensity: ${symptomIntensity}/10, Duration: ${durName})`;
    return (
      <VStack align="start" gap={3}>
        <Text fontWeight="semibold">Summary</Text>
        <Text>{summary}</Text>
        <Flex gap={2}>
          <Button colorScheme="green" leftIcon={<FaCheck />} onClick={async () => {
            addUserMessage(`Symptom: ${summary}`);
            const nextIndex = currentBodyPartIndex + 1;
            if (nextIndex < selectedBodyParts.length) {
              setCurrentBodyPartIndex(nextIndex);
              setSelectedBodyPart(selectedBodyParts[nextIndex]);
              setSelectedCondition("");
              setSymptomIntensity(5);
              setSelectedDuration("");
              setImageFlowStep(1);
              return;
            }
            // Finalize once
            setFinishedImagesFlow(true);
            try {
              // Images mode: show short loader before API call (5s)
              startTimedLoader(5000);
              const response = await fetch('http://localhost:5000/api/chat/', {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  'X-Language': 'english',
                  'X-Mode': 'images'
                },
                body: JSON.stringify({
                  message: '',
                  selections: selectedBodyParts.map(id => bodyParts.find(b => b.id === id)?.en || id),
                  final: true,
                  _context: { language: 'english', mode: 'images' }
                })
              });
              const data = await response.json();
              console.log('🧪 Images manual Done: raw API data', data);
              const triageSource = data?.fused_result ?? data?.disease_prediction;
              if (data?.is_final_message && triageSource) {
                console.log('🧪 Images manual Done: API success payload', {
                  fused_result: data.fused_result,
                  disease_prediction: data.disease_prediction
                });
                // Timed loader is already running; no additional loader
                if (data.disease_prediction) setDiseasePrediction(data.disease_prediction);
                const triage = generateTriageSummary(
                  [...messages, { id: Date.now(), role: 'assistant', content: 'Images summary', timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }],
                  triageSource
                );
                console.log('🧪 Images manual Done: triage generated', triage);
                setTriageData(triage);
                setShowTriageModal(true);
                console.log('🧪 Images manual Done: triage modal shown');
              } else {
                console.log('🧪 Images manual Done: no triageSource found or not final message', {
                  is_final_message: data?.is_final_message,
                  has_fused_result: Boolean(data?.fused_result),
                  has_disease_prediction: Boolean(data?.disease_prediction)
                });
              }
            } catch (e) {
              console.error('Images mode finalize error', e);
            }
          }}>Done</Button>
        </Flex>
      </VStack>
    );
  };

  return (
    <Container maxW="100%" minH="100vh" display="flex" flexDir="column" py={2} px={4} position="relative" {...contrastStyles}>
      {/* Audio Prompt for Arrernte Voice Mode */}
      {showAudioPrompt && lang === "arrernte" && mode === "voice" && (
        <Box
          position="fixed"
          top="50%"
          left="50%"
          transform="translate(-50%, -50%)"
          bg={isDark ? "gray.800" : "white"}
          color={isDark ? "white" : "black"}
          p={6}
          borderRadius="lg"
          shadow="xl"
          border="2px solid"
          borderColor="teal.500"
          zIndex={2000}
          textAlign="center"
          maxW="400px"
        >
          <Text fontSize="lg" fontWeight="bold" mb={3}>
            🎵 Tap to hear welcome message
          </Text>
          <Text fontSize="sm" mb={4}>
            Click the microphone button to hear the Arrernte welcome message
          </Text>
          <Button
            colorScheme="teal"
            onClick={() => {
              setShowAudioPrompt(false);
              // Trigger the welcome audio play
              if (!welcomeAudioPlayed && !isPlayingWelcomeAudio.current) {
                isPlayingWelcomeAudio.current = true;
                const audio = new Audio("http://localhost:5000/static/audio/welcomeMessage_arrernte.mp3");
                audio.play()
                  .then(() => {
                    setWelcomeAudioPlayed(true);
                    isPlayingWelcomeAudio.current = false;
                    console.log('🎵 Welcome audio played from prompt');
                  })
                  .catch((error) => {
                    console.error('🎵 Welcome audio play failed from prompt:', error);
                    isPlayingWelcomeAudio.current = false;
                  });
              }
            }}
          >
            Play Welcome Audio
          </Button>
        </Box>
      )}
      
      {/* Accessibility Controls */}
      <Box 
        position="fixed" 
        top={{ base: "70px", sm: "75px", md: "80px", lg: "85px" }}
        right={{ base: 2, sm: 3, md: 4, lg: 6 }}
        display="flex" 
        flexDirection={{ base: "column", sm: "column", md: "row", lg: "row" }}
        gap={{ base: 1, sm: 1, md: 2, lg: 2 }}
        zIndex={1000}
        bg={isDark ? "gray.800" : "white"}
        p={{ base: 1, sm: 1, md: 2, lg: 2 }}
        borderRadius="lg"
        shadow="lg"
        border="1px solid"
        borderColor={isDark ? "gray.600" : "gray.200"}
        maxW={{ base: "60px", sm: "60px", md: "none", lg: "none" }}
        minW={{ base: "60px", sm: "60px", md: "auto", lg: "auto" }}
      >
        <IconButton 
          aria-label="Toggle color mode" 
          onClick={() => setIsDark((v) => !v)} 
          variant="ghost" 
          size={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          title="Toggle dark mode (Ctrl+D)"
          bg={isDark ? "gray.700" : "gray.100"}
          _hover={{ bg: isDark ? "gray.600" : "gray.200" }}
          fontSize={{ base: "sm", sm: "sm", md: "md", lg: "md" }}
        >
          {isDark ? "☀️" : "🌙"}
        </IconButton>
        <IconButton 
          aria-label="Toggle high contrast mode" 
          onClick={() => setHighContrast((v) => !v)} 
          variant="ghost" 
          size={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          title="Toggle high contrast (Ctrl+H)"
          bg={highContrast ? "yellow.400" : (isDark ? "gray.700" : "gray.100")}
          _hover={{ bg: highContrast ? "yellow.300" : (isDark ? "gray.600" : "gray.200") }}
          fontSize={{ base: "sm", sm: "sm", md: "md", lg: "md" }}
        >
          🎯
        </IconButton>
        <IconButton 
          aria-label="Increase font size" 
          onClick={() => setFontSize(prev => prev === "small" ? "normal" : prev === "normal" ? "large" : "xlarge")} 
          variant="ghost" 
          size={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          title="Increase font size (Ctrl++)"
          bg={isDark ? "gray.700" : "gray.100"}
          _hover={{ bg: isDark ? "gray.600" : "gray.200" }}
          fontSize={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
        >
          🔍+
        </IconButton>
        <IconButton 
          aria-label="Decrease font size" 
          onClick={() => setFontSize(prev => prev === "xlarge" ? "large" : prev === "large" ? "normal" : "small")} 
          variant="ghost" 
          size={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          title="Decrease font size (Ctrl+-)"
          bg={isDark ? "gray.700" : "gray.100"}
          _hover={{ bg: isDark ? "gray.600" : "gray.200" }}
          fontSize={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
        >
          🔍-
        </IconButton>
        <IconButton 
          aria-label="Give feedback" 
          onClick={() => setShowFeedbackModal(true)} 
          variant="ghost" 
          size={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          title="Give feedback or contribute"
          bg={isDark ? "gray.700" : "gray.100"}
          _hover={{ bg: isDark ? "gray.600" : "gray.200" }}
          fontSize={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
        >
          <FaComments />
        </IconButton>
        <IconButton 
          aria-label="Keyboard shortcuts" 
          onClick={() => setShowKeyboardShortcuts(!showKeyboardShortcuts)} 
          variant="ghost" 
          size={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          title="Show keyboard shortcuts"
          bg={showKeyboardShortcuts ? "teal.500" : (isDark ? "gray.700" : "gray.100")}
          _hover={{ bg: showKeyboardShortcuts ? "teal.400" : (isDark ? "gray.600" : "gray.200") }}
          fontSize={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
        >
          ⌨️
        </IconButton>
      </Box>

      {/* Language and Mode Selection - Top Left */}
      <Box 
        position="fixed" 
        top={{ base: "70px", sm: "75px", md: "80px", lg: "85px" }}
        left={{ base: 2, sm: 3, md: 4, lg: 6 }}
        display="flex" 
        flexDirection={{ base: "column", sm: "column", md: "row", lg: "row" }}
        gap={{ base: 1, sm: 1, md: 2, lg: 2 }}
        zIndex={1000}
        bg={isDark ? "gray.800" : "white"}
        p={{ base: 1, sm: 1, md: 2, lg: 2 }}
        borderRadius="lg"
        shadow="lg"
        border="1px solid"
        borderColor={isDark ? "gray.600" : "gray.200"}
      >
        {/* Change Language Button */}
        <Button
          as="a"
          href="/language"
          variant="ghost"
          size={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          bg={isDark ? "gray.700" : "gray.100"}
          _hover={{ bg: isDark ? "gray.600" : "gray.200" }}
          fontSize={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          leftIcon={<FaLanguage />}
          title="Change language"
        >
          Change Language
        </Button>

        {/* Change Mode Button */}
        <Button
          as="a"
          href="/mode"
          variant="ghost"
          size={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          bg={isDark ? "gray.700" : "gray.100"}
          _hover={{ bg: isDark ? "gray.600" : "gray.200" }}
          fontSize={{ base: "xs", sm: "xs", md: "sm", lg: "sm" }}
          leftIcon={mode === "voice" ? <FaMicrophone /> : mode === "images" ? <FaEye /> : <FaComments />}
          title="Change communication mode"
        >
          Change Mode
        </Button>
      </Box>

      {/* Keyboard Shortcuts Dropdown */}
      {showKeyboardShortcuts && (
        <Box
          data-keyboard-shortcuts
          position="fixed"
          top={{ base: "140px", sm: "145px", md: "150px", lg: "155px" }}
          right={{ base: 2, sm: 3, md: 4, lg: 6 }}
          zIndex={1001}
          bg={isDark ? "gray.800" : "white"}
          p={3}
          borderRadius="lg"
          shadow="2xl"
          border="1px solid"
          borderColor={isDark ? "gray.600" : "gray.200"}
          maxW={{ base: "280px", sm: "320px", md: "350px", lg: "380px" }}
          minW={{ base: "280px", sm: "320px", md: "350px", lg: "380px" }}
        >
          <VStack align="start" spacing={2}>
            <HStack justify="space-between" w="100%">
              <Text fontWeight="bold" fontSize="sm" color={isDark ? "gray.100" : "gray.800"}>
                Keyboard Shortcuts
              </Text>
              <IconButton
                aria-label="Close shortcuts"
                onClick={() => setShowKeyboardShortcuts(false)}
                variant="ghost"
                size="xs"
                color={isDark ? "gray.400" : "gray.600"}
                _hover={{ bg: isDark ? "gray.700" : "gray.100" }}
              >
                <FaTimes />
              </IconButton>
            </HStack>
            
            <Box w="100%" h="1px" bg={isDark ? "gray.600" : "gray.300"} />
            
            <VStack align="start" spacing={1} w="100%">
              <HStack spacing={2} w="100%">
                <Text as="kbd" bg={isDark ? "gray.700" : "gray.200"} px={2} py={1} borderRadius="sm" fontSize="xs" minW="60px" textAlign="center">
                  Space
                </Text>
                <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>
                  Start/Stop recording (voice mode)
                </Text>
              </HStack>
              
              <HStack spacing={2} w="100%">
                <Text as="kbd" bg={isDark ? "gray.700" : "gray.200"} px={2} py={1} borderRadius="sm" fontSize="xs" minW="60px" textAlign="center">
                  Enter
                </Text>
                <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>
                  Pause/Resume recording (voice mode)
                </Text>
              </HStack>
              
              <HStack spacing={2} w="100%">
                <Text as="kbd" bg={isDark ? "gray.700" : "gray.200"} px={2} py={1} borderRadius="sm" fontSize="xs" minW="60px" textAlign="center">
                  Escape
                </Text>
                <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>
                  Stop recording (voice mode)
                </Text>
              </HStack>
              
              <HStack spacing={2} w="100%">
                <Text as="kbd" bg={isDark ? "gray.700" : "gray.200"} px={2} py={1} borderRadius="sm" fontSize="xs" minW="60px" textAlign="center">
                  Ctrl+D
                </Text>
                <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>
                  Toggle dark mode
                </Text>
              </HStack>
              
              <HStack spacing={2} w="100%">
                <Text as="kbd" bg={isDark ? "gray.700" : "gray.200"} px={2} py={1} borderRadius="sm" fontSize="xs" minW="60px" textAlign="center">
                  Ctrl+H
                </Text>
                <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>
                  Toggle high contrast
                </Text>
              </HStack>
              
              <HStack spacing={2} w="100%">
                <Text as="kbd" bg={isDark ? "gray.700" : "gray.200"} px={2} py={1} borderRadius="sm" fontSize="xs" minW="60px" textAlign="center">
                  Ctrl++
                </Text>
                <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>
                  Increase font size
                </Text>
              </HStack>
              
              <HStack spacing={2} w="100%">
                <Text as="kbd" bg={isDark ? "gray.700" : "gray.200"} px={2} py={1} borderRadius="sm" fontSize="xs" minW="60px" textAlign="center">
                  Ctrl+-
                </Text>
                <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>
                  Decrease font size
                </Text>
              </HStack>
            </VStack>
          </VStack>
        </Box>
      )}
      <Stack gap={1} align="center" textAlign="center">
        <Heading size="md" color={isDark ? "gray.100" : undefined}>SwinSACA Chat</Heading>
        <Text fontSize="xs" color={isDark ? "gray.300" : "gray.600"}>Mode: {mounted ? mode : ""}{mounted ? "" : ""}{mounted ? `, Language: ${lang}` : ""}</Text>
        
        {/* Error Message Display */}
        {errorMessage && (
          <Box 
            bg="red.500" 
            color="white" 
            p={4} 
            borderRadius="md" 
            maxW="md" 
            role="alert"
            aria-live="polite"
          >
            <Text fontWeight="bold">⚠️ Error:</Text>
            <Text>{errorMessage}</Text>
          </Box>
        )}
      </Stack>
      <Flex flex={1} direction="column" gap={1} mt={1} pr={{ base: "70px", sm: "70px", md: 0, lg: 0 }}>
        <Box ref={listRef as any} h="calc(100vh - 240px)" borderWidth="1px" borderRadius="lg" p={3} overflowY="auto" bg={isDark ? "#0b1220" : "gray.200"}>
          <Stack gap={2}>
            {messages.map((m) => (
              <Flex key={m.id} justify={m.role === "user" ? "flex-end" : "flex-start"} align="flex-end" gap={3}>
                {m.role === "assistant" && (
                  <Box w={10} h={10} borderRadius="full" overflow="hidden" flexShrink={0} bg={isDark ? "whiteAlpha.900" : "white"} display="flex" alignItems="center" justifyContent="center" borderWidth="1px">
                    <img src={logoLight} alt="SwinSACA" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  </Box>
                )}
                <Box 
                  maxW={{ base: "85%", md: "60%" }} 
                  bg={highContrast ? (m.role === "user" ? "#000000" : "#ffffff") : (m.role === "user" ? "teal.500" : (isDark ? "whiteAlpha.900" : "gray.100"))} 
                  color={highContrast ? (m.role === "user" ? "#ffffff" : "#000000") : (m.role === "user" ? "white" : (isDark ? "black" : "black"))} 
                  px={3} 
                  py={2} 
                  borderRadius="xl"
                  border={highContrast ? "2px solid" : "none"}
                  borderColor={highContrast ? (m.role === "user" ? "#ffffff" : "#000000") : "transparent"}
                >
                  <Box maxH="30vh" overflowY="auto">
                    <Text {...fontSizeStyles[fontSize as keyof typeof fontSizeStyles]}>{m.content}</Text>
                  </Box>
                  <Flex justify="space-between" align="center" mt={1}>
                  {m.role === "user" && (
                      <Text fontSize="sm" opacity={0.8}>{m.timestamp}</Text>
                    )}
                    {m.role === "assistant" && mode === "voice" && m.audioUrl && (
                      <IconButton
                        aria-label="Replay audio"
                        onClick={() => {
                          const audio = new Audio(m.audioUrl);
                          audio.play().catch(console.error);
                        }}
                        size="xs"
                        variant="ghost"
                        colorScheme="teal"
                        icon={<FaMicrophone />}
                        title="Replay audio"
                      />
                    )}
                  </Flex>
                </Box>
                {m.role === "user" && (
                  <Box w={10} h={10} borderRadius="full" overflow="hidden" flexShrink={0} display="flex" alignItems="center" justifyContent="center" color="teal.600" bg={isDark ? "whiteAlpha.900" : "white"} borderWidth="1px">
                    <FaUserCircle size={28} />
                  </Box>
                )}
              </Flex>
            ))}

            {/* Inline images-mode selection UI as an assistant message inside chatbox */}
            {mode === "images" && (
              <Flex justify="center" align="stretch" gap={0} w="100%">
                <Box w="100%" bg="transparent" color="inherit" px={0} py={0}>
                  {renderImagesFlow()}
                </Box>
              </Flex>
            )}
          </Stack>
        </Box>
        {mode === "voice" ? (
          <Box py={1}>
            <Box mb={1} borderWidth="1px" borderRadius="lg" overflow="hidden">
              <canvas ref={canvasRef as any} style={{ width: "100%", height: 40, display: "block" }} />
            </Box>
            <Flex justify="center" align="center">
              <IconButton
                aria-label={isRecording ? "Stop recording (Press Space)" : "Start recording (Press Space)"}
                onClick={isRecording ? stopRecording : startRecording}
                bg={isRecording ? "red.500" : (isDark ? "teal.400" : "teal.600")}
                _hover={{ bg: isRecording ? "red.400" : (isDark ? "teal.300" : "teal.700") }}
                _focus={{ 
                  boxShadow: "0 0 0 4px rgba(66, 153, 225, 0.6)",
                  outline: "none"
                }}
                color={isRecording ? "white" : (isDark ? "gray.900" : "white")}
                size="lg"
                w="50px"
                h="50px"
                fontSize="lg"
                tabIndex={0}
              >
                <FaMicrophone />
              </IconButton>
              {lang === "arrernte" && (
                <>
                  <input
                    id="arr-upload"
                    type="file"
                    accept="audio/*"
                    style={{ display: "none" }}
                    onChange={async (e) => {
                      const inputEl = e.currentTarget as HTMLInputElement;
                      const file = inputEl.files?.[0];
                      if (!file) return;
                      try {
                        const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                        // Show a placeholder user message
                        const userMsg = { id: Date.now(), role: "user" as const, content: "[Uploaded audio]", timestamp: time };
                        setMessages((m) => [...m, userMsg]);
                        
                        // Show analyzing placeholder message
                        const analyzingMsg = { 
                          id: Date.now() + 0.5, 
                          role: "assistant" as const, 
                          content: "🔍 Analyzing audio... Please wait while I process your message.", 
                          timestamp: time 
                        };
                        setMessages((m) => [...m, analyzingMsg]);
                        const formData = new FormData();
                        formData.append('audio', file, file.name);
                        formData.append('language', 'arrernte');
                        formData.append('mode', 'voice');

                        const response = await fetch('http://localhost:5000/api/chat/', {
                          method: 'POST',
                          headers: {
                            'X-Language': 'arrernte',
                            'X-Mode': 'voice',
                          },
                          body: formData
                        });

                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        const data = await response.json();

                        // Replace placeholder with transcribed text if any
                        if (data.transcribed_text) {
                          setMessages((m) => m.map(msg => msg.id === userMsg.id ? { ...msg, content: data.transcribed_text } : msg));
                        }

                        // Replace the analyzing placeholder with the actual response
                        const reply: Message = {
                          id: Date.now() + 1,
                          role: 'assistant',
                          content: data.reply,
                          timestamp: time,
                          audioUrl: data.audio_url || undefined,
                        };
                        setMessages((m) => m.map(msg => msg.id === analyzingMsg.id ? reply : msg));
                        
                        // Check if this is a final message for disease prediction
                        const isFinalMessage = data.is_final_message || false;
                        
                        if (isFinalMessage) {
                          // Store the disease prediction data
                          if (data.disease_prediction) {
                            setDiseasePrediction(data.disease_prediction);
                          }

                          // Show loader and delay summary to match progress
                          setShowProgressBar(true);
                          setIsAnalyzing(true);
                          setProgressStep(0);
                          setProgressMessage("Analyzing symptoms...");

                          // Simulate progress steps
                          const progressSteps = [
                            { message: "Analyzing symptoms...", progress: 20 },
                            { message: "Processing medical data...", progress: 40 },
                            { message: "Running ML models...", progress: 60 },
                            { message: "Generating assessment...", progress: 80 },
                            { message: "Finalizing results...", progress: 100 }
                          ];

                          progressSteps.forEach((step, index) => {
                            setTimeout(() => {
                              setProgressStep(step.progress);
                              setProgressMessage(step.message);
                            }, index * 1200);
                          });

                          // Show triage summary after delay
                          setTimeout(() => {
                            const triage = generateTriageSummary([...messages, userMsg], data.disease_prediction);
                            setTriageData(triage);
                            setShowTriageModal(true);
                            setShowProgressBar(false);
                            setIsAnalyzing(false);
                          }, 6000);

                          // Voice announcements for assessment results
                          speakText("Medical triage summary is ready. Please review the assessment results.");
                          setTimeout(() => {
                            if (data.disease_prediction && data.disease_prediction.final) {
                              speakText(`Assessment result: ${data.disease_prediction.final.disease_label}`);
                            }
                          }, 3000);
                          setTimeout(() => {
                            speakText("Please visit a doctor for proper medical evaluation.");
                          }, 6000);
                        }
                        
                        if (mode === 'voice' && data.audio_url) {
                          const audio = new Audio(data.audio_url);
                          audio.play().catch(console.error);
                        }
                      } catch (err) {
                        console.error('Upload voice error:', err);
                        const time = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
                        setMessages((m) => [...m, { id: Date.now() + 1, role: 'assistant', content: 'Failed to process uploaded audio. Please try again.', timestamp: time }]);
                      } finally {
                        inputEl.value = '';
                      }
                    }}
                  />
                  <IconButton
                    aria-label="Upload Arrernte audio"
                    onClick={() => document.getElementById('arr-upload')?.click()}
                    ml={2}
                    bg={isDark ? 'blue.400' : 'blue.600'}
                    _hover={{ bg: isDark ? 'blue.300' : 'blue.700' }}
                    _focus={{ boxShadow: '0 0 0 4px rgba(66, 153, 225, 0.6)', outline: 'none' }}
                    color={isDark ? 'gray.900' : 'white'}
                    size="lg"
                    w="50px"
                    h="50px"
                    fontSize="lg"
                    tabIndex={0}
                    title="Upload Arrernte audio"
                  >
                    <FaThumbtack />
                  </IconButton>
                </>
              )}
              {isRecording && (
                <IconButton
                  aria-label={isPaused ? "Resume recording (Press Enter)" : "Pause recording (Press Enter)"}
                  onClick={togglePause}
                  ml={2}
                  bg={"yellow.400"}
                  _hover={{ bg: "yellow.300" }}
                  _focus={{ 
                    boxShadow: "0 0 0 4px rgba(66, 153, 225, 0.6)",
                    outline: "none"
                  }}
                  color={"black"}
                  size="md"
                  w="40px"
                  h="40px"
                  fontSize="sm"
                  tabIndex={0}
                >
                  {isPaused ? <FaPlay /> : <FaPause />}
                </IconButton>
              )}
            </Flex>
          </Box>
        ) : mode === "images" ? (
          <Box />
        ) : (
          <Box as="form" onSubmit={onSubmit} display="flex" gap={2}>
            <Input 
              size="md" 
              value={input} 
              onChange={(e) => setInput(e.target.value)} 
              placeholder="Type your message..." 
              bg={isDark ? "whiteAlpha.200" : "gray.200"} 
              borderColor={isDark ? "whiteAlpha.400" : "gray.300"} 
              _placeholder={{ color: isDark ? "whiteAlpha.700" : "gray.600" }}
              _focus={{
                boxShadow: "0 0 0 2px rgba(66, 153, 225, 0.6)",
                outline: "none"
              }}
              aria-label="Message input"
              {...fontSizeStyles[fontSize as keyof typeof fontSizeStyles]}
            />
            <Button 
              size="md" 
              type="submit" 
              bg={isDark ? "teal.400" : "teal.600"} 
              color={isDark ? "gray.900" : "white"} 
              _hover={{ bg: isDark ? "teal.300" : "teal.700" }}
              _focus={{
                boxShadow: "0 0 0 2px rgba(66, 153, 225, 0.6)",
                outline: "none"
              }}
              aria-label="Send message"
            >
              Send
            </Button>
          </Box>
        )}
        
      </Flex>

      {/* Medical Triage Summary Modal */}
      {showTriageModal && (
        <Box
          position="fixed"
          top={0}
          left={0}
          right={0}
          bottom={0}
          zIndex={1000}
          display="flex"
          alignItems="center"
          justifyContent="center"
          p={4}
        >
          {/* Overlay */}
          <Box 
            position="absolute" 
            top={0} 
            left={0} 
            right={0} 
            bottom={0} 
            bg="blackAlpha.600" 
            backdropFilter="blur(4px)"
            onClick={() => setShowTriageModal(false)}
          />
          
          {/* Modal Content */}
          <Box 
            maxW="6xl"
            maxH="90vh" 
            overflowY="auto"
            bg={isDark ? "gray.800" : "white"}
            color={isDark ? "white" : "black"}
            borderRadius="md"
            shadow="2xl"
            position="relative"
            zIndex={1001}
            w="full"
          >
          <Box 
            fontSize="2xl" 
            fontWeight="bold" 
            textAlign="center"
            bg={triageData?.severity?.color === "red" ? "red.500" : 
                triageData?.severity?.color === "orange" ? "orange.500" : 
                triageData?.severity?.color === "yellow" ? "yellow.500" : 
                triageData?.severity?.color === "green" ? "green.500" : "blue.500"}
            color="white"
            position="relative"
            p={6}
            borderTopRadius="md"
          >
            🏥 Medical Triage Assessment Summary
            <IconButton
              aria-label="Close triage summary"
              icon={<FaTimes />}
              size="lg"
              color="white"
              variant="ghost"
              position="absolute"
              right={4}
              top="50%"
              transform="translateY(-50%)"
              onClick={() => setShowTriageModal(false)}
              _hover={{ bg: "whiteAlpha.200" }}
              _focus={{
                boxShadow: "0 0 0 2px rgba(255, 255, 255, 0.6)",
                outline: "none"
              }}
            />
          </Box>
          <Box p={8}>
            {triageData && (
              <VStack spacing={6} align="stretch">
                {/* Severity Level with Progress Bar */}
                <Box textAlign="center">
                  <Heading size="lg" mb={4}>Severity Assessment</Heading>
                  <VStack spacing={4}>
                    <Badge 
                      size="lg" 
                      colorScheme={triageData.severity.color}
                      fontSize="xl"
                      px={6}
                      py={3}
                      borderRadius="full"
                    >
                      {triageData.severity.label} - Level {triageData.severity.level}/5
                    </Badge>
                    <Box 
                      w="100%" 
                      h="30px" 
                      bg={isDark ? "gray.600" : "gray.200"} 
                      borderRadius="full"
                      overflow="hidden"
                      position="relative"
                    >
                      <Box
                        w={`${triageData.severity.level * 20}%`}
                        h="100%"
                        bg={triageData.severity.color + ".500"}
                        borderRadius="full"
                        transition="width 0.3s ease"
                      />
                    </Box>
                    <Text fontSize="lg" fontWeight="semibold" color={triageData.severity.color + ".500"}>
                      {triageData.severity.description}
                    </Text>
                  </VStack>
                </Box>

                <Box h="1px" bg={isDark ? "gray.600" : "gray.300"} />

                {/* Chat Summary */}
                <Box>
                  <Heading size="md" mb={3} display="flex" alignItems="center" gap={2}>
                    <FaInfoCircle />
                    Chat Summary
                  </Heading>
                  <Box 
                    bg={isDark ? "gray.700" : "gray.100"} 
                    p={4} 
                    borderRadius="md"
                    border="1px solid"
                    borderColor={isDark ? "gray.600" : "gray.300"}
                  >
                    <Text {...fontSizeStyles[fontSize as keyof typeof fontSizeStyles]}>
                      {triageData.chatSummary}
                    </Text>
                  </Box>
                </Box>

                <Box h="1px" bg={isDark ? "gray.600" : "gray.300"} />

                {/* Disease Prediction Results */}
                {diseasePrediction && (
                  <Box>
                    <Heading size="md" mb={3} display="flex" alignItems="center" gap={2}>
                      <FaStethoscope color="blue" />
                      AI Disease Prediction
                    </Heading>
                    <VStack spacing={3} align="stretch">
                      {diseasePrediction.predicted_diseases?.map((disease: any, index: number) => (
                        <Box 
                          key={index}
                          bg={isDark ? "blue.900" : "blue.100"} 
                          p={4} 
                          borderRadius="md"
                          border="1px solid"
                          borderColor={isDark ? "blue.700" : "blue.300"}
                        >
                          <HStack justify="space-between" mb={2}>
                            <Text fontWeight="bold" color={isDark ? "blue.200" : "blue.800"}>
                              {disease.name}
                            </Text>
                            <Badge colorScheme="blue" fontSize="sm">
                              {Math.round(disease.confidence * 100)}% confidence
                            </Badge>
                          </HStack>
                          <Text fontSize="sm" color={isDark ? "blue.300" : "blue.700"}>
                            {disease.description}
                          </Text>
                        </Box>
                      ))}
                    </VStack>
                  </Box>
                )}

                {/* ML API Results */}
                {triageData?.mlResults && (
                  <Box>
                    {/* Final AI Diagnosis only */}
                    <Box mb={4}>
                      <Heading size="sm" mb={2} color={isDark ? "purple.200" : "purple.800"}>
                        🎯 Final AI Diagnosis
                      </Heading>
                      <Box 
                        bg={isDark ? "purple.900" : "purple.100"} 
                        p={4} 
                        borderRadius="md"
                        border="1px solid"
                        borderColor={isDark ? "purple.700" : "purple.300"}
                      >
                        <HStack justify="space-between" mb={2}>
                          <Text fontWeight="bold" fontSize="lg" color={isDark ? "purple.200" : "purple.800"}>
                            {triageData.mlResults.fusion.finalDiagnosis}
                          </Text>
                        </HStack>
                        {/* Source/policy intentionally hidden as requested */}
                      </Box>
                    </Box>
                    {/* ML1/ML2 sections removed as requested */}
                  </Box>
                )}

                {/* Possible Medical Conditions */}
                <Box>
                  <Heading size="md" mb={3} display="flex" alignItems="center" gap={2}>
                    <FaExclamationTriangle color="orange" />
                    Possible Medical Conditions
                  </Heading>
                  <VStack spacing={2} align="stretch">
                    {triageData.possibleConditions.map((condition: string, index: number) => (
                      <Box 
                        key={index}
                        bg={isDark ? "orange.900" : "orange.100"} 
                        p={3} 
                        borderRadius="md"
                        border="1px solid"
                        borderColor={isDark ? "orange.700" : "orange.300"}
                      >
                        <Text fontWeight="semibold" color={isDark ? "orange.200" : "orange.800"}>
                          {condition}
                        </Text>
                      </Box>
                    ))}
                  </VStack>
                </Box>

                <Box h="1px" bg={isDark ? "gray.600" : "gray.300"} />

                {/* AI Recommendations */}
                {diseasePrediction?.recommendations && (
                  <Box>
                    <Heading size="md" mb={3} display="flex" alignItems="center" gap={2}>
                      <FaCheckCircle color="purple" />
                      AI Recommendations
                    </Heading>
                    <VStack spacing={3} align="stretch">
                      {diseasePrediction.recommendations.map((recommendation: string, index: number) => (
                        <Box 
                          key={index}
                          bg={isDark ? "purple.900" : "purple.100"} 
                          p={4} 
                          borderRadius="md"
                          border="1px solid"
                          borderColor={isDark ? "purple.700" : "purple.300"}
                        >
                          <Text {...fontSizeStyles[fontSize as keyof typeof fontSizeStyles]}>
                            {recommendation}
                          </Text>
                        </Box>
                      ))}
                    </VStack>
                  </Box>
                )}

                {/* Next Steps */}
                <Box>
                  <Heading size="md" mb={3} display="flex" alignItems="center" gap={2}>
                    <FaCheckCircle color="green" />
                    Recommended Next Steps
                  </Heading>
                  <VStack spacing={3} align="stretch">
                    {triageData.nextSteps.map((step: string, index: number) => (
                      <Box 
                        key={index}
                        bg={isDark ? "green.900" : "green.100"} 
                        p={4} 
                        borderRadius="md"
                        border="1px solid"
                        borderColor={isDark ? "green.700" : "green.300"}
                      >
                        <Text {...fontSizeStyles[fontSize as keyof typeof fontSizeStyles]}>
                          {step}
                        </Text>
                      </Box>
                    ))}
                  </VStack>
                </Box>

                <Box h="1px" bg={isDark ? "gray.600" : "gray.300"} />

                {/* Timestamp and Disclaimer */}
                <Box textAlign="center" color={isDark ? "gray.400" : "gray.600"}>
                  <Text fontSize="sm">
                    Assessment generated on: {triageData.timestamp}
                  </Text>
                  <Text fontSize="xs" mt={2} fontStyle="italic">
                    ⚠️ This is a preliminary assessment. Always consult with a qualified healthcare professional for proper medical diagnosis and treatment.
                  </Text>
                </Box>

                {/* Action Buttons */}
                <HStack spacing={4} justify="center" mt={6}>
                  <Button 
                    size="lg" 
                    colorScheme="blue" 
                    onClick={() => {
                      setShowTriageModal(false);
                      speakText("Triage summary closed");
                    }}
                    _focus={{
                      boxShadow: "0 0 0 2px rgba(66, 153, 225, 0.6)",
                      outline: "none"
                    }}
                  >
                    Close Summary
                  </Button>
                  {triageData.severity.level >= 4 && (
                    <Button 
                      size="lg" 
                      colorScheme="red" 
                      onClick={() => {
                        speakText("Emergency contact information displayed");
                        alert("Emergency Services: 000\nAmbulance: 000\nPolice: 000\nFire: 000");
                      }}
                      _focus={{
                        boxShadow: "0 0 0 2px rgba(66, 153, 225, 0.6)",
                        outline: "none"
                      }}
                    >
                      🚨 Emergency Contacts
                    </Button>
                  )}
                </HStack>
              </VStack>
            )}
          </Box>
          </Box>
        </Box>
      )}

      {/* Feedback Modal */}
      {showFeedbackModal && (
        <Box
          position="fixed"
          top={0}
          left={0}
          right={0}
          bottom={0}
          zIndex={1000}
          display="flex"
          alignItems="center"
          justifyContent="center"
          p={4}
        >
          {/* Overlay */}
          <Box 
            position="absolute" 
            top={0} 
            left={0} 
            right={0} 
            bottom={0} 
            bg="rgba(0, 0, 0, 0.6)"
            onClick={() => setShowFeedbackModal(false)}
          />
          
          {/* Modal Content */}
          <Box 
            maxW="2xl"
            maxH="90vh" 
            overflowY="auto"
            bg={isDark ? "#1a202c" : "#ffffff"}
            color={isDark ? "#ffffff" : "#000000"}
            borderRadius="md"
            shadow="2xl"
            position="relative"
            zIndex={1001}
            w="full"
            border="1px solid"
            borderColor={isDark ? "#2d3748" : "#e2e8f0"}
          >
            <Box 
              fontSize="2xl" 
              fontWeight="bold" 
              textAlign="center"
              bg="#319795"
              color="white"
              position="relative"
              p={6}
              borderTopRadius="md"
            >
              <FaComments style={{ display: "inline", marginRight: "8px" }} />
              Feedback & Contribution
              <IconButton
                aria-label="Close feedback modal"
                icon={<FaTimes />}
                size="lg"
                color="white"
                variant="ghost"
                position="absolute"
                right={4}
                top="50%"
                transform="translateY(-50%)"
                onClick={() => setShowFeedbackModal(false)}
                _hover={{ bg: "whiteAlpha.200" }}
                _focus={{
                  boxShadow: "0 0 0 2px rgba(255, 255, 255, 0.6)",
                  outline: "none"
                }}
              />
            </Box>
            
            <Box p={8}>
              {!feedbackSubmitted ? (
                <VStack spacing={6} align="stretch">
                  {/* Feedback Form */}
                  <Box>
                    <Heading size="md" mb={4} display="flex" alignItems="center" gap={2}>
                      <FaComments />
                      Share Your Feedback
                    </Heading>
                    
                    <VStack spacing={4} align="stretch">
                      <Box>
                        <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                          Feedback Type
                        </Text>
                        <Box position="relative" data-dropdown>
                          <Input
                            value={feedbackType === "general" ? "General Feedback" : 
                                   feedbackType === "bug" ? "Bug Report" : "Feature Request"}
                            readOnly
                            bg={isDark ? "gray.700" : "gray.100"}
                            borderColor={isDark ? "gray.600" : "gray.300"}
                            cursor="pointer"
                            onClick={() => setShowDropdown(!showDropdown)}
                            _focus={{ outline: "none" }}
                          />
                          
                          {/* Dropdown Arrow */}
                          <Box
                            position="absolute"
                            right="12px"
                            top="50%"
                            transform="translateY(-50%)"
                            pointerEvents="none"
                            fontSize="sm"
                            color={isDark ? "gray.400" : "gray.600"}
                          >
                            {showDropdown ? "▲" : "▼"}
                          </Box>
                          
                          {/* Dropdown Options */}
                          {showDropdown && (
                            <Box
                              position="absolute"
                              top="100%"
                              left={0}
                              right={0}
                              zIndex={1002}
                              bg={isDark ? "#2d3748" : "#ffffff"}
                              border="1px solid"
                              borderColor={isDark ? "#4a5568" : "#e2e8f0"}
                              borderRadius="md"
                              shadow="lg"
                              mt={1}
                            >
                              <Box
                                p={2}
                                cursor="pointer"
                                bg={feedbackType === "general" ? (isDark ? "#4a5568" : "#f7fafc") : "transparent"}
                                _hover={{ bg: isDark ? "#4a5568" : "#f7fafc" }}
                                onClick={() => {
                                  setFeedbackType("general");
                                  setShowDropdown(false);
                                }}
                                borderBottom="1px solid"
                                borderBottomColor={isDark ? "#4a5568" : "#e2e8f0"}
                              >
                                <Text color={isDark ? "#ffffff" : "#000000"} fontSize="sm">
                                  General Feedback
                                </Text>
                              </Box>
                              <Box
                                p={2}
                                cursor="pointer"
                                bg={feedbackType === "bug" ? (isDark ? "#4a5568" : "#f7fafc") : "transparent"}
                                _hover={{ bg: isDark ? "#4a5568" : "#f7fafc" }}
                                onClick={() => {
                                  setFeedbackType("bug");
                                  setShowDropdown(false);
                                }}
                                borderBottom="1px solid"
                                borderBottomColor={isDark ? "#4a5568" : "#e2e8f0"}
                              >
                                <Text color={isDark ? "#ffffff" : "#000000"} fontSize="sm">
                                  Bug Report
                                </Text>
                              </Box>
                              <Box
                                p={2}
                                cursor="pointer"
                                bg={feedbackType === "feature" ? (isDark ? "#4a5568" : "#f7fafc") : "transparent"}
                                _hover={{ bg: isDark ? "#4a5568" : "#f7fafc" }}
                                onClick={() => {
                                  setFeedbackType("feature");
                                  setShowDropdown(false);
                                }}
                              >
                                <Text color={isDark ? "#ffffff" : "#000000"} fontSize="sm">
                                  Feature Request
                                </Text>
                              </Box>
                            </Box>
                          )}
                        </Box>
                      </Box>
                      
                      <Box>
                        <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                          Your Feedback *
                        </Text>
                        <Input
                          as="textarea"
                          value={feedbackText}
                          onChange={(e) => setFeedbackText(e.target.value)}
                          placeholder="Tell us what you think! Share your experience, report issues, or suggest improvements..."
                          bg={isDark ? "gray.700" : "gray.100"}
                          borderColor={isDark ? "gray.600" : "gray.300"}
                          _placeholder={{ color: isDark ? "whiteAlpha.700" : "gray.600" }}
                          minH="120px"
                          resize="vertical"
                          style={{ 
                            height: "120px",
                            resize: "vertical",
                            overflow: "auto"
                          }}
                        />
                      </Box>
                      
                      <Button
                        onClick={handleFeedbackSubmit}
                        colorScheme="teal"
                        size="lg"
                        isDisabled={!feedbackText.trim()}
                        _focus={{
                          boxShadow: "0 0 0 2px rgba(66, 153, 225, 0.6)",
                          outline: "none"
                        }}
                      >
                        Submit Feedback
                      </Button>
                    </VStack>
                  </Box>

                  <Box h="1px" bg={isDark ? "gray.600" : "gray.300"} />

                  {/* Contribution Section */}
                  <Box>
                    <Heading size="md" mb={4} display="flex" alignItems="center" gap={2}>
                      <FaHeart color="red" />
                      Contribute to SwinSACA
                    </Heading>
                    
                    <VStack spacing={4} align="stretch">
                      <Text color={isDark ? "gray.300" : "gray.600"}>
                        Help us make SwinSACA better for everyone! There are many ways you can contribute:
                      </Text>
                      
                      <VStack spacing={3} align="stretch">
                        <Box 
                          bg={isDark ? "blue.900" : "blue.100"} 
                          p={4} 
                          borderRadius="md"
                          border="1px solid"
                          borderColor={isDark ? "blue.700" : "blue.300"}
                        >
                          <HStack spacing={3}>
                            <FaLanguage size={24} color="#3182ce" />
                            <Box>
                              <Text fontWeight="semibold" color={isDark ? "blue.200" : "blue.800"}>
                                Translation & Localization
                              </Text>
                              <Text fontSize="sm" color={isDark ? "blue.300" : "blue.700"}>
                                Help translate SwinSACA into more languages, especially Indigenous languages
                              </Text>
                            </Box>
                          </HStack>
                        </Box>
                        
                        <Box 
                          bg={isDark ? "green.900" : "green.100"} 
                          p={4} 
                          borderRadius="md"
                          border="1px solid"
                          borderColor={isDark ? "green.700" : "green.300"}
                        >
                          <HStack spacing={3}>
                            <FaGithub size={24} color="#38a169" />
                            <Box>
                              <Text fontWeight="semibold" color={isDark ? "green.200" : "green.800"}>
                                Code & Development
                              </Text>
                              <Text fontSize="sm" color={isDark ? "green.300" : "green.700"}>
                                Contribute to the codebase, fix bugs, or add new features
                              </Text>
                            </Box>
                          </HStack>
                        </Box>
                        
                        <Box 
                          bg={isDark ? "purple.900" : "purple.100"} 
                          p={4} 
                          borderRadius="md"
                          border="1px solid"
                          borderColor={isDark ? "purple.700" : "purple.300"}
                        >
                          <HStack spacing={3}>
                            <FaComments size={24} color="#805ad5" />
                            <Box>
                              <Text fontWeight="semibold" color={isDark ? "purple.200" : "purple.800"}>
                                Testing & Feedback
                              </Text>
                              <Text fontSize="sm" color={isDark ? "purple.300" : "purple.700"}>
                                Test the application and provide detailed feedback
                              </Text>
                            </Box>
                          </HStack>
                        </Box>
                      </VStack>
                      
                      <HStack spacing={4} justify="center" mt={4}>
                        <Button
                          as="a"
                          href="https://github.com/your-org/swinsaca"
                          target="_blank"
                          rel="noopener noreferrer"
                          colorScheme="blue"
                          variant="outline"
                          leftIcon={<FaGithub />}
                          _focus={{
                            boxShadow: "0 0 0 2px rgba(66, 153, 225, 0.6)",
                            outline: "none"
                          }}
                        >
                          View on GitHub
                        </Button>
                        <Button
                          as="a"
                          href="mailto:contribute@swinsaca.org"
                          colorScheme="teal"
                          leftIcon={<FaHeart />}
                          _focus={{
                            boxShadow: "0 0 0 2px rgba(66, 153, 225, 0.6)",
                            outline: "none"
                          }}
                        >
                          Contact Us
                        </Button>
                      </HStack>
                    </VStack>
                  </Box>
                </VStack>
              ) : (
                <VStack spacing={6} align="center" py={8}>
                  <Box textAlign="center">
                    <FaCheckCircle size={64} color="#38a169" />
                    <Heading size="lg" mt={4} color="green.500">
                      Thank You!
                    </Heading>
                    <Text fontSize="lg" color={isDark ? "gray.300" : "gray.600"} mt={2}>
                      Your feedback has been submitted successfully.
                    </Text>
                    <Text fontSize="sm" color={isDark ? "gray.400" : "gray.500"} mt={2}>
                      We'll review it and get back to you if needed.
                    </Text>
                  </Box>
                </VStack>
              )}
            </Box>
          </Box>
        </Box>
      )}
      
      {/* Progress Bar for Disease Prediction */}
      {renderProgressBar()}

      {/* Removed duplicate triage overlay that blocked scrolling of the main modal */}
    </Container>
  );
}
