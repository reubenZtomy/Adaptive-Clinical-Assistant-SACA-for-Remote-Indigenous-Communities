// update icons to what you have in src/assets/images/
import mic from "./images/microphone.png";
import textIcon from "./images/keyboard.png";
import imgIcon from "./images/image-gallery.png";

const services = [
  {
    id: "svc-voice",
    name: "Voice Input",
    body: "Record patient symptoms and medical notes using voice commands",
    image: mic,
    path: "/voice",
  },
  {
    id: "svc-text",
    name: "Text Input",
    body: "Enter patient information, symptoms, and medical observations",
    image: textIcon,
    path: "/text",
  },
  {
    id: "svc-image",
    name: "Image Input",
    body: "Choose pictures to describe symptoms if typing/speaking is hard",
    image: imgIcon,
    path: "/image",
  },
];

export default services;
