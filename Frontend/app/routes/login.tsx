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
} from "@chakra-ui/react";
// Note: ViewIcon and ViewOffIcon may not be available in Chakra UI v3
// Using simple text for now
import { motion } from "framer-motion";

const API_BASE_URL = "http://localhost:5000/api";

export default function Login() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    username: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
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

    try {
      console.log("Attempting login with:", formData);
      
      const response = await fetch(`${API_BASE_URL}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      console.log("Login response status:", response.status);
      const data = await response.json();
      console.log("Login response data:", data);

      if (response.ok) {
        // Store token and user data
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
        
        console.log("Login successful, navigating to home...");
        // Navigate to home page
        navigate("/");
      } else {
        console.log("Login failed:", data.message);
        setError(data.message || "Login failed");
      }
    } catch (err) {
      console.error("Login error:", err);
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
          <Stack gap={6}>
            <Box textAlign="center">
              <Heading size="lg" mb={2}>
                Welcome Back
              </Heading>
              <Text color="gray.600">
                Sign in to your SwinSACA account
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
              <Stack gap={4}>
                <Box>
                  <Text as="label" fontSize="sm" fontWeight="medium" mb={2} display="block">
                    Username or Email *
                  </Text>
                  <Input
                    name="username"
                    type="text"
                    value={formData.username}
                    onChange={handleChange}
                    placeholder="Enter your username or email"
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
                      placeholder="Enter your password"
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

                <Button
                  type="submit"
                  colorScheme="teal"
                  size="lg"
                  loading={isLoading}
                  loadingText="Signing in..."
                  w="full"
                >
                  Sign In
                </Button>
              </Stack>
            </form>

            <Box textAlign="center">
              <Text>
                Don't have an account?{" "}
                <Link to="/register" style={{ color: "#319795", fontWeight: "bold" }}>
                  Sign up
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
