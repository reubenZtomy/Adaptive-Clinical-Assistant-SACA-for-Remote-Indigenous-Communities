import { Box, Button, Container, Heading, IconButton, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { useEffect, useState, useRef } from "react";
import { useLocation, useNavigate } from "react-router";
import { FaKeyboard, FaMicrophone, FaImages } from "react-icons/fa";

export function meta() {
  return [
    { title: "Choose Communication Mode - SwinSACA" },
  ];
}

export default function Mode() {
  const navigate = useNavigate();
  const location = useLocation();
  const lang = (location.state as any)?.lang ?? "en";
  const [isDark, setIsDark] = useState(false);
  const [audioLoaded, setAudioLoaded] = useState(false);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const currentTTSRef = useRef<SpeechSynthesisUtterance | null>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isPlayingRef = useRef<boolean>(false);
  const currentHoverIdRef = useRef<number>(0);

  // Audio management functions
  const stopCurrentAudio = () => {
    // Clear any pending hover timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    
    // Stop any currently playing audio
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current = null;
    }
    
    // Stop any currently playing TTS
    window.speechSynthesis.cancel();
    currentTTSRef.current = null;
    isPlayingRef.current = false;
  };

  const playHoverAudio = (text: string) => {
    // Generate unique ID for this hover event
    const hoverId = ++currentHoverIdRef.current;
    
    // Clear any existing timeout
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    
    // Stop current audio immediately
    stopCurrentAudio();
    
    // Add a small delay to prevent rapid-fire audio
    hoverTimeoutRef.current = setTimeout(() => {
      // Check if this is still the latest hover event
      if (hoverId !== currentHoverIdRef.current) {
        return; // This hover event is outdated, ignore it
      }
      
      // Prevent duplicate audio if already playing
      if (isPlayingRef.current) {
        return;
      }
      
      try {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.pitch = 1;
        utterance.volume = 0.8;
        
        currentTTSRef.current = utterance;
        isPlayingRef.current = true;
        
        // Clear reference when finished
        utterance.onstart = () => {
          isPlayingRef.current = true;
        };
        
        utterance.onend = () => {
          currentTTSRef.current = null;
          isPlayingRef.current = false;
        };
        
        utterance.onerror = () => {
          currentTTSRef.current = null;
          isPlayingRef.current = false;
        };
        
        window.speechSynthesis.speak(utterance);
      } catch (error) {
        console.warn('TTS error:', error);
        isPlayingRef.current = false;
      }
    }, 50); // Small delay to prevent rapid overlapping
  };

  useEffect(() => {
    try {
      const root = document.documentElement as HTMLElement;
      root.style.setProperty("--app-bg", isDark ? "#0f172a" : "#f9fafb");
      root.style.setProperty("--app-fg", isDark ? "#f8fafc" : "#1f2937");
      document.body.style.backgroundColor = getComputedStyle(root).getPropertyValue("--app-bg");
      document.body.style.color = getComputedStyle(root).getPropertyValue("--app-fg");
    } catch {}
  }, [isDark]);

  // Initialize audio system
  useEffect(() => {
    // Check if speech synthesis is available
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      // Small delay to ensure everything is loaded
      const timer = setTimeout(() => {
        setAudioLoaded(true);
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopCurrentAudio();
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  const handleMode = (mode: "text" | "voice" | "images") => {
    navigate("/chat", { state: { lang, mode } });
  };

  return (
    <Box minH="100dvh" display="flex" alignItems="center" justifyContent="center" px={4}>
      <Container maxW="7xl" position="relative" pb={24}>
        {/* Audio loading indicator */}
        <Box position="fixed" top={4} left={4} zIndex={10}>
          <Text 
            fontSize="sm" 
            color={isDark ? "gray.400" : "gray.600"}
            bg={isDark ? "gray.800" : "white"}
            px={3}
            py={1}
            borderRadius="md"
            borderWidth="1px"
            borderColor={isDark ? "gray.700" : "gray.200"}
            shadow="sm"
          >
            {audioLoaded ? "🔊 Audio ready - hover to hear" : "⏳ Loading audio..."}
          </Text>
        </Box>
        
        <Box position="fixed" top={4} right={4}>
          <IconButton aria-label="Toggle color mode" onClick={() => setIsDark((v) => !v)} variant="ghost" fontSize="2xl">
            {isDark ? "☀️" : "🌙"}
          </IconButton>
        </Box>
        <Stack gap={10} align="center" textAlign="center">
          <Heading size="2xl" color={isDark ? "gray.100" : undefined}>How would you like to communicate?</Heading>
          <Text fontSize={{ base: "xl", md: "2xl" }} color={isDark ? "gray.300" : "gray.600"}>Select a mode below</Text>
          <SimpleGrid mt={{ base: 12, md: 16 }} columns={{ base: 1, md: 3 }} gap={{ base: 10, md: 16 }} w="full">
            <Box 
              role="button" 
              onClick={() => handleMode("text")} 
              onMouseEnter={() => audioLoaded && playHoverAudio("Text mode - Type your messages")}
              onMouseLeave={() => stopCurrentAudio()}
              borderWidth="1px" 
              borderRadius="xl" 
              p={6} 
              bg={isDark ? "teal.900" : "teal.50"} 
              borderColor={isDark ? "teal.700" : "teal.400"} 
              color={isDark ? "teal.100" : "teal.800"} 
              _hover={{ shadow: "md", bg: isDark ? "teal.800" : "teal.100" }}
              cursor="pointer"
            >
              <Stack align="center" gap={3}>
                <FaKeyboard size={48} />
                <Heading size="xl">Text</Heading>
                <Text color={isDark ? "teal.200" : "teal.700"}>Type your messages</Text>
              </Stack>
            </Box>
            <Box 
              role="button" 
              onClick={() => handleMode("voice")} 
              onMouseEnter={() => audioLoaded && playHoverAudio("Voice mode - Speak with the assistant")}
              onMouseLeave={() => stopCurrentAudio()}
              borderWidth="1px" 
              borderRadius="xl" 
              p={6} 
              bg={isDark ? "teal.900" : "teal.50"} 
              borderColor={isDark ? "teal.700" : "teal.400"} 
              color={isDark ? "teal.100" : "teal.800"} 
              _hover={{ shadow: "md", bg: isDark ? "teal.800" : "teal.100" }}
              cursor="pointer"
            >
              <Stack align="center" gap={3}>
                <FaMicrophone size={48} />
                <Heading size="xl">Voice</Heading>
                <Text color={isDark ? "teal.200" : "teal.700"}>Speak with the assistant</Text>
              </Stack>
            </Box>
            <Box 
              role="button" 
              onClick={() => handleMode("images")} 
              onMouseEnter={() => audioLoaded && playHoverAudio("Images mode - Share helpful pictures")}
              onMouseLeave={() => stopCurrentAudio()}
              borderWidth="1px" 
              borderRadius="xl" 
              p={6} 
              bg={isDark ? "teal.900" : "teal.50"} 
              borderColor={isDark ? "teal.700" : "teal.400"} 
              color={isDark ? "teal.100" : "teal.800"} 
              _hover={{ shadow: "md", bg: isDark ? "teal.800" : "teal.100" }}
              cursor="pointer"
            >
              <Stack align="center" gap={3}>
                <FaImages size={48} />
                <Heading size="xl">Images</Heading>
                <Text color={isDark ? "teal.200" : "teal.700"}>Share helpful pictures</Text>
              </Stack>
            </Box>
          </SimpleGrid>
          <Box position="fixed" bottom={8} right={8}>
            <Button bg={isDark ? "teal.400" : "teal.600"} color={isDark ? "gray.900" : "white"} _hover={{ bg: isDark ? "teal.300" : "teal.700" }} onClick={() => navigate(-1)}>
              Back
            </Button>
          </Box>
        </Stack>
      </Container>
    </Box>
  );
}


