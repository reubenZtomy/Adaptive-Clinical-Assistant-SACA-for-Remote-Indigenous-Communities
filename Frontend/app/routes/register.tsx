import { useState } from "react";
import { useNavigate, Link } from "react-router";
import {
  Box,
  Button,
  Container,
  Input,
  Stack,
  Text,
  Heading,
  Alert,
  IconButton,
  HStack,
} from "@chakra-ui/react";
// Note: ViewIcon and ViewOffIcon may not be available in Chakra UI v3
// Using simple text for now
import { motion } from "framer-motion";

const API_BASE_URL = "http://localhost:5000/api";

export default function Register() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: "",
    email: "",
    password: "",
    confirmPassword: "",
    first_name: "",
    last_name: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const bgColor = "white";
  const borderColor = "gray.200";

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError("");

    // Validate passwords match
    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      setIsLoading(false);
      return;
    }

    // Validate password length
    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters long");
      setIsLoading(false);
      return;
    }

    try {
      console.log("Attempting registration with:", formData);
      
      const response = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: formData.username,
          email: formData.email,
          password: formData.password,
          first_name: formData.first_name,
          last_name: formData.last_name,
        }),
      });

      console.log("Registration response status:", response.status);
      const data = await response.json();
      console.log("Registration response data:", data);

      if (response.ok) {
        // Store token and user data
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        
        console.log("Registration successful, navigating to home...");
        // Navigate to home page
        navigate("/");
      } else {
        setError(data.message || "Registration failed");
      }
    } catch (err) {
      console.error("Registration error:", err);
      setError("Network error. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Container maxW="md" minH="100vh" display="flex" alignItems="center" justifyContent="center">
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
                Create Account
              </Heading>
              <Text color="gray.600">
                Join SwinSACA to get started
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

            <form onSubmit={handleSubmit}>
              <Stack spacing={4}>
                <HStack>
                  <Box flex={1}>
                    <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                      First Name *
                    </Text>
                    <Input
                      name="first_name"
                      type="text"
                      value={formData.first_name}
                      onChange={handleChange}
                      placeholder="First name"
                      size="lg"
                      required
                    />
                  </Box>
                  <Box flex={1}>
                    <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                      Last Name *
                    </Text>
                    <Input
                      name="last_name"
                      type="text"
                      value={formData.last_name}
                      onChange={handleChange}
                      placeholder="Last name"
                      size="lg"
                      required
                    />
                  </Box>
                </HStack>

                <Box>
                  <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                    Username *
                  </Text>
                  <Input
                    name="username"
                    type="text"
                    value={formData.username}
                    onChange={handleChange}
                    placeholder="Choose a username"
                    size="lg"
                    required
                  />
                </Box>

                <Box>
                  <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                    Email *
                  </Text>
                  <Input
                    name="email"
                    type="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder="Enter your email"
                    size="lg"
                    required
                  />
                </Box>

                <Box>
                  <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                    Password *
                  </Text>
                  <Box position="relative">
                    <Input
                      name="password"
                      type={showPassword ? "text" : "password"}
                      value={formData.password}
                      onChange={handleChange}
                      placeholder="Create a password"
                      size="lg"
                      pr="50px"
                      required
                    />
                    <IconButton
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      variant="ghost"
                      size="sm"
                      position="absolute"
                      right="5px"
                      top="50%"
                      transform="translateY(-50%)"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      {showPassword ? "👁️" : "👁️‍🗨️"}
                    </IconButton>
                  </Box>
                </Box>

                <Box>
                  <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                    Confirm Password *
                  </Text>
                  <Box position="relative">
                    <Input
                      name="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      value={formData.confirmPassword}
                      onChange={handleChange}
                      placeholder="Confirm your password"
                      size="lg"
                      pr="50px"
                      required
                    />
                    <IconButton
                      aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                      variant="ghost"
                      size="sm"
                      position="absolute"
                      right="5px"
                      top="50%"
                      transform="translateY(-50%)"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    >
                      {showConfirmPassword ? "👁️" : "👁️‍🗨️"}
                    </IconButton>
                  </Box>
                </Box>

                <Button
                  type="submit"
                  colorScheme="teal"
                  size="lg"
                  isLoading={isLoading}
                  loadingText="Creating account..."
                  w="full"
                >
                  Create Account
                </Button>
              </Stack>
            </form>

            <Box textAlign="center">
              <Text>
                Already have an account?{" "}
                <Link to="/login" style={{ color: "#319795", fontWeight: "bold" }}>
                  Sign in
                </Link>
              </Text>
            </Box>

            <Box textAlign="center">
              <Link to="/" style={{ color: "#319795" }}>
                ← Back to Home
              </Link>
            </Box>
          </Stack>
        </Box>
      </motion.div>
    </Container>
  );
}
