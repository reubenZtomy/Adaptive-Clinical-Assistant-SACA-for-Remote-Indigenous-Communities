import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  Box,
  Button,
  Container,
  Text,
  Heading,
  IconButton,
  Badge,
  Stack,
  Spinner,
  Center,
  useDisclosure,
  VStack,
  HStack
} from "@chakra-ui/react";
import { motion } from "framer-motion";

const API_BASE_URL = "http://localhost:5000/api";

interface Prediction {
  id: number;
  user_id: number;
  prediction_text: string;
  severity: string;
  language: string;
  mode: string;
  created_at: string;
  ml1_result?: any;
  ml2_result?: any;
  fused_result?: any;
}

export default function History() {
  const navigate = useNavigate();
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedPrediction, setSelectedPrediction] = useState<Prediction | null>(null);

  const isDark = false; // Light mode
  const bgColor = "white";
  const borderColor = "gray.200";

  // Check if user is logged in
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const user = localStorage.getItem('user');
    console.log('History page - Token:', token ? 'Present' : 'Missing');
    console.log('History page - User:', user ? 'Present' : 'Missing');
    
    if (!token) {
      console.log('No token found, redirecting to login');
      navigate('/login');
      return;
    }
    
    // Check if token is old format (contains integer) and clear it
    try {
      const tokenParts = token.split('.');
      if (tokenParts.length === 3) {
        const payload = JSON.parse(atob(tokenParts[1]));
        console.log('Token payload:', payload);
        if (typeof payload.sub === 'number') {
          console.log('Old token format detected, clearing and redirecting to login');
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          navigate('/login');
          return;
        }
      }
    } catch (e) {
      console.log('Error parsing token, clearing and redirecting to login');
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      navigate('/login');
      return;
    }
    
    fetchPredictions();
  }, [navigate]);

  const fetchPredictions = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('access_token');
      console.log('Token being sent:', token ? 'Present' : 'Missing');
      
      const response = await fetch(`${API_BASE_URL}/auth/predictions`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('access_token');
          navigate('/login');
          return;
        }
        const errorText = await response.text();
        console.error('API Error:', response.status, errorText);
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
      }

      const data = await response.json();
      setPredictions(data.predictions || []);
    } catch (err) {
      console.error('Error fetching predictions:', err);
      setError('Failed to load prediction history');
    } finally {
      setLoading(false);
    }
  };

  const deletePrediction = async (id: number) => {
    try {
      setDeletingId(id);
      const token = localStorage.getItem('access_token');
      
      const response = await fetch(`${API_BASE_URL}/auth/predictions/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Remove from local state
      setPredictions(prev => prev.filter(p => p.id !== id));
    } catch (err) {
      console.error('Error deleting prediction:', err);
      setError('Failed to delete prediction');
    } finally {
      setDeletingId(null);
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'mild': return 'green';
      case 'moderate': return 'yellow';
      case 'severe': return 'red';
      default: return 'gray';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const truncateText = (text: string, maxLength: number = 100) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const showPredictionDetails = (prediction: Prediction) => {
    setSelectedPrediction(prediction);
    onOpen();
  };

  if (loading) {
    return (
      <Center h="100vh">
        <VStack spacing={4}>
          <Spinner size="xl" color="teal.500" />
          <Text>Loading prediction history...</Text>
        </VStack>
      </Center>
    );
  }

  return (
    <Container maxW="7xl" py={8}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <VStack spacing={6} align="stretch">
          <Box textAlign="center">
            <Heading size="xl" mb={2}>Prediction History</Heading>
            <Text color="gray.600" fontSize="lg">
              View and manage your medical predictions
            </Text>
          </Box>

          {error && (
            <Box bg="red.50" border="1px solid" borderColor="red.200" borderRadius="md" p={4}>
              <Text color="red.600" fontWeight="medium">
                {error}
              </Text>
            </Box>
          )}

          {predictions.length === 0 && !loading ? (
            <Box textAlign="center" py={12}>
              <Text fontSize="lg" color="gray.500" mb={4}>
                No predictions found
              </Text>
              <Text color="gray.400">
                Your medical predictions will appear here after you make them.
              </Text>
            </Box>
          ) : predictions.length > 0 ? (
            <Box
              borderWidth="1px"
              borderRadius="lg"
              overflow="hidden"
              bg={bgColor}
              borderColor={borderColor}
            >
              <VStack spacing={4} align="stretch">
                {predictions.map((prediction) => (
                  <Box
                    key={prediction.id}
                    p={4}
                    border="1px solid"
                    borderColor={borderColor}
                    borderRadius="md"
                    bg={bgColor}
                    _hover={{ shadow: "md" }}
                  >
                    <VStack spacing={3} align="stretch">
                      <HStack justify="space-between" align="start">
                        <VStack align="start" spacing={1} flex={1}>
                          <Text fontSize="sm" color="gray.500">
                            {formatDate(prediction.created_at)}
                          </Text>
                          <Text
                            fontSize="sm"
                            cursor="pointer"
                            color="teal.500"
                            _hover={{ textDecoration: "underline" }}
                            onClick={() => showPredictionDetails(prediction)}
                            noOfLines={2}
                          >
                            {truncateText(prediction.prediction_text)}
                          </Text>
                        </VStack>
                        <HStack spacing={2}>
                          <Badge colorScheme={getSeverityColor(prediction.severity)}>
                            {prediction.severity}
                          </Badge>
                          <Badge colorScheme={prediction.language === 'english' ? 'blue' : 'purple'}>
                            {prediction.language}
                          </Badge>
                          <Badge colorScheme="gray">
                            {prediction.mode}
                          </Badge>
                        </HStack>
                      </HStack>
                      <HStack justify="flex-end" spacing={2}>
                        <IconButton
                          aria-label="View details"
                          icon={<Text>👁</Text>}
                          size="sm"
                          variant="ghost"
                          onClick={() => showPredictionDetails(prediction)}
                        />
                        <IconButton
                          aria-label="Delete prediction"
                          icon={<Text>🗑</Text>}
                          size="sm"
                          variant="ghost"
                          colorScheme="red"
                          isLoading={deletingId === prediction.id}
                          onClick={() => deletePrediction(prediction.id)}
                        />
                      </HStack>
                    </VStack>
                  </Box>
                ))}
              </VStack>
            </Box>
          ) : null}

          <HStack justify="center" spacing={4}>
            <Button
              colorScheme="teal"
              onClick={() => navigate('/chat')}
            >
              Back to Chat
            </Button>
            <Button
              variant="outline"
              onClick={fetchPredictions}
            >
              Refresh
            </Button>
          </HStack>
        </VStack>
      </motion.div>

      {/* Prediction Details Modal */}
      {isOpen && (
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
          {/* Backdrop */}
          <Box
            position="absolute"
            top={0}
            left={0}
            right={0}
            bottom={0}
            bg="blackAlpha.600"
            backdropFilter="blur(4px)"
            onClick={onClose}
          />
          
          {/* Modal Content */}
          <Box
            maxW="xl"
            maxH="90vh"
            overflowY="auto"
            bg="white"
            borderRadius="md"
            shadow="2xl"
            position="relative"
            zIndex={1001}
            w="full"
          >
            <Box p={4} borderBottom="1px solid" borderColor="gray.200">
              <HStack justify="space-between" align="center">
                <Text fontWeight="bold" fontSize="lg">Prediction Details</Text>
                <IconButton
                  aria-label="Close modal"
                  icon={<Text>✕</Text>}
                  size="sm"
                  variant="ghost"
                  onClick={onClose}
                />
              </HStack>
            </Box>
            <Box p={6}>
              {selectedPrediction && (
                <VStack spacing={4} align="stretch">
                  <Box>
                    <Text fontWeight="bold" mb={2}>Prediction Text:</Text>
                    <Text p={3} bg="gray.50" borderRadius="md" whiteSpace="pre-wrap">
                      {selectedPrediction.prediction_text}
                    </Text>
                  </Box>

                  <HStack spacing={4}>
                    <Box>
                      <Text fontWeight="bold" mb={1}>Severity:</Text>
                      <Badge colorScheme={getSeverityColor(selectedPrediction.severity)}>
                        {selectedPrediction.severity}
                      </Badge>
                    </Box>
                    <Box>
                      <Text fontWeight="bold" mb={1}>Language:</Text>
                      <Badge colorScheme={selectedPrediction.language === 'english' ? 'blue' : 'purple'}>
                        {selectedPrediction.language}
                      </Badge>
                    </Box>
                    <Box>
                      <Text fontWeight="bold" mb={1}>Mode:</Text>
                      <Badge colorScheme="gray">
                        {selectedPrediction.mode}
                      </Badge>
                    </Box>
                  </HStack>

                  <Box h="1px" bg="gray.200" w="100%" />

                  {selectedPrediction.fused_result && (
                    <Box>
                      <Text fontWeight="bold" mb={2}>ML Model Results:</Text>
                      <Box p={3} bg="gray.50" borderRadius="md">
                        <pre style={{ fontSize: '12px', overflow: 'auto' }}>
                          {JSON.stringify(selectedPrediction.fused_result, null, 2)}
                        </pre>
                      </Box>
                    </Box>
                  )}

                  <Text fontSize="sm" color="gray.500">
                    Created: {formatDate(selectedPrediction.created_at)}
                  </Text>
                </VStack>
              )}
            </Box>
            <Box p={4} borderTop="1px solid" borderColor="gray.200">
              <HStack justify="flex-end" spacing={3}>
                <Button variant="ghost" onClick={onClose}>
                  Close
                </Button>
                {selectedPrediction && (
                  <Button
                    colorScheme="red"
                    onClick={() => {
                      deletePrediction(selectedPrediction.id);
                      onClose();
                    }}
                    isLoading={deletingId === selectedPrediction.id}
                  >
                    Delete
                  </Button>
                )}
              </HStack>
            </Box>
          </Box>
        </Box>
      )}
    </Container>
  );
}
