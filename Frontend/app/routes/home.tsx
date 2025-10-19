import type { Route } from "./+types/home";
import { Welcome } from "../welcome/welcome";

export function meta({}: Route.MetaArgs) {
  return [
    { title: "SACA Clinical Assistant" },
    { name: "description", content: "Adaptive Clinical Assistant for Remote Indigenous Communities" },
  ];
}

export default function Home() {
  return <Welcome />;
}
