// Removed Route types import to avoid missing file error
import { Box, Button, Container, Heading, IconButton, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { useEffect, useRef, useState } from "react";
import { speakOnHover } from "../utils/tts";
import { useNavigate } from "react-router";
import { motion } from "framer-motion";

export function meta() {
  return [
    { title: "Choose Language - SwinSACA" },
  ];
}

export default function Language() {
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(false);
  const headingRef = useRef<HTMLDivElement | null>(null);
  const englishRef = useRef<HTMLDivElement | null>(null);
  const arrernteRef = useRef<HTMLDivElement | null>(null);
  const BG_URL = "/images/arrerente.jpg";
  useEffect(() => {
    const c1 = speakOnHover(headingRef.current, "Language selection. Please choose your language.");
    const c2 = speakOnHover(englishRef.current, "English. Click to continue in English.");
    const c3 = speakOnHover(arrernteRef.current, "Arrernte. Click to continue in Arrernte.");
    return () => {
      c1 && c1();
      c2 && c2();
      c3 && c3();
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
  const handleSelect = (lang: string) => {
    navigate("/mode", { state: { lang } });
  };
  return (
    <Box
      minH="100dvh"
      bgImage={`url(${BG_URL})`}
      bgSize="cover"
      bgPosition="center"
      bgRepeat="no-repeat"
      position="relative"
      _before={{
        content: '""',
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        bg: "rgba(0, 0, 0, 0.4)",
        zIndex: 1,
      }}
    >
      <Container maxW="7xl" minH="100dvh" display="flex" alignItems="center" justifyContent="center" position="relative" zIndex={2} pb={24}>
        <Box position="fixed" top={4} right={4} zIndex={10}>
          <IconButton aria-label="Toggle color mode" onClick={() => setIsDark((v) => !v)} variant="ghost" fontSize="2xl">
            {isDark ? "☀️" : "🌙"}
          </IconButton>
        </Box>
        <Stack gap={10} align="center" textAlign="center" w="full" position="relative" zIndex={2}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <Heading 
              ref={headingRef as any} 
              size={{ base: "2xl", md: "4xl" }}
              lineHeight={1.1}
              color="white" 
              textShadow="0 2px 12px rgba(0,0,0,0.9), 0 0 30px rgba(0,0,0,0.6)"
              maxW="3xl" 
              mx="auto"
            >
              Language Selection
            </Heading>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Text 
              fontSize={{ base: "xl", md: "2xl" }} 
              color="whiteAlpha.900" 
              textShadow="0 2px 8px rgba(0,0,0,0.7)" 
              maxW="3xl" 
              mx="auto"
            >
              Please choose your preferred language
            </Text>
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
          >
            <SimpleGrid mt={{ base: 12, md: 16 }} columns={{ base: 1, md: 2 }} gap={{ base: 12, md: 16 }} w={{ base: "full", md: "2xl" }}>
              <motion.div
                whileHover={{ scale: 1.02, y: -4 }}
                whileTap={{ scale: 0.98 }}
                transition={{ duration: 0.2 }}
              >
                <Box
                  ref={englishRef as any}
                  role="button"
                  onClick={() => handleSelect("en")}
                  borderWidth="1px"
                  borderRadius="2xl"
                  p={8}
                  bg={isDark ? "whiteAlpha.200" : "whiteAlpha.800"}
                  backdropFilter="blur(2px)"
                  borderColor={isDark ? "whiteAlpha.400" : "teal.300"}
                  color={isDark ? "whiteAlpha.900" : "teal.900"}
                  shadow="lg"
                  _hover={{ shadow: "xl", transition: "all 180ms ease" }}
                >
                  <Heading size="xl" color={isDark ? "white" : "teal.800"}>English</Heading>
                  <Text mt={2} color={isDark ? "whiteAlpha.800" : "teal.700"}>Continue in English</Text>
                </Box>
              </motion.div>
              <motion.div
                whileHover={{ scale: 1.02, y: -4 }}
                whileTap={{ scale: 0.98 }}
                transition={{ duration: 0.2 }}
              >
                <Box
                  ref={arrernteRef as any}
                  role="button"
                  onClick={() => handleSelect("arrernte")}
                  borderWidth="1px"
                  borderRadius="2xl"
                  p={8}
                  bg={isDark ? "whiteAlpha.200" : "whiteAlpha.800"}
                  backdropFilter="blur(2px)"
                  borderColor={isDark ? "whiteAlpha.400" : "teal.300"}
                  color={isDark ? "whiteAlpha.900" : "teal.900"}
                  shadow="lg"
                  _hover={{ shadow: "xl", transition: "all 180ms ease" }}
                >
                  <Heading size="xl" color={isDark ? "white" : "teal.800"}>Arrernte</Heading>
                  <Text mt={2} color={isDark ? "whiteAlpha.800" : "teal.700"}>Mparntwe Arrernte language</Text>
                </Box>
              </motion.div>
            </SimpleGrid>
          </motion.div>
          <Box position="fixed" bottom={8} right={8}>
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.6 }}
            >
              <Button
                bg={isDark ? "teal.400" : "teal.600"}
                color={isDark ? "gray.900" : "white"}
                _hover={{ bg: isDark ? "teal.300" : "teal.700" }}
                onClick={() => navigate(-1)}
              >
                Back
              </Button>
            </motion.div>
          </Box>
        </Stack>
      </Container>
    </Box>
  );
}


