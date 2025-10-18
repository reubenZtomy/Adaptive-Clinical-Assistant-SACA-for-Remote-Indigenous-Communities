import { Box, Button, Container, Heading, IconButton, Stack, Text } from "@chakra-ui/react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, Link } from "react-router";
import { speakOnHover } from "../utils/tts";
import { AnimatePresence, motion } from "framer-motion";
import { loadArrernteDictionary, findByEnglish, playAudio } from "../utils/arrernte";

export function Welcome() {
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(false);
  const [user, setUser] = useState<any>(null);
  // Background image placed under /public/images/arrernte-bg.jpg
  // You can replace with any culturally appropriate image for Eastern/Central Arrernte (Mparntwe – Alice Springs)
  const BG_URL = "/images/arrerente.jpg";
  const headingRef = useRef<HTMLDivElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const taglineRef = useRef<HTMLParagraphElement | null>(null);
  const dictRef = useRef<any[]>([]);
  const [btnIndex, setBtnIndex] = useState(0);
  const [arrernteStart, setArrernteStart] = useState<{word: string; audio: string | null}>({ word: "Arrernte", audio: null });
  const btnIndexRef = useRef(0);
  const buttonTexts = [
    "Get Started",
    `Mpe!`,
  ];
  useEffect(() => {
    // Check if user is logged in
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      try {
        setUser(JSON.parse(storedUser));
      } catch (err) {
        localStorage.removeItem("user");
        localStorage.removeItem("access_token");
      }
    }

    // Dynamic TTS based on current text for heading/tagline and button
    const headingHover = () => {
      try {
        const audio = new Audio("/audio/welcome/Welcometitle.mp3");
        audio.play().catch(() => {});
      } catch {}
    };
    headingRef.current?.addEventListener("mouseenter", headingHover);
    const buttonHover = () => {
      try {
        const url = btnIndexRef.current === 1 ? "/audio/welcome/mpe.mp3" : "/audio/welcome/getstarted.mp3";
        const audio = new Audio(url);
        audio.play().catch(() => {});
      } catch {}
    };
    buttonRef.current?.addEventListener("mouseenter", buttonHover);
    const taglineHover = () => {
      try {
        const audio = new Audio("/audio/welcome/Welcomemessage.mp3");
        audio.play().catch(() => {});
      } catch {}
    };
    taglineRef.current?.addEventListener("mouseenter", taglineHover);
    loadArrernteDictionary().then((d) => {
      dictRef.current = d;
      const keys = ["start", "begin", "go", "come"];
      let found: any;
      for (const k of keys) {
        const f = findByEnglish(d as any, k);
        if (f) { found = f; break; }
      }
      if (!found) {
        found = (d as any[]).find(e => (e.english_meaning||"").toLowerCase().startsWith("come"))
             || (d as any[]).find(e => (e.arrernte_word||"").toLowerCase() === "apetyeme");
      }
      if (found) setArrernteStart({ word: found.arrernte_word, audio: found.audio_url || null });
    });
    const id = window.setInterval(() => setBtnIndex((i) => (i + 1) % buttonTexts.length), 4000);
    return () => {
      headingRef.current?.removeEventListener("mouseenter", headingHover);
      buttonRef.current?.removeEventListener("mouseenter", buttonHover);
      taglineRef.current?.removeEventListener("mouseenter", taglineHover);
      window.clearInterval(id);
    };
  }, []);

  useEffect(() => {
    try {
      const root = document.documentElement as HTMLElement;
      root.style.setProperty("--app-bg", isDark ? "#0f172a" : "#f9fafb");
      root.style.setProperty("--app-fg", isDark ? "#f8fafc" : "#1f2937");
      document.body.style.backgroundColor = getComputedStyle(root).getPropertyValue("--app-bg");
      document.body.style.color = getComputedStyle(root).getPropertyValue("--app-fg");
    } catch {}
  }, [isDark]);

  useEffect(() => {
    btnIndexRef.current = btnIndex;
  }, [btnIndex]);
  return (
    <Box position="relative" minH="100dvh">
      {/* Background image layer */}
      <Box
        position="fixed"
        top={0}
        left={0}
        right={0}
        bottom={0}
        // Layered backgrounds: photo on top, soft gradient fallback beneath
        bgImage={`url(${BG_URL}), linear-gradient(180deg, #e6f1ed 0%, #f3f7f9 100%)`}
        bgSize="cover"
        bgPos="center"
        bgRepeat="no-repeat"
        zIndex={0}
      />
      {/* Readability overlay (adjusts with light/dark) */}
      <Box
        position="fixed"
        top={0}
        left={0}
        right={0}
        bottom={0}
        bg={isDark ? "blackAlpha.400" : "blackAlpha.300"}
        zIndex={1}
      />

      <Container maxW="7xl" minH="100dvh" display="flex" alignItems="center" justifyContent="center" position="relative" zIndex={2}>
      <Box position="fixed" top={4} right={4}>
          <IconButton aria-label="Toggle color mode" onClick={() => setIsDark((v) => !v)} variant="ghost" fontSize="2xl">
          {isDark ? "☀️" : "🌙"}
        </IconButton>
      </Box>
      <Stack gap={12} align="center" textAlign="center" w="full" px={4}>
        <Box position="relative" minH={{ base: "auto", md: "unset" }}>
          <AnimatePresence mode="wait">
            <motion.div key={`heading-${btnIndex}`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.35 }}>
              <Heading
                ref={headingRef as any}
                size={{ base: "2xl", md: "4xl" }}
                lineHeight={1.1}
                color="white"
                textShadow="0 2px 12px rgba(0,0,0,0.9), 0 0 30px rgba(0,0,0,0.6)"
              >
                {btnIndex === 0 ? "Welcome to SwinSACA" : "Akangkeme SwinSACA"}
              </Heading>
            </motion.div>
          </AnimatePresence>
        </Box>
        <Box position="relative">
          <AnimatePresence mode="wait">
            <motion.div key={`tag-${btnIndex}`} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.35 }}>
              <Text
                ref={taglineRef as any}
                fontSize={{ base: "xl", md: "2xl" }}
                color="whiteAlpha.900"
                textShadow="0 2px 8px rgba(0,0,0,0.7)"
                maxW="3xl"
              >
                {btnIndex === 0
                  ? "AI-guided medical triage to help you describe symptoms and get the right care, fast."
                  : "AI-guided akaltye akngakeme to help you angkeme symptoms and get the right care, fast."}
              </Text>
            </motion.div>
          </AnimatePresence>
        </Box>
        {/* Cards removed as requested */}
        <Box mt={{ base: 6, md: 10 }}>
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5, duration: 0.5 }}>
            <Button
              ref={buttonRef}
              size="lg"
              bg={isDark ? "teal.400" : "teal.600"}
              color={isDark ? "gray.900" : "white"}
              _hover={{ bg: isDark ? "teal.300" : "teal.700" }}
              onClick={() => navigate("/language")}
            >
              <motion.span key={btnIndex} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                {buttonTexts[btnIndex]}
              </motion.span>
            </Button>
          </motion.div>
        </Box>

        {/* Optional Login Prompt - Only show if user is not logged in */}
        {!user && (
          <Box mt={8}>
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8, duration: 0.5 }}>
              <Text fontSize="sm" color="whiteAlpha.900" textShadow="0 1px 6px rgba(0,0,0,0.7)" mb={3}>
                Want to save your progress and access personalized features?
              </Text>
              <Stack direction="row" gap={3} justify="center">
                <Link to="/login">
                  <Button
                    variant="outline"
                    size="sm"
                    color="white"
                    borderColor="whiteAlpha.800"
                    _hover={{ bg: "whiteAlpha.200", borderColor: "whiteAlpha.900" }}
                    _active={{ bg: "whiteAlpha.300" }}
                  >
                    Sign In
                  </Button>
                </Link>
                <Link to="/register">
                  <Button
                    variant="solid"
                    size="sm"
                    bg="teal.500"
                    color="white"
                    _hover={{ bg: "teal.600" }}
                    _active={{ bg: "teal.700" }}
                  >
                    Create Account
                  </Button>
                </Link>
              </Stack>
            </motion.div>
          </Box>
        )}
      </Stack>
      </Container>
    </Box>
  );
}
