import { useState, useEffect } from "react";
import { useNavigate } from "react-router";
import {
  Box,
  Button,
  Container,
  Input,
  Stack,
  Text,
  Heading,
  HStack,
  VStack,
} from "@chakra-ui/react";
import { motion } from "framer-motion";

const API_BASE_URL = "http://localhost:5000/api";

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  created_at: string;
}

export default function Profile() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const bgColor = "white";
  const borderColor = "gray.200";

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      navigate("/login");
      return;
    }

    // Try to get user data from localStorage first
    const storedUser = localStorage.getItem("user");
    if (storedUser) {
      try {
        const userData = JSON.parse(storedUser);
        setUser(userData);
        setFormData({
          first_name: userData.first_name || "",
          last_name: userData.last_name || "",
          email: userData.email || "",
        });
        setIsLoading(false);
      } catch (err) {
        console.error("Failed to parse stored user data:", err);
      }
    }

    // Then fetch fresh data from API
    fetchUserProfile();
  }, [navigate]);

  const fetchUserProfile = async () => {
    try {
      setIsLoading(true);
      setError("");
      
      const token = localStorage.getItem("access_token");
      console.log("Fetching profile with token:", token ? "present" : "missing");
      console.log("Token value:", token);
      
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      console.log("Profile response status:", response.status);

      if (response.ok) {
        const userData = await response.json();
        console.log("Profile data received:", userData);
        setUser(userData);
        setFormData({
          first_name: userData.first_name || "",
          last_name: userData.last_name || "",
          email: userData.email || "",
        });
      } else if (response.status === 401) {
        console.log("Unauthorized, redirecting to login");
        localStorage.removeItem("access_token");
        localStorage.removeItem("user");
        navigate("/login");
      } else {
        const errorData = await response.json();
        console.log("Profile API error:", errorData);
        // Only show error if we don't have cached data from localStorage
        const storedUser = localStorage.getItem("user");
        if (!storedUser) {
          setError(errorData.message || "Failed to fetch profile");
        }
      }
    } catch (err) {
      console.error("Profile fetch error:", err);
      setError("Network error. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (response.ok) {
        setUser(data);
        setSuccess("Profile updated successfully!");
        // Update stored user data
        localStorage.setItem("user", JSON.stringify(data));
      } else {
        setError(data.message || "Update failed");
      }
    } catch (err) {
      setError("Network error. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    navigate("/");
  };

  if (isLoading) {
    return (
      <Container maxW="md" minH="100vh" display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={4}>
          <Text fontSize="lg">Loading your profile...</Text>
          {error && (
            <Box
              bg="red.50"
              border="1px solid"
              borderColor="red.200"
              borderRadius="md"
              p={4}
              color="red.800"
            >
              <Text fontWeight="bold">⚠️ Error:</Text>
              <Text>{error}</Text>
            </Box>
          )}
        </VStack>
      </Container>
    );
  }

  if (!user) {
    return (
      <Container maxW="md" minH="100vh" display="flex" alignItems="center" justifyContent="center">
        <VStack spacing={4}>
          <Text fontSize="lg">No user data found</Text>
          <Button onClick={() => navigate("/login")} colorScheme="teal">
            Go to Login
          </Button>
        </VStack>
      </Container>
    );
  }

  return (
    <Container maxW="md" minH="100vh" py={8}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{ width: "100%" }}
      >
        <Box
          bg={bgColor}
          p={8}
          rounded="lg"
          shadow="lg"
          border="1px"
          borderColor={borderColor}
          w="full"
        >
          <Stack spacing={6}>
            <Box textAlign="center">
              <Heading size="lg" mb={2}>
                Profile
              </Heading>
              <Text color="gray.600">
                Manage your account information
              </Text>
            </Box>

            {error && (
              <Box
                bg="red.50"
                border="1px solid"
                borderColor="red.200"
                borderRadius="md"
                p={4}
                color="red.800"
              >
                <Text fontWeight="bold">⚠️ Error:</Text>
                <Text>{error}</Text>
              </Box>
            )}

            {success && (
              <Box
                bg="green.50"
                border="1px solid"
                borderColor="green.200"
                borderRadius="md"
                p={4}
                color="green.800"
              >
                <Text fontWeight="bold">✅ Success:</Text>
                <Text>{success}</Text>
              </Box>
            )}

            {/* User Info Display */}
            <VStack spacing={3} align="stretch">
              <HStack justify="space-between">
                <Text fontWeight="bold">Username:</Text>
                <Text>{user.username}</Text>
              </HStack>
              <HStack justify="space-between">
                <Text fontWeight="bold">Member since:</Text>
                <Text>{new Date(user.created_at).toLocaleDateString()}</Text>
              </HStack>
            </VStack>

            <Box height="1px" bg="gray.200" my={4} />

            {/* Profile Update Form */}
            <form onSubmit={handleSubmit}>
              <Stack spacing={4}>
                <HStack>
                  <Box flex={1}>
                    <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                      First Name
                    </Text>
                    <Input
                      name="first_name"
                      type="text"
                      value={formData.first_name}
                      onChange={handleChange}
                      placeholder="First name"
                      size="lg"
                    />
                  </Box>
                  <Box flex={1}>
                    <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                      Last Name
                    </Text>
                    <Input
                      name="last_name"
                      type="text"
                      value={formData.last_name}
                      onChange={handleChange}
                      placeholder="Last name"
                      size="lg"
                    />
                  </Box>
                </HStack>

                <Box>
                  <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                    Email
                  </Text>
                  <Input
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="Enter your email"
                    size="lg"
                  />
                </Box>

                <Button
                  type="submit"
                  colorScheme="teal"
                  size="lg"
                  isLoading={isSubmitting}
                  loadingText="Updating..."
                  w="full"
                >
                  Update Profile
                </Button>
              </Stack>
            </form>

            <Box height="1px" bg="gray.200" my={4} />

            <Stack spacing={3}>
              <Button
                colorScheme="red"
                variant="outline"
                size="lg"
                onClick={handleLogout}
                w="full"
              >
                Logout
              </Button>
              
              <Button
                variant="ghost"
                size="lg"
                onClick={() => navigate("/")}
                w="full"
              >
                ← Back to Home
              </Button>
            </Stack>
          </Stack>
        </Box>
      </motion.div>
    </Container>
  );
}
