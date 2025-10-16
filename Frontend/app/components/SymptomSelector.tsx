import { Box, Button, Container, Flex, Heading, IconButton, SimpleGrid, Stack, Text, VStack, HStack, Badge, Progress } from "@chakra-ui/react";
import { useState, useRef, useEffect } from "react";
import { 
  FaHeart, FaBrain, FaEye, FaDeaf, FaTooth, FaHandPaper, FaShoePrints, 
  FaHeartbeat, FaBone, FaUserAlt, FaUserInjured, FaStethoscope,
  FaArrowLeft, FaArrowRight, FaCheck, FaTimes
} from "react-icons/fa";
import { speakText } from "../utils/tts";

export interface SymptomData {
  bodyPart: string;
  condition: string;
  intensity: number;
  duration: string;
}

interface SymptomSelectorProps {
  isDark: boolean;
  onComplete: (symptoms: SymptomData[]) => void;
  onBack: () => void;
}

const bodyParts = [
  { id: "head", name: "Head", icon: FaUserAlt, description: "Head and brain" },
  { id: "eyes", name: "Eyes", icon: FaEye, description: "Vision and eye problems" },
  { id: "ears", name: "Ears", icon: FaDeaf, description: "Hearing and ear issues" },
  { id: "mouth", name: "Mouth", icon: FaTooth, description: "Teeth and oral health" },
  { id: "chest", name: "Chest", icon: FaHeartbeat, description: "Heart and lungs" },
  { id: "stomach", name: "Stomach", icon: FaStethoscope, description: "Digestive system" },
  { id: "arms", name: "Arms", icon: FaHandPaper, description: "Arms and hands" },
  { id: "legs", name: "Legs", icon: FaShoePrints, description: "Legs and feet" },
  { id: "back", name: "Back", icon: FaBone, description: "Spine and back" },
  { id: "general", name: "General", icon: FaUserInjured, description: "Overall feeling" }
];

const conditions = {
  head: [
    { id: "headache", name: "Headache", description: "Pain in the head" },
    { id: "dizziness", name: "Dizziness", description: "Feeling lightheaded" },
    { id: "confusion", name: "Confusion", description: "Mental disorientation" },
    { id: "fever", name: "Fever", description: "High body temperature" }
  ],
  eyes: [
    { id: "blurry", name: "Blurry Vision", description: "Difficulty seeing clearly" },
    { id: "pain", name: "Eye Pain", description: "Pain in the eyes" },
    { id: "dry", name: "Dry Eyes", description: "Eyes feel dry" },
    { id: "red", name: "Red Eyes", description: "Eyes appear red" }
  ],
  ears: [
    { id: "pain", name: "Ear Pain", description: "Pain in the ears" },
    { id: "ringing", name: "Ringing", description: "Hearing ringing sounds" },
    { id: "hearing", name: "Hearing Loss", description: "Difficulty hearing" },
    { id: "pressure", name: "Pressure", description: "Feeling pressure in ears" }
  ],
  mouth: [
    { id: "toothache", name: "Toothache", description: "Pain in teeth" },
    { id: "sore", name: "Sore Throat", description: "Pain when swallowing" },
    { id: "dry", name: "Dry Mouth", description: "Mouth feels dry" },
    { id: "taste", name: "Taste Loss", description: "Can't taste properly" }
  ],
  chest: [
    { id: "chest_pain", name: "Chest Pain", description: "Pain in chest area" },
    { id: "breathing", name: "Breathing Issues", description: "Difficulty breathing" },
    { id: "cough", name: "Cough", description: "Persistent coughing" },
    { id: "heartbeat", name: "Irregular Heartbeat", description: "Heart rhythm problems" }
  ],
  stomach: [
    { id: "stomach_pain", name: "Stomach Pain", description: "Pain in stomach" },
    { id: "nausea", name: "Nausea", description: "Feeling sick" },
    { id: "diarrhea", name: "Diarrhea", description: "Loose bowel movements" },
    { id: "constipation", name: "Constipation", description: "Difficulty with bowel movements" }
  ],
  arms: [
    { id: "pain", name: "Arm Pain", description: "Pain in arms or hands" },
    { id: "numbness", name: "Numbness", description: "Loss of feeling" },
    { id: "weakness", name: "Weakness", description: "Reduced strength" },
    { id: "swelling", name: "Swelling", description: "Arms appear swollen" }
  ],
  legs: [
    { id: "pain", name: "Leg Pain", description: "Pain in legs or feet" },
    { id: "numbness", name: "Numbness", description: "Loss of feeling" },
    { id: "weakness", name: "Weakness", description: "Reduced strength" },
    { id: "swelling", name: "Swelling", description: "Legs appear swollen" }
  ],
  back: [
    { id: "back_pain", name: "Back Pain", description: "Pain in back" },
    { id: "stiffness", name: "Stiffness", description: "Back feels stiff" },
    { id: "spasm", name: "Muscle Spasm", description: "Involuntary muscle contractions" },
    { id: "limited", name: "Limited Movement", description: "Can't move freely" }
  ],
  general: [
    { id: "fatigue", name: "Fatigue", description: "Feeling very tired" },
    { id: "weakness", name: "Weakness", description: "General body weakness" },
    { id: "fever", name: "Fever", description: "High body temperature" },
    { id: "chills", name: "Chills", description: "Feeling cold and shivering" }
  ]
};

const durationRanges = [
  { id: "today", name: "Today", description: "Started today" },
  { id: "1-2", name: "1-2 days", description: "Started 1-2 days ago" },
  { id: "3-7", name: "3-7 days", description: "Started 3-7 days ago" },
  { id: "1-2weeks", name: "1-2 weeks", description: "Started 1-2 weeks ago" },
  { id: "2-4weeks", name: "2-4 weeks", description: "Started 2-4 weeks ago" },
  { id: "1month+", name: "1+ months", description: "Started over a month ago" }
];

export default function SymptomSelector({ isDark, onComplete, onBack }: SymptomSelectorProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedBodyPart, setSelectedBodyPart] = useState<string>("");
  const [selectedCondition, setSelectedCondition] = useState<string>("");
  const [intensity, setIntensity] = useState(5);
  const [selectedDuration, setSelectedDuration] = useState<string>("");
  const [symptoms, setSymptoms] = useState<SymptomData[]>([]);
  const [audioLoaded, setAudioLoaded] = useState(false);
  
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);
  const currentTTSRef = useRef<SpeechSynthesisUtterance | null>(null);
  const hoverTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isPlayingRef = useRef<boolean>(false);
  const currentHoverIdRef = useRef<number>(0);

  const steps = [
    { title: "Select Body Part", description: "Choose the part of your body that's affected" },
    { title: "Select Condition", description: "What type of problem are you experiencing?" },
    { title: "Rate Intensity", description: "How severe is this symptom? (1 = mild, 10 = severe)" },
    { title: "Duration", description: "How long have you had this symptom?" },
    { title: "Review", description: "Review your symptoms and add more if needed" }
  ];

  // Audio management functions (similar to mode.tsx)
  const stopCurrentAudio = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
      hoverTimeoutRef.current = null;
    }
    
    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.currentTime = 0;
      currentAudioRef.current = null;
    }
    
    window.speechSynthesis.cancel();
    currentTTSRef.current = null;
    isPlayingRef.current = false;
  };

  const playHoverAudio = (text: string) => {
    const hoverId = ++currentHoverIdRef.current;
    
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
    
    stopCurrentAudio();
    
    hoverTimeoutRef.current = setTimeout(() => {
      if (hoverId !== currentHoverIdRef.current || isPlayingRef.current) {
        return;
      }
      
      try {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.pitch = 1;
        utterance.volume = 0.8;
        
        currentTTSRef.current = utterance;
        isPlayingRef.current = true;
        
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
    }, 50);
  };

  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      const timer = setTimeout(() => {
        setAudioLoaded(true);
      }, 500);
      
      return () => clearTimeout(timer);
    }
  }, []);

  useEffect(() => {
    return () => {
      stopCurrentAudio();
      if (hoverTimeoutRef.current) {
        clearTimeout(hoverTimeoutRef.current);
      }
    };
  }, []);

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      // Complete the symptom selection
      onComplete(symptoms);
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    } else {
      onBack();
    }
  };

  const addSymptom = () => {
    if (selectedBodyPart && selectedCondition && selectedDuration) {
      const newSymptom: SymptomData = {
        bodyPart: selectedBodyPart,
        condition: selectedCondition,
        intensity: intensity,
        duration: selectedDuration
      };
      setSymptoms([...symptoms, newSymptom]);
      
      // Reset selections
      setSelectedBodyPart("");
      setSelectedCondition("");
      setSelectedDuration("");
      setIntensity(5);
      setCurrentStep(0);
    }
  };

  const removeSymptom = (index: number) => {
    setSymptoms(symptoms.filter((_, i) => i !== index));
  };

  const renderBodyPartSelection = () => (
    <SimpleGrid columns={{ base: 2, md: 3, lg: 5 }} gap={4} w="full">
      {bodyParts.map((part) => {
        const IconComponent = part.icon;
        return (
          <Box
            key={part.id}
            role="button"
            onClick={() => setSelectedBodyPart(part.id)}
            onMouseEnter={() => audioLoaded && playHoverAudio(`${part.name} - ${part.description}`)}
            onMouseLeave={() => stopCurrentAudio()}
            borderWidth="2px"
            borderRadius="xl"
            p={4}
            bg={selectedBodyPart === part.id ? (isDark ? "teal.800" : "teal.100") : (isDark ? "gray.800" : "white")}
            borderColor={selectedBodyPart === part.id ? "teal.500" : (isDark ? "gray.600" : "gray.200")}
            color={selectedBodyPart === part.id ? "teal.100" : (isDark ? "gray.100" : "gray.700")}
            _hover={{ shadow: "md", bg: selectedBodyPart === part.id ? (isDark ? "teal.700" : "teal.200") : (isDark ? "gray.700" : "gray.50") }}
            cursor="pointer"
            textAlign="center"
          >
            <VStack gap={2}>
              <IconComponent size={32} />
              <Text fontSize="sm" fontWeight="medium">{part.name}</Text>
            </VStack>
          </Box>
        );
      })}
    </SimpleGrid>
  );

  const renderConditionSelection = () => {
    const availableConditions = conditions[selectedBodyPart as keyof typeof conditions] || [];
    
    return (
      <SimpleGrid columns={{ base: 1, md: 2 }} gap={4} w="full">
        {availableConditions.map((condition) => (
          <Box
            key={condition.id}
            role="button"
            onClick={() => setSelectedCondition(condition.id)}
            onMouseEnter={() => audioLoaded && playHoverAudio(`${condition.name} - ${condition.description}`)}
            onMouseLeave={() => stopCurrentAudio()}
            borderWidth="2px"
            borderRadius="lg"
            p={4}
            bg={selectedCondition === condition.id ? (isDark ? "teal.800" : "teal.100") : (isDark ? "gray.800" : "white")}
            borderColor={selectedCondition === condition.id ? "teal.500" : (isDark ? "gray.600" : "gray.200")}
            color={selectedCondition === condition.id ? "teal.100" : (isDark ? "gray.100" : "gray.700")}
            _hover={{ shadow: "md", bg: selectedCondition === condition.id ? (isDark ? "teal.700" : "teal.200") : (isDark ? "gray.700" : "gray.50") }}
            cursor="pointer"
          >
            <VStack gap={2} align="start">
              <Text fontSize="lg" fontWeight="semibold">{condition.name}</Text>
              <Text fontSize="sm" color={isDark ? "gray.300" : "gray.600"}>{condition.description}</Text>
            </VStack>
          </Box>
        ))}
      </SimpleGrid>
    );
  };

  const renderIntensityScale = () => (
    <VStack gap={6} w="full" maxW="520px">
      <Text fontSize="lg" textAlign="center">
        Current intensity: <Badge colorScheme="red" fontSize="lg" px={3} py={1}>{intensity}</Badge>
      </Text>
      
      <VStack w="full" gap={3}>
        <Flex wrap="wrap" gap={2} justify="center">
          {Array.from({ length: 10 }).map((_, idx) => {
            const value = idx + 1;
            const isSelected = intensity === value;
            const color = value <= 3 ? (isDark ? "green.300" : "green.600") : value <= 7 ? (isDark ? "yellow.300" : "yellow.600") : (isDark ? "red.300" : "red.600");
            const bg = isSelected ? (isDark ? "whiteAlpha.200" : "blackAlpha.100") : "transparent";
            return (
              <Button
                key={value}
                size="sm"
                onClick={() => setIntensity(value)}
                variant="outline"
                borderColor={color}
                color={color}
                bg={bg}
                _hover={{ bg: isDark ? "whiteAlpha.300" : "blackAlpha.200" }}
                minW="40px"
              >
                {value}
              </Button>
            );
          })}
        </Flex>
        <HStack gap={4} fontSize="sm" color={isDark ? "gray.300" : "gray.600"}>
          <Text>Mild</Text>
          <Text>Moderate</Text>
          <Text>Severe</Text>
        </HStack>
      </VStack>
    </VStack>
  );

  const renderDurationSelection = () => (
    <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={4} w="full">
      {durationRanges.map((duration) => (
        <Box
          key={duration.id}
          role="button"
          onClick={() => setSelectedDuration(duration.id)}
          onMouseEnter={() => audioLoaded && playHoverAudio(`${duration.name} - ${duration.description}`)}
          onMouseLeave={() => stopCurrentAudio()}
          borderWidth="2px"
          borderRadius="lg"
          p={4}
          bg={selectedDuration === duration.id ? (isDark ? "teal.800" : "teal.100") : (isDark ? "gray.800" : "white")}
          borderColor={selectedDuration === duration.id ? "teal.500" : (isDark ? "gray.600" : "gray.200")}
          color={selectedDuration === duration.id ? "teal.100" : (isDark ? "gray.100" : "gray.700")}
          _hover={{ shadow: "md", bg: selectedDuration === duration.id ? (isDark ? "teal.700" : "teal.200") : (isDark ? "gray.700" : "gray.50") }}
          cursor="pointer"
          textAlign="center"
        >
          <VStack gap={2}>
            <Text fontSize="lg" fontWeight="semibold">{duration.name}</Text>
            <Text fontSize="sm" color={isDark ? "gray.300" : "gray.600"}>{duration.description}</Text>
          </VStack>
        </Box>
      ))}
    </SimpleGrid>
  );

  const renderReview = () => (
    <VStack gap={6} w="full">
      {symptoms.length === 0 ? (
        <Text fontSize="lg" color={isDark ? "gray.300" : "gray.600"}>No symptoms added yet.</Text>
      ) : (
        <VStack gap={4} w="full">
          {symptoms.map((symptom, index) => {
            const bodyPart = bodyParts.find(p => p.id === symptom.bodyPart);
            const condition = conditions[symptom.bodyPart as keyof typeof conditions]?.find(c => c.id === symptom.condition);
            const duration = durationRanges.find(d => d.id === symptom.duration);
            
            return (
              <Box
                key={index}
                borderWidth="1px"
                borderRadius="lg"
                p={4}
                w="full"
                bg={isDark ? "gray.800" : "white"}
                borderColor={isDark ? "gray.600" : "gray.200"}
              >
                <Flex justify="space-between" align="start">
                  <VStack align="start" gap={2}>
                    <HStack gap={2}>
                      {bodyPart && <bodyPart.icon size={20} />}
                      <Text fontWeight="semibold">{bodyPart?.name} - {condition?.name}</Text>
                    </HStack>
                    <Text fontSize="sm" color={isDark ? "gray.300" : "gray.600"}>
                      Intensity: {symptom.intensity}/10 | Duration: {duration?.name}
                    </Text>
                  </VStack>
                  <IconButton
                    aria-label="Remove symptom"
                    icon={<FaTimes />}
                    size="sm"
                    variant="ghost"
                    colorScheme="red"
                    onClick={() => removeSymptom(index)}
                  />
                </Flex>
              </Box>
            );
          })}
        </VStack>
      )}
      
      {selectedBodyPart && selectedCondition && selectedDuration && (
        <Box
          borderWidth="2px"
          borderColor="teal.500"
          borderRadius="lg"
          p={4}
          w="full"
          bg={isDark ? "teal.900" : "teal.50"}
        >
          <VStack gap={2}>
            <Text fontWeight="semibold" color="teal.600">Ready to add:</Text>
            <Text>
              {bodyParts.find(p => p.id === selectedBodyPart)?.name} - 
              {conditions[selectedBodyPart as keyof typeof conditions]?.find(c => c.id === selectedCondition)?.name} 
              (Intensity: {intensity}/10, Duration: {durationRanges.find(d => d.id === selectedDuration)?.name})
            </Text>
            <Button
              colorScheme="teal"
              onClick={addSymptom}
              leftIcon={<FaCheck />}
            >
              Add This Symptom
            </Button>
          </VStack>
        </Box>
      )}
    </VStack>
  );

  const renderCurrentStep = () => {
    switch (currentStep) {
      case 0: return renderBodyPartSelection();
      case 1: return renderConditionSelection();
      case 2: return renderIntensityScale();
      case 3: return renderDurationSelection();
      case 4: return renderReview();
      default: return null;
    }
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0: return selectedBodyPart !== "";
      case 1: return selectedCondition !== "";
      case 2: return true; // Intensity always has a value
      case 3: return selectedDuration !== "";
      case 4: return symptoms.length > 0;
      default: return false;
    }
  };

  return (
    <Container maxW="6xl" py={8}>
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

      <VStack gap={8} align="center">
        {/* Progress indicator */}
        <Box w="full" maxW="600px">
          <Flex justify="space-between" mb={2}>
            {steps.map((step, index) => (
              <Text
                key={index}
                fontSize="sm"
                color={index <= currentStep ? "teal.600" : (isDark ? "gray.500" : "gray.400")}
                fontWeight={index === currentStep ? "semibold" : "normal"}
              >
                {step.title}
              </Text>
            ))}
          </Flex>
          <Progress
            value={(currentStep / (steps.length - 1)) * 100}
            colorScheme="teal"
            size="sm"
            borderRadius="full"
          />
        </Box>

        {/* Step content */}
        <VStack gap={6} w="full">
          <VStack gap={2} textAlign="center">
            <Heading size="lg">{steps[currentStep].title}</Heading>
            <Text color={isDark ? "gray.300" : "gray.600"}>{steps[currentStep].description}</Text>
          </VStack>

          {renderCurrentStep()}
        </VStack>

        {/* Navigation buttons */}
        <Flex gap={4} w="full" maxW="400px" justify="space-between">
          <Button
            leftIcon={<FaArrowLeft />}
            onClick={handleBack}
            variant="outline"
            colorScheme="teal"
          >
            {currentStep === 0 ? "Back to Chat" : "Previous"}
          </Button>
          
          <Button
            rightIcon={currentStep === steps.length - 1 ? <FaCheck /> : <FaArrowRight />}
            onClick={handleNext}
            colorScheme="teal"
            isDisabled={!canProceed()}
          >
            {currentStep === steps.length - 1 ? "Complete" : "Next"}
          </Button>
        </Flex>
      </VStack>
    </Container>
  );
}
