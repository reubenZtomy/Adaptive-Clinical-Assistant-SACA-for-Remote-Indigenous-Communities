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
  Spinner,
  Center,
  VStack,
  HStack,
  Flex
} from "@chakra-ui/react";

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
  const [filteredPredictions, setFilteredPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const onOpen = () => setIsOpen(true);
  const onClose = () => setIsOpen(false);
  const [selectedPrediction, setSelectedPrediction] = useState<Prediction | null>(null);
  const [sortBy, setSortBy] = useState<string>("date-desc");

  const isDark = false; // Light mode
  const bgColor = "white";
  const borderColor = "black";

  // Check if user is logged in
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/login");
      return;
    }
    fetchPredictions();
  }, [navigate]);

  // Sort predictions when sortBy changes
  useEffect(() => {
    sortPredictions();
  }, [predictions, sortBy]);

  const fetchPredictions = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API_BASE_URL}/auth/predictions`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setPredictions(data.predictions || []);
        setError("");
      } else {
        setError("Failed to fetch predictions");
      }
    } catch (err) {
      setError("Error fetching predictions");
      console.error("Error:", err);
    } finally {
      setLoading(false);
    }
  };

  const deletePrediction = async (id: number) => {
    try {
      setDeletingId(id);
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API_BASE_URL}/auth/predictions/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        setPredictions(predictions.filter((p) => p.id !== id));
      } else {
        setError("Failed to delete prediction");
      }
    } catch (err) {
      setError("Error deleting prediction");
      console.error("Error:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const showPredictionDetails = (prediction: Prediction) => {
    setSelectedPrediction(prediction);
    onOpen();
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const truncateText = (text: string, maxLength: number) => {
    return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
  };

  const getSeverityColor = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "mild":
        return "green";
      case "moderate":
        return "yellow";
      case "severe":
        return "red";
      default:
        return "gray";
    }
  };

  const getSeverityValue = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "mild":
        return 1;
      case "moderate":
        return 2;
      case "severe":
        return 3;
      default:
        return 0;
    }
  };

  const getSeverityProgress = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "mild":
        return 33;
      case "moderate":
        return 66;
      case "severe":
        return 100;
      default:
        return 0;
    }
  };

  const getFinalPrediction = (prediction: Prediction) => {
    if (prediction.fused_result && prediction.fused_result.final) {
      return {
        disease: prediction.fused_result.final.disease_label || 'Unknown',
        probability: prediction.fused_result.final.probability || 0,
        severity: prediction.fused_result.final.severity || prediction.severity,
        source: prediction.fused_result.final.source || 'Unknown'
      };
    }
    return null;
  };

  const sortPredictions = () => {
    let sorted = [...predictions];
    
    switch (sortBy) {
      case "date-asc":
        sorted.sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime());
        break;
      case "date-desc":
        sorted.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        break;
      case "severity-asc":
        sorted.sort((a, b) => getSeverityValue(a.severity) - getSeverityValue(b.severity));
        break;
      case "severity-desc":
        sorted.sort((a, b) => getSeverityValue(b.severity) - getSeverityValue(a.severity));
        break;
      default:
        break;
    }
    
    setFilteredPredictions(sorted);
  };

  const handleSortChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSortBy(event.target.value);
  };

  if (loading) {
    return (
      <Container maxW="7xl" py={8}>
        <Center>
          <VStack spacing={4}>
            <Spinner size="xl" color="blue.500" />
            <Text>Loading predictions...</Text>
          </VStack>
        </Center>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxW="7xl" py={8}>
        <Center>
          <VStack spacing={4}>
            <Text color="red.500">{error}</Text>
            <Button onClick={fetchPredictions}>Retry</Button>
          </VStack>
        </Center>
      </Container>
    );
  }

  return (
    <Container maxW="7xl" py={8}>
      <Box>
        <VStack spacing={6} align="stretch">
          <Box textAlign="center">
            <Heading size="xl" mb={2} color="black">Prediction History</Heading>
            <Text color="gray.600" fontSize="lg">
              View and manage your medical predictions
            </Text>
          </Box>

          {/* Sorting Controls */}
          <Box>
            <HStack spacing={4} align="center">
              <Text fontSize="sm" fontWeight="medium" color="black">
                Sort by:
              </Text>
              <Box
                as="select"
                value={sortBy}
                onChange={handleSortChange}
                p={2}
                border="1px solid"
                borderColor="black"
                borderRadius="md"
                bg="white"
                maxW="200px"
                fontSize="sm"
              >
                <option value="date-desc">Date (Newest First)</option>
                <option value="date-asc">Date (Oldest First)</option>
                <option value="severity-desc">Severity (High to Low)</option>
                <option value="severity-asc">Severity (Low to High)</option>
              </Box>
            </HStack>
          </Box>

          {/* Predictions List */}
          {filteredPredictions.length === 0 && !loading ? (
            <Center py={12}>
              <VStack spacing={4}>
                <Text fontSize="lg" color="gray.500">
                  No predictions found
                </Text>
                <Text fontSize="sm" color="gray.400">
                  Complete a medical assessment to see your predictions here
                </Text>
              </VStack>
            </Center>
          ) : filteredPredictions.length > 0 ? (
            <VStack spacing={4} align="stretch">
              {filteredPredictions.map((prediction) => {
                const finalPrediction = getFinalPrediction(prediction);
                return (
                  <Box
                    key={prediction.id}
                    p={6}
                    border="2px solid"
                    borderColor="black"
                    borderRadius="lg"
                    bg={bgColor}
                    _hover={{ shadow: "lg", transform: "translateY(-2px)" }}
                    transition="all 0.2s"
                  >
                    <VStack spacing={4} align="stretch">
                      {/* Header with Date and Actions */}
                      <Flex justify="space-between" align="center">
                        <Text fontSize="sm" color="gray.600" fontWeight="medium">
                          {formatDate(prediction.created_at)}
                        </Text>
                        <HStack spacing={2}>
                          <IconButton
                            aria-label="View details"
                            children="👁"
                            size="sm"
                            variant="outline"
                            borderColor="black"
                            color="black"
                            _hover={{ bg: "gray.100" }}
                            onClick={() => showPredictionDetails(prediction)}
                          />
                          <IconButton
                            aria-label="Delete prediction"
                            children="🗑"
                            size="sm"
                            variant="outline"
                            borderColor="red.500"
                            color="red.500"
                            _hover={{ bg: "red.50" }}
                            isLoading={deletingId === prediction.id}
                            onClick={() => deletePrediction(prediction.id)}
                          />
                        </HStack>
                      </Flex>

                      <Box height="1px" bg="gray.300" />

                      {/* Prediction Text */}
                      <Box>
                        <Text
                          fontSize="md"
                          cursor="pointer"
                          color="black"
                          fontWeight="medium"
                          _hover={{ textDecoration: "underline" }}
                          onClick={() => showPredictionDetails(prediction)}
                          noOfLines={3}
                        >
                          {truncateText(prediction.prediction_text, 150)}
                        </Text>
                      </Box>

                      {/* Severity with Progress Bar */}
                      <Box>
                        <Flex align="center" gap={3} mb={2}>
                          <Text fontSize="sm" fontWeight="medium" color="black">
                            Severity:
                          </Text>
                          <Badge 
                            colorScheme={getSeverityColor(prediction.severity)}
                            size="lg"
                            px={3}
                            py={1}
                            borderRadius="full"
                          >
                            {prediction.severity.toUpperCase()}
                          </Badge>
                          <Text fontSize="sm" color="gray.600">
                            ({getSeverityValue(prediction.severity)}/3)
                          </Text>
                        </Flex>
                        <Box
                          w="100%"
                          h="8px"
                          bg="gray.200"
                          borderRadius="full"
                          overflow="hidden"
                        >
                          <Box
                            h="100%"
                            w={`${getSeverityProgress(prediction.severity)}%`}
                            bg={getSeverityColor(prediction.severity) === "green" ? "green.400" : 
                                 getSeverityColor(prediction.severity) === "yellow" ? "yellow.400" : 
                                 getSeverityColor(prediction.severity) === "red" ? "red.400" : "gray.400"}
                            borderRadius="full"
                            transition="width 0.3s ease"
                          />
                        </Box>
                      </Box>

                      {/* Final ML Prediction */}
                      {finalPrediction && (
                        <Box p={3} bg="gray.50" borderRadius="md" border="1px solid" borderColor="gray.200">
                          <Text fontSize="sm" fontWeight="bold" color="black" mb={2}>
                            Final ML Prediction:
                          </Text>
                          <VStack spacing={2} align="start">
                            <HStack spacing={4}>
                              <Text fontSize="sm" color="black">
                                <strong>Disease:</strong> {finalPrediction.disease}
                              </Text>
                              <Text fontSize="sm" color="gray.600">
                                <strong>Confidence:</strong> {(finalPrediction.probability * 100).toFixed(1)}%
                              </Text>
                            </HStack>
                            <Text fontSize="sm" color="gray.600">
                              <strong>Source:</strong> {finalPrediction.source}
                            </Text>
                          </VStack>
                        </Box>
                      )}

                      {/* Language and Mode Badges */}
                      <HStack spacing={2}>
                        <Badge colorScheme={prediction.language === 'english' ? 'blue' : 'purple'} variant="outline">
                          {prediction.language}
                        </Badge>
                        <Badge colorScheme="gray" variant="outline">
                          {prediction.mode}
                        </Badge>
                      </HStack>
                    </VStack>
                  </Box>
                );
              })}
            </VStack>
          ) : null}

          {/* Refresh Button */}
          <HStack justify="center" pt={4}>
            <Button
              onClick={fetchPredictions}
              colorScheme="blue"
              variant="outline"
              borderColor="black"
              color="black"
              _hover={{ bg: "blue.50" }}
            >
              Refresh
            </Button>
          </HStack>
        </VStack>
      </Box>

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
            position="relative"
            bg="white"
            borderRadius="lg"
            p={6}
            maxW="600px"
            w="full"
            maxH="80vh"
            overflowY="auto"
            border="2px solid"
            borderColor="black"
          >
            <VStack spacing={4} align="stretch">
              <Flex justify="space-between" align="center">
                <Heading size="md" color="black">Prediction Details</Heading>
                <Button
                  onClick={onClose}
                  size="sm"
                  variant="outline"
                  borderColor="black"
                  color="black"
                >
                  ✕
                </Button>
              </Flex>

              {selectedPrediction && (
                <>
                  <Box>
                    <Text fontSize="sm" color="gray.600" mb={2}>
                      {formatDate(selectedPrediction.created_at)}
                    </Text>
                    <Text fontSize="md" color="black" mb={4}>
                      {selectedPrediction.prediction_text}
                    </Text>
                  </Box>

                  {/* Final Prediction */}
                  {getFinalPrediction(selectedPrediction) && (
                    <Box p={4} bg="blue.50" borderRadius="md" border="1px solid" borderColor="blue.200">
                      <Text fontSize="lg" fontWeight="bold" color="black" mb={3}>
                        Final Prediction
                      </Text>
                      <VStack spacing={2} align="start">
                        <Text fontSize="sm" color="black">
                          <strong>Disease:</strong> {getFinalPrediction(selectedPrediction)?.disease}
                        </Text>
                        <Text fontSize="sm" color="black">
                          <strong>Confidence:</strong> {((getFinalPrediction(selectedPrediction)?.probability || 0) * 100).toFixed(1)}%
                        </Text>
                        <Text fontSize="sm" color="black">
                          <strong>Severity:</strong> {getFinalPrediction(selectedPrediction)?.severity}
                        </Text>
                        <Text fontSize="sm" color="black">
                          <strong>Source:</strong> {getFinalPrediction(selectedPrediction)?.source}
                        </Text>
                      </VStack>
                    </Box>
                  )}

                  {/* Detailed Results */}
                  <Box>
                    <Text fontSize="md" fontWeight="bold" color="black" mb={2}>
                      Detailed Results
                    </Text>
                    <Box
                      p={3}
                      bg="gray.50"
                      borderRadius="md"
                      border="1px solid"
                      borderColor="gray.200"
                      maxH="200px"
                      overflowY="auto"
                    >
                      <Text fontSize="sm" color="black" whiteSpace="pre-wrap">
                        {JSON.stringify(selectedPrediction.fused_result, null, 2)}
                      </Text>
                    </Box>
                  </Box>

                  <HStack spacing={2}>
                    <Badge colorScheme={selectedPrediction.language === 'english' ? 'blue' : 'purple'} variant="outline">
                      {selectedPrediction.language}
                    </Badge>
                    <Badge colorScheme="gray" variant="outline">
                      {selectedPrediction.mode}
                    </Badge>
                  </HStack>
                </>
              )}
            </VStack>
          </Box>
        </Box>
      )}
    </Container>
  );
}