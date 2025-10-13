// src/pages/Home.jsx
import Navbar from "../components/navbar/Navbar";
import Banner from "../components/banner/Banner";
//import Services from "../components/services/Services";
import Footer from "../components/footer/Footer";
import AboutSection from "../components/about/AboutSection";

export default function Home() {
  return (
    <>
      <Navbar />
      <Banner />
      <AboutSection/>
      <Footer />
    </>
  );
}
