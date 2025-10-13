import cough from "./symptoms/cough.jpg";
import headache from "./symptoms/headache.jpeg";
import stomach from "./symptoms/stomach_pain.jpg";
import rash from "./symptoms/rash.jpg"; 
import wound from "./symptoms/wound.jpg";
import ear from "./symptoms/ear_pain.jpg";
import eye from "./symptoms/eye_problem.jpg";
import tooth from "./symptoms/tooth_pain.jpeg";
import vomiting from "./symptoms/vomiting.jpg";
import backpain from "./symptoms/back-pain.jpg";
import chestpain from "./symptoms/chestpain.jpg";
import fever from "./symptoms/fever.jpg";


// If you get Arrernte translations later, add `arr:` field too.
const CATALOG = [
  { id: "cough",      name: "Cough",               img: cough },
  { id: "headache",   name: "Headache",            img: headache },
  { id: "stomach",    name: "Stomach Pain",        img: stomach },
  { id: "rash",       name: "Skin Rash",           img: rash },
  { id: "wound",      name: "Wound / Cut",         img: wound },
  { id: "ear",        name: "Ear Pain",            img: ear },
  { id: "eye",        name: "Eye Problem",         img: eye },
  { id: "tooth",      name: "Tooth Pain",          img: tooth },
  { id: "vomiting",   name: "Vomiting",            img: vomiting },
{ id: "backpain",   name: "Back Pain",            img: backpain },
 { id: "chestpain",   name: "Chest Pain",            img: chestpain },
  { id: "fever",   name: "Fever",            img: fever },
 
];
export default CATALOG;
