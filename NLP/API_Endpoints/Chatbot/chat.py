# --- Chatbot/chat.py (updated) ---

import json
import random
import re
from typing import Dict, List, Optional
from pathlib import Path

import torch

# Support both package import (from Chatbot.chat) and running this file directly
try:
    from .model import NeuralNet
    from .nltk_utils import tokenize, bag_of_words, stem
except ImportError:  # running as a script (python chat.py)
    from model import NeuralNet
    from nltk_utils import tokenize, bag_of_words, stem

# ---------- Paths relative to this file ----------
PKG_DIR = Path(__file__).resolve().parent
INTENTS_PATH = PKG_DIR / "intents.json"
DATA_PATH = PKG_DIR / "data.pth"

# -------------- Helpers for JSON schema --------------
def get_intents(doc: Dict):
    intents = doc.get("intents")
    if not isinstance(intents, list):
        raise ValueError("intents.json must contain a top-level 'intents' array")
    return intents

def get_tag(intent: Dict) -> Optional[str]:
    return intent.get("tag", intent.get("intent"))

def get_responses(intent: Dict) -> List[str]:
    rs = intent.get("responses", [])
    if isinstance(rs, str):
        rs = [rs]
    return rs

# -------------- Load resources --------------
with INTENTS_PATH.open("r", encoding="utf-8") as f:
    intents_doc = json.load(f)
intents_list = get_intents(intents_doc)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Expect a training artifact dict with sizes, vocab, tags, and model_state
data = torch.load(str(DATA_PATH), map_location=device)
input_size = data["input_size"]
hidden_size = data["hidden_size"]
output_size = data["output_size"]
all_words = data["all_words"]
tags = data["tags"]
model_state = data["model_state"]

model = NeuralNet(input_size, hidden_size, output_size).to(device)
model.load_state_dict(model_state)
model.eval()

bot_name = "Bot"
THRESHOLD = 0.75

# -------------- Dialog State (covers multiple symptom flows) --------------
dialog_state: Dict = {
    "active_domain": None,   # "headache" | "fever" | "cough" | "stomach" | "fatigue" | "skin"
    "stage": None,           # domain-specific stage
    "slots": {}              # domain-specific slots
}

def reset_state():
    dialog_state["active_domain"] = None
    dialog_state["stage"] = None
    dialog_state["slots"] = {}

# -------------- Intent groups (router triggers) --------------
HEADACHE_INTENTS = {"Symptom_Headache", "HeadacheFollowup", "Pain"}
FEVER_INTENTS    = {"Symptom_Fever", "FeverFollowup", "Fever"}
COUGH_INTENTS    = {"Symptom_Cough", "CoughFollowup", "Respiratory"}
STOMACH_INTENTS  = {"Symptom_Stomach", "StomachFollowup", "Digestive"}
FATIGUE_INTENTS  = {"Symptom_Fatigue", "FatigueFollowup", "GeneralWeakness"}
SKIN_INTENTS     = {"Symptom_SkinRash", "SkinRashFollowup", "Dermatology"}  # new

# Simple keyword sniffers to kick off a flow even if classifier tag isn't present
SKIN_KEYWORDS = [
    "rash","rashes","itch","itchy","itching","hives","urticaria","red spots","spots",
    "bumps","blister","blisters","eczema","psoriasis","dermatitis","ringworm",
    "mosquito bite","insect bite","allergy","allergic","welts","scaly","flaky","peeling"
]

# -------------- Shared extractors --------------
DURATION_PAT = re.compile(r"(\d+)\s*(minute|minutes|min|hour|hours|hr|hrs|day|days|week|weeks)", re.I)
SEVERITY_PAT = re.compile(r"\b(10|[1-9])\b")  # 1-10 scale

def extract_duration(text: str) -> Optional[str]:
    m = DURATION_PAT.search(text)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    if re.search(r"yesterday|today|all day|since (morning|evening|last night)", text, re.I):
        return re.search(r"(yesterday|today|all day|since (?:morning|evening|last night))", text, re.I).group(0)
    return None

def extract_severity(text: str) -> Optional[int]:
    m = SEVERITY_PAT.search(text)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(10|[1-9])\s*/\s*10\b", text)
    if m:
        return int(m.group(1))
    return None

def extract_yes_no(text: str) -> Optional[bool]:
    t = text.lower()
    if any(w in t for w in ["yes", "yeah", "yep", "yup", "affirmative", "i do", "i am", "have", "has"]):
        return True
    if any(w in t for w in ["no", "nope", "nah", "negative", "don't", "do not", "haven't", "hasn't"]):
        return False
    return None

# -------------- Headache flow --------------
LOCATION_WORDS_HEAD = {
    "front": ["front", "forehead", "frontal"],
    "back": ["back", "back of head", "occipital"],
    "left": ["left", "left side", "left temple"],
    "right": ["right", "right side", "right temple"],
    "sides": ["sides", "temple", "temples", "both sides"]
}
ASSOCIATED_HEAD_FLAGS = ["nausea", "vomit", "vomiting", "light", "sound", "aura",
                         "vision", "blur", "fever", "stiff neck", "neck", "photophobia", "phonophobia"]

def extract_location_head(text: str) -> Optional[str]:
    t = text.lower()
    for loc_key, variants in LOCATION_WORDS_HEAD.items():
        for v in variants:
            if v in t:
                return loc_key
    return None

def extract_assoc_head(text: str) -> Optional[List[str]]:
    t = text.lower()
    hits = [w for w in ASSOCIATED_HEAD_FLAGS if w in t]
    return list(sorted(set(hits))) if hits else None

def start_headache_flow():
    dialog_state["active_domain"] = "headache"
    dialog_state["stage"] = "ask_location"
    dialog_state["slots"] = {}
    return "I’m sorry to hear about the pain. Where exactly is the headache—front, back, sides, left or right?"

def continue_headache_flow(user_text: str) -> str:
    stage = dialog_state["stage"]
    slots = dialog_state["slots"]

    # passive extraction
    loc = extract_location_head(user_text)
    if loc and "location" not in slots:
        slots["location"] = loc
    sev = extract_severity(user_text)
    if sev and "severity" not in slots:
        slots["severity"] = sev
    dur = extract_duration(user_text)
    if dur and "duration" not in slots:
        slots["duration"] = dur
    assoc = extract_assoc_head(user_text)
    if assoc:
        prev = set(slots.get("assoc", []))
        slots["assoc"] = list(prev.union(assoc))

    # progression
    if stage == "ask_location":
        if "location" not in slots:
            return "Where is the headache located—front, back, sides, left or right?"
        dialog_state["stage"] = "ask_severity"
        return "Got it. On a scale of 1 to 10, how severe is the pain?"

    if stage == "ask_severity":
        if "severity" not in slots:
            return "On a scale of 1 to 10, how severe is the pain?"
        dialog_state["stage"] = "ask_duration"
        return "Understood. How long has this been going on?"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "How long has this been going on (e.g., 2 hours, since yesterday)?"
        dialog_state["stage"] = "ask_assoc"
        return "Any of these too: nausea/vomiting, sensitivity to light or sound, fever, stiff neck, or vision changes?"

    if stage == "ask_assoc":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        loc_txt = slots.get("location", "unspecified location")
        sev_txt = slots.get("severity", "unspecified severity")
        dur_txt = slots.get("duration", "unspecified duration")
        assoc_txt = ", ".join(slots.get("assoc", [])) if slots.get("assoc") else "no associated red-flag symptoms reported"
        reset_state()
        return (
            f"Thanks for the details. Summary: headache at {loc_txt}, severity {sev_txt}/10, duration {dur_txt}, {assoc_txt}. "
            f"If you develop high fever, severe neck stiffness, confusion, fainting, or vision changes, seek urgent care."
        )

    return "Thanks—please tell me a bit more so I can assess this carefully."

# -------------- Fever flow --------------
TEMP_PAT = re.compile(r"(\d+(?:\.\d+)?)\s*(°?\s*[cf]|celsius|fahrenheit)\b", re.I)
ASSOCIATED_FEV_FLAGS = ["chills", "shiver", "shivering", "sweat", "sweating", "body ache", "aches", "sore throat", "cough"]

def extract_temperature(text: str) -> Optional[str]:
    m = TEMP_PAT.search(text)
    if m:
        val = m.group(1)
        unit = m.group(2).replace("°", "").strip().lower()
        if unit in ["celsius", "c"]:
            return f"{val} C"
        if unit in ["fahrenheit", "f"]:
            return f"{val} F"
        return f"{val} {unit.upper()}"
    m2 = re.search(r"\b(\d{2}(?:\.\d+)?)\b", text)
    if m2:
        try:
            n = float(m2.group(1))
            if 34 <= n <= 43:
                return f"{n} C"
        except Exception:
            pass
    return None

def extract_assoc_fever(text: str) -> Optional[List[str]]:
    t = text.lower()
    hits = [w for w in ASSOCIATED_FEV_FLAGS if w in t]
    return list(sorted(set(hits))) if hits else None

def start_fever_flow():
    dialog_state["active_domain"] = "fever"
    dialog_state["stage"] = "ask_duration"
    dialog_state["slots"] = {}
    return "I’m sorry you’re feeling unwell. How long have you had the fever?"

def continue_fever_flow(user_text: str) -> str:
    stage = dialog_state["stage"]
    slots = dialog_state["slots"]

    dur = extract_duration(user_text)
    if dur and "duration" not in slots:
        slots["duration"] = dur
    temp = extract_temperature(user_text)
    if temp and "temperature" not in slots:
        slots["temperature"] = temp
    assoc = extract_assoc_fever(user_text)
    if assoc:
        prev = set(slots.get("assoc", []))
        slots["assoc"] = list(prev.union(assoc))

    if stage == "ask_duration":
        if "duration" not in slots:
            return "How long has the fever been present (e.g., 2 days, since yesterday)?"
        dialog_state["stage"] = "ask_temp"
        return "Do you know your highest temperature so far? (e.g., 38.5 C or 101 F)"

    if stage == "ask_temp":
        if "temperature" not in slots:
            return "What’s the highest temperature you’ve measured (e.g., 38.5 C or 101 F)?"
        dialog_state["stage"] = "ask_assoc"
        return "Are you also experiencing chills, sweating, body aches, sore throat, or cough?"

    if stage == "ask_assoc":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        dur_txt = slots.get("duration", "unspecified duration")
        temp_txt = slots.get("temperature", "unknown maximum temperature")
        assoc_txt = ", ".join(slots.get("assoc", [])) if slots.get("assoc") else "no additional symptoms reported"
        reset_state()
        return (
            f"Thanks. Summary: fever for {dur_txt}, max temperature {temp_txt}, {assoc_txt}. "
            f"If you develop a rash, stiff neck, confusion, severe dehydration, very high temperature, "
            f"or difficulty breathing, please seek urgent care."
        )

    return "Thanks—please share a bit more detail so I can assess this carefully."

# -------------- Cough/Respiratory flow --------------
ASSOCIATED_RESP_RED = ["breathless", "short of breath", "shortness of breath", "difficulty breathing",
                       "chest pain", "wheezing", "blue lips", "bluish lips"]
SPUTUM_COLORS = ["clear", "white", "yellow", "green", "brown", "bloody", "red", "pink", "rust"]

def extract_cough_type(text: str) -> Optional[str]:
    t = text.lower()
    if "dry" in t:
        return "dry"
    if any(w in t for w in ["mucus", "phlegm", "wet", "productive"]):
        return "productive"
    return None

def extract_sputum_color(text: str) -> Optional[str]:
    t = text.lower()
    for c in SPUTUM_COLORS:
        if c in t:
            return c
    return None

def extract_resp_red_flags(text: str) -> Optional[List[str]]:
    t = text.lower()
    hits = [w for w in ASSOCIATED_RESP_RED if w in t]
    return list(sorted(set(hits))) if hits else None

def start_cough_flow():
    dialog_state["active_domain"] = "cough"
    dialog_state["stage"] = "ask_type"
    dialog_state["slots"] = {}
    return "I see. Is your cough dry or producing mucus/phlegm?"

def continue_cough_flow(user_text: str) -> str:
    stage = dialog_state["stage"]
    slots = dialog_state["slots"]

    ctype = extract_cough_type(user_text)
    if ctype and "type" not in slots:
        slots["type"] = ctype
    color = extract_sputum_color(user_text)
    if color and "sputum_color" not in slots:
        slots["sputum_color"] = color
    dur = extract_duration(user_text)
    if dur and "duration" not in slots:
        slots["duration"] = dur
    red = extract_resp_red_flags(user_text)
    if red:
        prev = set(slots.get("red_flags", []))
        slots["red_flags"] = list(prev.union(red))

    if stage == "ask_type":
        if "type" not in slots:
            return "Is your cough dry, or are you bringing up mucus/phlegm?"
        dialog_state["stage"] = "ask_duration"
        return "How long have you been coughing?"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "How long has the cough been going on (e.g., 3 days, since last night)?"
        dialog_state["stage"] = "ask_assoc"
        return "Do you have any of these: shortness of breath, chest pain, wheezing, or bluish lips?"

    if stage == "ask_assoc":
        dialog_state["stage"] = "ask_sputum"
        return "If you’re producing mucus, what color is it (e.g., clear, yellow, green, bloody)?"

    if stage == "ask_sputum":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        t_txt = slots.get("type", "unspecified cough type")
        d_txt = slots.get("duration", "unspecified duration")
        s_txt = slots.get("sputum_color", "no sputum color reported")
        r_txt = ", ".join(slots.get("red_flags", [])) if slots.get("red_flags") else "no breathing red flags reported"
        reset_state()
        return (
            f"Thanks. Summary: {t_txt} cough for {d_txt}, sputum {s_txt}, {r_txt}. "
            f"If you experience severe breathlessness, chest pain, coughing up blood, or bluish lips, seek urgent care."
        )

    return "Thanks—please share a bit more so I can assess it carefully."

# -------------- Stomach/Digestive flow --------------
LOC_STOMACH = {
    "upper": ["upper", "upper abdomen", "upper stomach", "epigastric"],
    "lower": ["lower", "lower abdomen", "lower stomach"],
    "right": ["right side", "right abdomen", "right lower", "rlq", "ruq"],
    "left":  ["left side", "left abdomen", "left lower", "llq", "luq"],
    "center":["center", "middle", "around navel", "periumbilical"]
}
ASSOC_GI = ["vomit", "vomiting", "diarrhea", "diarrhoea", "bloody stool", "blood in stool",
            "black stool", "loss of appetite", "bloating", "gas", "nausea"]

def extract_stomach_location(text: str) -> Optional[str]:
    t = text.lower()
    for key, variants in LOC_STOMACH.items():
        for v in variants:
            if v in t:
                return key
    return None

def extract_gi_assoc(text: str) -> Optional[List[str]]:
    t = text.lower()
    hits = [w for w in ASSOC_GI if w in t]
    return list(sorted(set(hits))) if hits else None

def extract_food_trigger(text: str) -> Optional[bool]:
    t = text.lower()
    if any(p in t for p in ["after eating", "after food", "post meal", "post-meal", "after meals", "after i eat"]):
        return True
    if any(p in t for p in ["not related to food", "no relation with food", "before eating", "empty stomach"]):
        return False
    return None

def start_stomach_flow():
    dialog_state["active_domain"] = "stomach"
    dialog_state["stage"] = "ask_location"
    dialog_state["slots"] = {}
    return "I understand stomach issues can be uncomfortable. Where exactly is the pain—upper, lower, right, left, or center?"

def continue_stomach_flow(user_text: str) -> str:
    stage = dialog_state["stage"]
    slots = dialog_state["slots"]

    loc = extract_stomach_location(user_text)
    if loc and "location" not in slots:
        slots["location"] = loc
    dur = extract_duration(user_text)
    if dur and "duration" not in slots:
        slots["duration"] = dur
    assoc = extract_gi_assoc(user_text)
    if assoc:
        prev = set(slots.get("assoc", []))
        slots["assoc"] = list(prev.union(assoc))
    trig = extract_food_trigger(user_text)
    if trig is not None and "after_food" not in slots:
        slots["after_food"] = trig

    if stage == "ask_location":
        if "location" not in slots:
            return "Where is the pain located—upper, lower, right, left, or center?"
        dialog_state["stage"] = "ask_assoc"
        return "Do you also have any of these: nausea, vomiting, diarrhea, blood in stool, black stool, bloating, or loss of appetite?"

    if stage == "ask_assoc":
        dialog_state["stage"] = "ask_duration"
        return "How long has this been going on?"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "For how long has this been happening (e.g., 6 hours, since this morning, 3 days)?"
        dialog_state["stage"] = "ask_trigger"
        return "Does it get worse after eating, or is it unrelated to meals?"

    if stage == "ask_trigger":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        l_txt = slots.get("location", "unspecified location")
        d_txt = slots.get("duration", "unspecified duration")
        a_txt = ", ".join(slots.get("assoc", [])) if slots.get("assoc") else "no GI associated symptoms reported"
        f_txt = ("worse after eating" if slots.get("after_food") else
                 ("not clearly related to meals" if "after_food" in slots else "meal relation not specified"))
        reset_state()
        return (
            f"Thanks. Summary: abdominal symptoms at {l_txt}, duration {d_txt}, {a_txt}, {f_txt}. "
            f"If you develop persistent vomiting, blood in vomit or stool, black stool, severe dehydration, or intense sudden pain, seek urgent care."
        )

    return "Thanks—please tell me a little more so I can assess it carefully."

# -------------- Fatigue flow --------------
ASSOC_FATIGUE = ["dizzy", "dizziness", "shortness of breath", "breathless", "weight loss", "palpitations"]

def extract_sleep_quality(text: str) -> Optional[str]:
    t = text.lower()
    if any(p in t for p in ["sleep well", "sleeping well", "good sleep", "ok sleep", "fine sleep"]):
        return "sleeping well"
    if any(p in t for p in ["not sleeping", "poor sleep", "bad sleep", "insomnia", "cant sleep", "can't sleep"]):
        return "poor sleep"
    return None

def extract_time_of_day_pattern(text: str) -> Optional[str]:
    t = text.lower()
    if "morning" in t:
        return "worse in the morning"
    if "evening" in t or "night" in t:
        return "worse in the evening/night"
    if "all day" in t:
        return "all day"
    return None

def extract_assoc_fatigue(text: str) -> Optional[List[str]]:
    t = text.lower()
    hits = [w for w in ASSOC_FATIGUE if w in t]
    return list(sorted(set(hits))) if hits else None

def start_fatigue_flow():
    dialog_state["active_domain"] = "fatigue"
    dialog_state["stage"] = "ask_sleep"
    dialog_state["slots"] = {}
    return "I’m sorry you’re feeling this way. Have you been sleeping well recently?"

def continue_fatigue_flow(user_text: str) -> str:
    stage = dialog_state["stage"]
    slots = dialog_state["slots"]

    sl = extract_sleep_quality(user_text)
    if sl and "sleep" not in slots:
        slots["sleep"] = sl
    tod = extract_time_of_day_pattern(user_text)
    if tod and "pattern" not in slots:
        slots["pattern"] = tod
    dur = extract_duration(user_text)
    if dur and "duration" not in slots:
        slots["duration"] = dur
    assoc = extract_assoc_fatigue(user_text)
    if assoc:
        prev = set(slots.get("assoc", []))
        slots["assoc"] = list(prev.union(assoc))

    if stage == "ask_sleep":
        if "sleep" not in slots:
            return "Have you been sleeping well recently?"
        dialog_state["stage"] = "ask_pattern"
        return "Do you feel this tiredness more at certain times of the day (morning/evening), or all day?"

    if stage == "ask_pattern":
        if "pattern" not in slots:
            return "Is it worse in the morning, evening/night, or all day?"
        dialog_state["stage"] = "ask_duration"
        return "How long have you been feeling this way?"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "For how long have you felt like this (e.g., 1 week, since yesterday)?"
        dialog_state["stage"] = "ask_assoc"
        return "Are you also experiencing dizziness, shortness of breath, palpitations, or unintentional weight loss?"

    if stage == "ask_assoc":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        s_txt = slots.get("sleep", "sleep quality not specified")
        p_txt = slots.get("pattern", "time-of-day pattern not specified")
        d_txt = slots.get("duration", "unspecified duration")
        a_txt = ", ".join(slots.get("assoc", [])) if slots.get("assoc") else "no concerning associated symptoms reported"
        reset_state()
        return (
            f"Thanks. Summary: fatigue with {s_txt}, {p_txt}, duration {d_txt}, {a_txt}. "
            f"If you develop severe shortness of breath, chest pain, fainting, or sudden worsening, please seek urgent care."
        )

    return "Thanks—please share a bit more so I can assess properly."

# -------------- Skin/Rash flow (NEW) --------------
SKIN_LOCATIONS = {
    "face": ["face", "cheek", "chin", "nose", "forehead"],
    "scalp": ["scalp"],
    "neck": ["neck"],
    "chest": ["chest"],
    "back": ["back"],
    "abdomen": ["abdomen", "stomach", "belly", "tummy", "trunk"],
    "arm": ["arm", "upper arm"],
    "forearm": ["forearm"],
    "elbow": ["elbow"],
    "hand": ["hand", "hands", "palm", "palms"],
    "fingers": ["finger", "fingers"],
    "leg": ["leg", "legs", "calf", "calves", "thigh", "thighs"],
    "knee": ["knee", "knees"],
    "foot": ["foot", "feet", "sole", "soles"],
    "toes": ["toe", "toes"],
    "groin": ["groin", "genital", "genitals"],
    "armpit": ["armpit", "armpits", "axilla"],
    "generalized": ["all over", "whole body", "everywhere", "body"]
}
SKIN_APPEARANCE_TERMS = [
    "red","pink","purple","brown","black","flat","raised","bump","bumps","hive","hives","welts",
    "scaly","flaky","peeling","dry","oozing","pus","pustule","pustules","crust","crusting",
    "blister","blisters","vesicle","vesicles","ring","target","bullseye","central clearing"
]
SKIN_TRIGGERS = [
    "new soap","new detergent","detergent","shampoo","lotion","cream","cosmetic","makeup",
    "new medication","antibiotic","drug","penicillin","ibuprofen","paracetamol",
    "food","peanut","seafood","shellfish","prawn","strawberry","egg","milk",
    "insect bite","mosquito","midge","gnat","bee","wasp","ant bite","spider",
    "plant","grass","poison ivy","sun","heat","sweat","exercise",
    "latex","gloves","wool","nickel","jewelry","jewellery","perfume","fragrance"
]
SKIN_SYSTEMIC_FLAGS = [
    "fever","painful","very painful","swollen lips","swollen face","lip swelling","face swelling",
    "mouth sores","mouth ulcer","ulcers in mouth","eye redness","red eyes","difficulty breathing",
    "trouble breathing","breathless","short of breath","genital","genitals","widespread","whole body"
]

def extract_skin_location(text: str) -> Optional[str]:
    t = text.lower()
    for key, variants in SKIN_LOCATIONS.items():
        for v in variants:
            if v in t:
                return key
    return None

def extract_skin_appearance(text: str) -> Optional[List[str]]:
    t = text.lower()
    hits = [w for w in SKIN_APPEARANCE_TERMS if w in t]
    return list(sorted(set(hits))) if hits else None

def extract_skin_spread(text: str) -> Optional[bool]:
    t = text.lower()
    if any(p in t for p in ["spreading", "spread", "getting bigger", "expanded", "worsening"]):
        return True
    if any(p in t for p in ["not spreading", "no spread", "stable", "same size"]):
        return False
    return None

def extract_skin_triggers(text: str) -> Optional[List[str]]:
    t = text.lower()
    hits = [w for w in SKIN_TRIGGERS if w in t]
    return list(sorted(set(hits))) if hits else None

def extract_skin_systemic(text: str) -> Optional[List[str]]:
    t = text.lower()
    hits = [w for w in SKIN_SYSTEMIC_FLAGS if w in t]
    return list(sorted(set(hits))) if hits else None

def start_skin_flow():
    dialog_state["active_domain"] = "skin"
    dialog_state["stage"] = "ask_location"
    dialog_state["slots"] = {}
    return "I’m sorry you’re dealing with a skin issue. Where is the rash located (e.g., face, arms, legs, torso, hands, feet)?"

def continue_skin_flow(user_text: str) -> str:
    stage = dialog_state["stage"]
    slots = dialog_state["slots"]

    # passive extraction
    loc = extract_skin_location(user_text)
    if loc and "location" not in slots:
        slots["location"] = loc

    app = extract_skin_appearance(user_text)
    if app:
        prev = set(slots.get("appearance", []))
        slots["appearance"] = list(prev.union(app))

    dur = extract_duration(user_text)
    if dur and "duration" not in slots:
        slots["duration"] = dur

    itch = extract_severity(user_text)
    if itch and "itch_severity" not in slots:
        slots["itch_severity"] = itch

    spread = extract_skin_spread(user_text)
    if spread is not None and "spreading" not in slots:
        slots["spreading"] = spread

    trig = extract_skin_triggers(user_text)
    if trig:
        prevt = set(slots.get("triggers", []))
        slots["triggers"] = list(prevt.union(trig))

    sys = extract_skin_systemic(user_text)
    if sys:
        prevs = set(slots.get("systemic", []))
        slots["systemic"] = list(prevs.union(sys))

    # stage progression
    if stage == "ask_location":
        if "location" not in slots:
            return "Where is the rash located (e.g., face, arms, legs, torso, hands, feet)?"
        dialog_state["stage"] = "ask_appearance"
        return "What does it look like (e.g., red, raised bumps, hives, scaly, blisters, oozing, ring-shaped)?"

    if stage == "ask_appearance":
        if not slots.get("appearance"):
            return "Could you describe the appearance (red/pink, flat/raised, bumps/hives, scaly/flaky, blisters, crusting, ring-shaped)?"
        dialog_state["stage"] = "ask_duration"
        return "How long have you had this rash?"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "How long has this been present (e.g., 2 days, since this morning, 1 week)?"
        dialog_state["stage"] = "ask_itch"
        return "How itchy is it on a scale of 1 to 10?"

    if stage == "ask_itch":
        if "itch_severity" not in slots:
            return "On a scale of 1 to 10, how intense is the itch?"
        dialog_state["stage"] = "ask_spread"
        return "Is it spreading or staying about the same?"

    if stage == "ask_spread":
        if "spreading" not in slots:
            return "Is the rash spreading or staying the same?"
        dialog_state["stage"] = "ask_triggers"
        return "Have you recently started any new soap, detergent, cosmetics, medications, foods, or had insect bites/plant contact?"

    if stage == "ask_triggers":
        dialog_state["stage"] = "ask_systemic"
        return "Any of these present: fever, very painful rash, swelling of lips/face, mouth sores, red eyes, or trouble breathing?"

    if stage == "ask_systemic":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        l_txt = slots.get("location", "unspecified location")
        a_txt = ", ".join(slots.get("appearance", [])) if slots.get("appearance") else "appearance not specified"
        d_txt = slots.get("duration", "unspecified duration")
        i_txt = f"{slots.get('itch_severity')}/10 itch" if "itch_severity" in slots else "itch severity not specified"
        s_txt = "spreading" if slots.get("spreading") else ("not spreading" if "spreading" in slots else "spreading not specified")
        t_txt = ", ".join(slots.get("triggers", [])) if slots.get("triggers") else "no clear triggers noted"
        y_txt = ", ".join(slots.get("systemic", [])) if slots.get("systemic") else "no systemic red flags reported"

        reset_state()
        return (
            f"Thanks. Summary: rash on {l_txt}, {a_txt}, duration {d_txt}, {i_txt}, {s_txt}, triggers: {t_txt}, systemic: {y_txt}. "
            f"If you notice rapidly spreading rash, swelling of lips/face, breathing difficulty, high fever, "
            f"painful blisters, mouth/eye involvement, or you feel very unwell, please seek urgent care."
        )

    return "Thanks—please share a little more so I can assess it carefully."

# -------------- Classifier + Router --------------
def predict_tag(msg: str):
    tokens = tokenize(msg)
    tokens = [stem(t) for t in tokens]
    X = bag_of_words(tokens, all_words)
    X = torch.from_numpy(X).unsqueeze(0).to(device)
    with torch.no_grad():
        outputs = model(X)
        probs = torch.softmax(outputs, dim=1)
        top_p, top_i = torch.max(probs, dim=1)
        return tags[top_i.item()], top_p.item()

def canned_response_for_tag(predicted_tag: str) -> Optional[str]:
    for intent in intents_list:
        intent_tag = get_tag(intent)
        if intent_tag == predicted_tag:
            rs = get_responses(intent)
            if rs:
                return random.choice(rs)
            break
    return None

def route_message(user_text: str) -> str:
    # Continue active flow first
    domain = dialog_state["active_domain"]
    if domain == "headache":
        return continue_headache_flow(user_text)
    if domain == "fever":
        return continue_fever_flow(user_text)
    if domain == "cough":
        return continue_cough_flow(user_text)
    if domain == "stomach":
        return continue_stomach_flow(user_text)
    if domain == "fatigue":
        return continue_fatigue_flow(user_text)
    if domain == "skin":
        return continue_skin_flow(user_text)

    # Otherwise classify new message
    tag, conf = predict_tag(user_text)

    # Kick off the correct flow if it's a symptom domain via classifier
    if conf >= THRESHOLD:
        if tag in HEADACHE_INTENTS:
            return start_headache_flow()
        if tag in FEVER_INTENTS:
            return start_fever_flow()
        if tag in COUGH_INTENTS:
            return start_cough_flow()
        if tag in STOMACH_INTENTS:
            return start_stomach_flow()
        if tag in FATIGUE_INTENTS:
            return start_fatigue_flow()
        if tag in SKIN_INTENTS:
            return start_skin_flow()

        # Otherwise, serve canned response
        resp = canned_response_for_tag(tag)
        if resp:
            return resp

    # Lightweight keyword trigger for skin/rash if classifier didn't catch it
    t = user_text.lower()
    if any(k in t for k in SKIN_KEYWORDS):
        return start_skin_flow()

    return "I’m not fully sure yet—could you rephrase or add more details?"

def chat_loop():
    print("Let's chat! (type 'quit' to exit)")
    while True:
        sentence = input("You: ").strip()
        if sentence.lower() in {"quit", "exit", "q"}:
            print("Bot: Bye!")
            break
        reply = route_message(sentence)
        print(f"{bot_name}: {reply}")

if __name__ == "__main__":
    chat_loop()
