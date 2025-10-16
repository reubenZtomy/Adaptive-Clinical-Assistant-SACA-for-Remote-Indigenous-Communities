import { Box, Container, Heading, Text, Button } from "@chakra-ui/react";
import { Link } from "react-router";

export function meta() {
  return [
    { title: "404 - Page Not Found - SwinSACA" },
  ];
}

export default function NotFound() {
  return (
    <Container maxW="container.md" py={20} textAlign="center">
      <Box>
        <Heading size="2xl" mb={4} color="teal.500">
          404
        </Heading>
        <Heading size="lg" mb={4}>
          Page Not Found
        </Heading>
        <Text mb={8} color="gray.600">
          The page you're looking for doesn't exist or has been moved.
        </Text>
        <Button as={Link} to="/" colorScheme="teal" size="lg">
          Go Home
        </Button>
      </Box>
    </Container>
  );
}
