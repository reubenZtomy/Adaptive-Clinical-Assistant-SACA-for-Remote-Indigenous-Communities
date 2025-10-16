import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("language", "routes/language.tsx"),
  route("mode", "routes/mode.tsx"),
  route("chat", "routes/chat.tsx"),
  route("login", "routes/login.tsx"),
  route("register", "routes/register.tsx"),
  route("profile", "routes/profile.tsx"),
  // Catch-all route for Chrome DevTools and other requests
  route("*", "routes/404.tsx"),
] satisfies RouteConfig;
