import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router";
import {
  Box,
  Button,
  HStack,
  IconButton,
  Text,
} from "@chakra-ui/react";
import { FaUser, FaSignInAlt, FaUserPlus, FaSignOutAlt, FaCog } from "react-icons/fa";

interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
}

export function Header() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const bgColor = "white";
  const borderColor = "gray.200";

  useEffect(() => {
    const checkUser = () => {
      const storedUser = localStorage.getItem("user");
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
        } catch (err) {
          localStorage.removeItem("user");
          localStorage.removeItem("access_token");
          setUser(null);
        }
      } else {
        setUser(null);
      }
      setIsLoading(false);
    };

    checkUser();

    // Listen for storage changes (when user logs in/out in another tab)
    const handleStorageChange = (e: StorageEvent) => {
      if (e.key === "user") {
        checkUser();
      }
    };

    window.addEventListener("storage", handleStorageChange);

    // Also check periodically for changes (for same-tab login/logout)
    const interval = setInterval(checkUser, 1000);

    return () => {
      window.removeEventListener("storage", handleStorageChange);
      clearInterval(interval);
    };
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user");
    setUser(null);
    navigate("/");
  };

  const getInitials = (firstName?: string, lastName?: string) => {
    if (firstName && lastName) {
      return `${firstName[0]}${lastName[0]}`.toUpperCase();
    }
    return "U";
  };

  if (isLoading) {
    return null;
  }

  return (
    <Box
      position="fixed"
      top={0}
      left={0}
      right={0}
      zIndex={1000}
      bg={bgColor}
      borderBottom="1px"
      borderColor={borderColor}
      px={4}
      py={2}
    >
      <HStack justify="space-between" maxW="7xl" mx="auto">
        {/* Left side - Logo */}
        <Link to="/">
          <Text fontSize="xl" fontWeight="bold" color="teal.500">
            SwinSACA
          </Text>
        </Link>

        {/* Right side - Navigation Links and Auth Buttons */}
        <HStack spacing={4}>
          <Button as={Link} to="/" variant="ghost" size="sm" colorScheme="teal">
            Home
          </Button>
          
          {user && (
            <>
              <Button
                as={Link}
                to="/history"
                variant="outline"
                size="sm"
                colorScheme="teal"
                leftIcon={<Text>📊</Text>}
              >
                View History
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                leftIcon={<FaSignOutAlt />}
              >
                Logout
              </Button>
            </>
          )}
          
          <HStack spacing={2}>
            {user ? (
            <HStack spacing={2}>
              <Box
                w={8}
                h={8}
                borderRadius="full"
                bg="teal.500"
                color="white"
                display="flex"
                alignItems="center"
                justifyContent="center"
                fontSize="sm"
                fontWeight="bold"
              >
                {getInitials(user.first_name, user.last_name)}
              </Box>
              <Text fontSize="sm">
                {user.first_name ? `${user.first_name} ${user.last_name}` : user.username}
              </Text>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate("/profile")}
                leftIcon={<FaCog />}
              >
                Profile
              </Button>
            </HStack>
          ) : (
            <>
              <Button
                as={Link}
                to="/login"
                variant="ghost"
                leftIcon={<FaSignInAlt />}
                size="sm"
              >
                Login
              </Button>
              <Button
                as={Link}
                to="/register"
                colorScheme="teal"
                leftIcon={<FaUserPlus />}
                size="sm"
              >
                Register
              </Button>
            </>
            )}
          </HStack>
        </HStack>
      </HStack>
    </Box>
  );
}
