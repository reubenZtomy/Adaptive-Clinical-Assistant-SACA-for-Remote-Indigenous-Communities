import type { Route } from "../+types/language";
import { Box, Button, Container, Heading, IconButton, SimpleGrid, Stack, Text } from "@chakra-ui/react";
import { useEffect, useRef, useState } from "react";
import { speakOnHover } from "../utils/tts";
import { useNavigate } from "react-router";

export function meta({}: Route.MetaArgs) {
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
    <Container maxW="7xl" minH="100dvh" display="flex" alignItems="center" justifyContent="center" position="relative" pb={24}>
      <Box position="fixed" top={4} right={4}>
        <IconButton aria-label="Toggle color mode" onClick={() => setIsDark((v) => !v)} variant="ghost" fontSize="2xl">
          {isDark ? "☀️" : "🌙"}
        </IconButton>
      </Box>
      <Stack spacing={10} align="center" textAlign="center" w="full">
        <Heading ref={headingRef as any} size="2xl" color={isDark ? "gray.100" : undefined}>Language Selection</Heading>
        <Text fontSize={{ base: "xl", md: "2xl" }} color={isDark ? "gray.300" : "gray.600"}>Please choose your preferred language</Text>
        <SimpleGrid mt={{ base: 12, md: 16 }} columns={{ base: 1, md: 2 }} gap={{ base: 12, md: 16 }} w={{ base: "full", md: "2xl" }}>
          <Box
            ref={englishRef as any}
            role="button"
            onClick={() => handleSelect("en")}
            borderWidth="1px"
            borderRadius="xl"
            p={6}
            bg={isDark ? "teal.900" : "teal.50"}
            borderColor={isDark ? "teal.700" : "teal.400"}
            color={isDark ? "teal.100" : "teal.800"}
            _hover={{ shadow: "md", bg: isDark ? "teal.800" : "teal.100" }}
          >
            <Heading size="xl" color={isDark ? "teal.100" : "teal.800"}>English</Heading>
            <Text mt={2} color={isDark ? "teal.200" : "teal.700"}>Continue in English</Text>
          </Box>
          <Box
            ref={arrernteRef as any}
            role="button"
            onClick={() => handleSelect("arrernte")}
            borderWidth="1px"
            borderRadius="xl"
            p={6}
            bg={isDark ? "teal.900" : "teal.50"}
            borderColor={isDark ? "teal.700" : "teal.400"}
            color={isDark ? "teal.100" : "teal.800"}
            _hover={{ shadow: "md", bg: isDark ? "teal.800" : "teal.100" }}
          >
            <Heading size="xl" color={isDark ? "teal.100" : "teal.800"}>Arrernte</Heading>
            <Text mt={2} color={isDark ? "teal.200" : "teal.700"}>Mparntwe Arrernte language</Text>
          </Box>
        </SimpleGrid>
        <Box position="fixed" bottom={8} right={8}>
          <Button
            bg={isDark ? "teal.400" : "teal.600"}
            color={isDark ? "gray.900" : "white"}
            _hover={{ bg: isDark ? "teal.300" : "teal.700" }}
            onClick={() => navigate(-1)}
          >
            Back
          </Button>
        </Box>
      </Stack>
    </Container>
  );
}


