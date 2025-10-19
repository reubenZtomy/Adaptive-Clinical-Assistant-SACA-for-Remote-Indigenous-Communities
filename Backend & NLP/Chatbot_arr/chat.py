# --- Chatbot/chat.py (updated) ---

import json
import os
import random
import re
from typing import Dict, List, Optional
from pathlib import Path

try:
    import torch
except (ImportError, OSError) as e:
    print(f"Warning: PyTorch not available: {e}")
    torch = None

# -------- Arrernte ↔ English OR-style matching helpers --------
ARR_EN_SYNONYMS = {
    "werte": ["hi", "hello", "hey"],
    "anwerne": ["you", "your"],
    "ayenge": ["i", "me", "my"],
    "nhenhe": ["this", "here", "that"],
    "arnterre": ["sick", "unwell", "ill"],
    "atnerte": ["stomach", "belly", "abdomen", "tummy", "gut"],
    "inwenge": ["chest"],
    "arlenye": ["dry"],
    "akngetyeme": ["phlegm", "mucus", "productive"],
    "yenpe": ["urine", "pee"],
    "akaltye": ["please"],
    "arlke": ["okay", "ok"],
    "arrule": ["thanks", "thank you"],
    "aye": ["?", "question"],
    "fever": ["fever","temperature","hot"],
    "cough": ["cough","coughing","wheeze","wheezing"],
    "headache": ["headache","migraine","head pain","pressure in head"],
    "fatigue": ["tired","fatigue","exhausted","drained","weak"],
    "stomach": ["stomach","nausea","nauseous","vomit","diarrhea","bloated","bloat"],
    "breathless": ["shortness of breath","breathless","difficulty breathing","trouble breathing"]
}

def _norm_txt(t: str) -> str:
    import re
    t = (t or "").lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t

def expand_with_synonyms(text: str) -> str:
    # Append Arr/Eng synonyms to simulate OR checks for keyword matching.
    words = set(_norm_txt(text).split())
    extras = []
    for arr, ens in ARR_EN_SYNONYMS.items():
        if arr in words or any(w in words for w in ens):
            extras.append(arr)
            extras.extend(ens)
    return _norm_txt(text) + " " + " ".join(sorted(set(extras)))



# Support both package import (from Chatbot.chat) and running this file directly
try:
    from .model import NeuralNet
    from .nltk_utils import tokenize, bag_of_words, stem as nltk_stem
except ImportError:  # running as a script (python chat.py)
    from model import NeuralNet
    from nltk_utils import tokenize, bag_of_words, stem as nltk_stem

# ---------- Paths relative to this file ----------
PKG_DIR = Path(__file__).resolve().parent
# Allow overriding intents/model via env vars. If a custom intents is used and no model is specified,
# auto-try data_<stem>.pth, else fall back to data.pth
INTENTS_PATH = Path(os.environ.get("SWINSACA_INTENTS", str(PKG_DIR / "intents.json")))
_model_override = os.environ.get("SWINSACA_MODEL")
if _model_override:
    DATA_PATH = Path(_model_override)
else:
    stem = INTENTS_PATH.stem
    candidate = PKG_DIR / f"data_{stem}.pth"
    DATA_PATH = candidate if candidate.exists() else (PKG_DIR / "data.pth")

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

if torch is not None:
    # Force CPU-only mode to avoid CUDA DLL issues on Windows
    device = torch.device("cpu")
    # Expect a training artifact dict with sizes, vocab, tags, and model_state
    data = torch.load(str(DATA_PATH), map_location=device)
    input_size = data["input_size"]
    hidden_size = data["hidden_size"]
    output_size = data["output_size"]
    all_words = data["all_words"]
    tags = data["tags"]
else:
    device = None
    data = None
    input_size = 0
    hidden_size = 0
    output_size = 0
    all_words = []
    tags = []
if data is not None:
    model_state = data["model_state"]
    model = NeuralNet(input_size, hidden_size, output_size).to(device)
    model.load_state_dict(model_state)
    model.eval()
else:
    model = None

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
GENERAL_INTENTS  = {"General_Followup"}

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
        # Return the matched duration span (e.g., "2 days")
        return m.group(0)
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
    t = expand_with_synonyms(text).lower()
    if any(w in t for w in ["yes", "yeah", "yep", "yup", "affirmative", "i do", "i am", "have", "has"]):
        return True
    if any(w in t for w in ["no", "nope", "nah", "negative", "don't", "do not", "haven't", "hasn't"]):
        return False
    return None

# -------------- General follow-up flow (for unrecognized inputs) --------------
GENERAL_ASSOC_FLAGS = [
    "fever", "cough", "shortness of breath", "breathless", "chest pain",
    "headache", "nausea", "vomit", "vomiting", "diarrhea", "rash", "pain"
]

def start_general_flow():
    dialog_state["active_domain"] = "general"
    dialog_state["stage"] = "ask_category"
    dialog_state["slots"] = {}
    return (
        "I’m here to help. Let’s start broadly: are you having pain, fever, cough, stomach issues, skin changes, or fatigue?"
    )

def continue_general_flow(user_text: str) -> str:
    stage = dialog_state["stage"]
    slots = dialog_state["slots"]

    # Passive extraction
    sev = extract_severity(user_text)
    if sev is not None and "severity" not in slots:
        slots["severity"] = sev
    dur = extract_duration(user_text)
    if dur and "duration" not in slots:
        slots["duration"] = dur
    # crude symptom flags capture
    t = expand_with_synonyms(user_text).lower()
    assoc_hits = [w for w in GENERAL_ASSOC_FLAGS if w in t]
    if assoc_hits:
        prev = set(slots.get("assoc", []))
        slots["assoc"] = list(prev.union(assoc_hits))

    if stage == "ask_category":
        dialog_state["stage"] = "ask_location"
        return "Anwerne, Where in your body do you notice this the most? aye?"

    if stage == "ask_location":
        if user_text.strip():
            slots["location"] = user_text.strip()
        dialog_state["stage"] = "ask_severity"
        return "Anwerne, On a scale of 1 to 10, how severe is it right now? arrule."

    if stage == "ask_severity":
        if "severity" not in slots:
            return "Werte, On a scale of 1 to 10, how severe is it right now? arlke!"
        dialog_state["stage"] = "ask_duration"
        return "Nthenhe When did this begin, and is it getting better, worse, or about the same? aye?"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "Nthenhe How long has this been going on? aye?"
        dialog_state["stage"] = "ask_assoc"
        return "Anwerne, Any of these: fever, cough, nausea/vomiting, diarrhea, rash, inwenge pain, or shortness of breath? arlke!"

    if stage == "ask_assoc":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        loc_txt = slots.get("location", "unspecified location")
        sev_txt = slots.get("severity", "unspecified severity")
        dur_txt = slots.get("duration", "unspecified duration")
        assoc_txt = ", ".join(slots.get("assoc", [])) if slots.get("assoc") else "no associated symptoms reported"
        reset_state()
        return (
            f"Thanks for the details. Summary: issue at {loc_txt}, severity {sev_txt}/10, duration {dur_txt}, {assoc_txt}. "
            f"If you develop red-flag symptoms like severe chest pain, trouble breathing, confusion, fainting, or rapidly worsening symptoms, seek urgent care."
        )

    return "Nthenhe Please share a bit more so I can guide you appropriately. aye?"

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
    t = expand_with_synonyms(text).lower()
    for loc_key, variants in LOCATION_WORDS_HEAD.items():
        for v in variants:
            if v in t:
                return loc_key
    return None

def extract_assoc_head(text: str) -> Optional[List[str]]:
    t = expand_with_synonyms(text).lower()
    hits = [w for w in ASSOCIATED_HEAD_FLAGS if w in t]
    return list(sorted(set(hits))) if hits else None

def start_headache_flow():
    dialog_state["active_domain"] = "headache"
    dialog_state["stage"] = "ask_location"
    dialog_state["slots"] = {}
    # Use the same English default prompt; language-specific rendering is handled upstream
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
            return "Ayenge nhenhe, Akerte nhenhe? front / back / sides / left / right? arrule."
        dialog_state["stage"] = "ask_severity"
        return "Anwerne, Severity 1–10? arlke!"

    if stage == "ask_severity":
        if "severity" not in slots:
            return "Anwerne, Severity 1–10? aye?"
        dialog_state["stage"] = "ask_duration"
        return "Anwerne, Arleke nthakenhe? arlke!"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "Werte, Arleke nthakenhe? aye?"
        dialog_state["stage"] = "ask_assoc"
        return "Ayenge nhenhe, Nausea, light-keme sensitivity, fever, stiff neck, vision changes itne? arrule."

    if stage == "ask_assoc":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        loc_txt = slots.get("location", "unspecified location")
        sev_txt = slots.get("severity", "unspecified severity")
        dur_txt = slots.get("duration", "unspecified duration")
        assoc_txt = ", ".join(slots.get("assoc", [])) if slots.get("assoc") else "no associated red-flag symptoms reported"
        reset_state()
        return (
            f"Thanks for the details. Summary akaltye — headache arlke at {loc_txt}, severity {sev_txt}/10, duration {dur_txt}, {assoc_txt}. "
            f"Ayenge nhenhe advice akaltye: if high fever, severe neck stiffness, confusion, fainting, or vision change nhenhe — please seek urgent care arlke!"
        )

    return "Werte, Thanks—please tell me a bit more so I can assess this carefully. arrule."

# -------------- Fever flow --------------
TEMP_PAT = re.compile(r"(\d+(?:\.\d+)?)\s*(°?\s*[cf]|celsius|fahrenheit)\b", re.I)
ASSOCIATED_FEV_FLAGS = ["chills", "shiver", "shivering", "sweat", "sweating", "body ache", "aches", "sore throat", "cough"]

def extract_temperature(text: str) -> Optional[str]:
    m = TEMP_PAT.search(text)
    if m:
        val = m.group(1)
        unit = m.group(2).replace("°", "").strip().lower()
        if unit in ["celsius", "c"]:
            return f"Ayenge nhenhe, {val} C arrule."
        if unit in ["fahrenheit", "f"]:
            return f"Anwerne, {val} F arlke!"
        return f"Werte, {val} {unit.upper} arrule."
    m2 = re.search(r"\b(\d{2}(?:\.\d+)?)\b", text)
    if m2:
        try:
            n = float(m2.group(1))
            if 34 <= n <= 43:
                return f"Ayenge nhenhe, {n} C arrule."
        except Exception:
            pass
    return None

def extract_assoc_fever(text: str) -> Optional[List[str]]:
    t = expand_with_synonyms(text).lower()
    hits = [w for w in ASSOCIATED_FEV_FLAGS if w in t]
    return list(sorted(set(hits))) if hits else None

def start_fever_flow():
    dialog_state["active_domain"] = "fever"
    dialog_state["stage"] = "ask_duration"
    dialog_state["slots"] = {}
    return "Werte, I’m sorry you’re feeling unwell. How long have you had the fever? aye?"

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
            return "Anwerne, How long has the fever been present? aye?"
        dialog_state["stage"] = "ask_temp"
        return "Nthenhe Do you know your highest temperature so far? akaltye."

    if stage == "ask_temp":
        if "temperature" not in slots:
            return "Ayenge nhenhe, What’s the highest temperature you’ve measured? arlke!"
        dialog_state["stage"] = "ask_assoc"
        return "Nthenhe Are you also experiencing chills, sweating, body aches, sore ahentye, or cough? arlke!"

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

    return "Ayenge nhenhe, Thanks—please share a bit more detail so I can assess this carefully. aye?"

# -------------- Cough/Respiratory flow --------------
ASSOCIATED_RESP_RED = ["breathless", "short of breath", "shortness of breath", "difficulty breathing",
                       "chest pain", "wheezing", "blue lips", "bluish lips"]
SPUTUM_COLORS = ["clear", "white", "yellow", "green", "brown", "bloody", "red", "pink", "rust"]

def extract_cough_type(text: str) -> Optional[str]:
    t = expand_with_synonyms(text).lower()
    if "dry" in t:
        return "arlenye"
    if any(w in t for w in ["mucus", "phlegm", "wet", "productive"]):
        return "Ayenge nhenhe, productive arlke!"
    return None

def extract_sputum_color(text: str) -> Optional[str]:
    t = expand_with_synonyms(text).lower()
    for c in SPUTUM_COLORS:
        if c in t:
            return c
    return None

def extract_resp_red_flags(text: str) -> Optional[List[str]]:
    t = expand_with_synonyms(text).lower()
    hits = [w for w in ASSOCIATED_RESP_RED if w in t]
    return list(sorted(set(hits))) if hits else None

def start_cough_flow():
    dialog_state["active_domain"] = "cough"
    dialog_state["stage"] = "ask_type"
    dialog_state["slots"] = {}
    return "Werte, I see. Is your cough arlenye or producing mucus/phlegm? aye?"

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
            return "Werte, Is your cough arlenye, or are you akngetyeme up mucus/phlegm? arlke!"
        dialog_state["stage"] = "ask_duration"
        return "Anwerne, How long have you been coughing? akaltye."

    if stage == "ask_duration":
        if "duration" not in slots:
            return "Ayenge nhenhe, How long has the cough been going on? arrule."
        dialog_state["stage"] = "ask_assoc"
        return "Nthenhe Do you have any of these: shortness of breath, inwenge pain, wheezing, or bluish arrirnpirnpe? arrule."

    if stage == "ask_assoc":
        dialog_state["stage"] = "ask_sputum"
        return "Werte, If you’re producing mucus, what color is it? arrule."

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

    return "Nthenhe Thanks—please share a bit more so I can assess it carefully. arlke!"

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
    t = expand_with_synonyms(text).lower()
    for key, variants in LOC_STOMACH.items():
        for v in variants:
            if v in t:
                return key
    return None

def extract_gi_assoc(text: str) -> Optional[List[str]]:
    t = expand_with_synonyms(text).lower()
    hits = [w for w in ASSOC_GI if w in t]
    return list(sorted(set(hits))) if hits else None

def extract_food_trigger(text: str) -> Optional[bool]:
    t = expand_with_synonyms(text).lower()
    if any(p in t for p in ["after eating", "after food", "post meal", "post-meal", "after meals", "after i eat"]):
        return True
    if any(p in t for p in ["not related to food", "no relation with food", "before eating", "empty stomach"]):
        return False
    return None

def start_stomach_flow():
    dialog_state["active_domain"] = "stomach"
    dialog_state["stage"] = "ask_location"
    dialog_state["slots"] = {}
    return "Nthenhe I understand atnerte issues can be uncomfortable. Where exactly is the pain—upper, lower, right, left, or center? akaltye."

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
            return "Anwerne, Where is the pain located—upper, lower, right, left, or center? aye?"
        dialog_state["stage"] = "ask_assoc"
        return "Anwerne, Do you also have any of these: nausea, vomiting, diarrhea, alhwe in stool, black stool, bloating, or loss of appetite? arlke!"

    if stage == "ask_assoc":
        dialog_state["stage"] = "ask_duration"
        return "Werte, How long has this been going on? aye?"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "Ayenge nhenhe, For how long has this been happening? aye?"
        dialog_state["stage"] = "ask_trigger"
        return "Nthenhe Does it get worse after eating, or is it unrelated to meals? arrule."

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

    return "Nthenhe Thanks—please tell me a little more so I can assess it carefully. arlke!"

# -------------- Fatigue flow --------------
ASSOC_FATIGUE = ["dizzy", "dizziness", "shortness of breath", "breathless", "weight loss", "palpitations"]

def extract_sleep_quality(text: str) -> Optional[str]:
    t = expand_with_synonyms(text).lower()
    if any(p in t for p in ["sleep well", "sleeping well", "good sleep", "ok sleep", "fine sleep"]):
        return "Werte, sleeping well arrule."
    if any(p in t for p in ["not sleeping", "poor sleep", "bad sleep", "insomnia", "cant sleep", "can't sleep"]):
        return "Anwerne, poor sleep aye?"
    return None

def extract_time_of_day_pattern(text: str) -> Optional[str]:
    t = expand_with_synonyms(text).lower()
    if "morning" in t:
        return "Ayenge nhenhe, worse in the ingweleme akaltye."
    if "evening" in t or "night" in t:
        return "Werte, worse in the evening/night arrule."
    if "all day" in t:
        return "Anwerne, all day aye?"
    return None

def extract_assoc_fatigue(text: str) -> Optional[List[str]]:
    t = expand_with_synonyms(text).lower()
    hits = [w for w in ASSOC_FATIGUE if w in t]
    return list(sorted(set(hits))) if hits else None

def start_fatigue_flow():
    dialog_state["active_domain"] = "fatigue"
    dialog_state["stage"] = "ask_sleep"
    dialog_state["slots"] = {}
    return "Ayenge nhenhe, I’m sorry you’re feeling this way. Have you been sleeping well recently? aye?"

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
            return "Nthenhe, anwerne been sleeping well recently akaltye? arrule."
        dialog_state["stage"] = "ask_pattern"
        return "Ayenge nhenhe, do you feel this tiredness more in the ingweleme (morning), evening/night, or all day akaltye?"

    if stage == "ask_pattern":
        if "pattern" not in slots:
            return "Anwerne, tiredness worse ingweleme, night, or all day nhenhe akaltye?"
        dialog_state["stage"] = "ask_duration"
        return "Werte, how long ayenge feeling this way arlke? akaltye."

    if stage == "ask_duration":
        if "duration" not in slots:
            return "Nthenhe, for how long arrantherre felt like this nhenhe aye?"
        dialog_state["stage"] = "ask_assoc"
        return "Werte anwerne, also having dizziness, short breath, palpitations, or weight loss nhenhe akaltye?"

    if stage == "ask_assoc":
        dialog_state["stage"] = "summary"

    if stage == "summary":
        s_txt = slots.get("sleep", "sleep quality not specified")
        p_txt = slots.get("pattern", "time-of-day pattern not specified")
        d_txt = slots.get("duration", "unspecified duration")
        a_txt = ", ".join(slots.get("assoc", [])) if slots.get("assoc") else "no red-flag symptoms reported"
        reset_state()
        return (
            f"Werte anwerne, summary nhenhe — fatigue with {s_txt}, {p_txt}, duration {d_txt}, {a_txt} akaltye. "
            f"If arrantherre feel severe short breath, chest pain, fainting, or sudden worsening, please seek help arrule."
        )

    return "Anwerne, thanks — please ileme atyenge a bit more so ayenge can assess properly akaltye."


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
    t = expand_with_synonyms(text).lower()
    for key, variants in SKIN_LOCATIONS.items():
        for v in variants:
            if v in t:
                return key
    return None

def extract_skin_appearance(text: str) -> Optional[List[str]]:
    t = expand_with_synonyms(text).lower()
    hits = [w for w in SKIN_APPEARANCE_TERMS if w in t]
    return list(sorted(set(hits))) if hits else None

def extract_skin_spread(text: str) -> Optional[bool]:
    t = expand_with_synonyms(text).lower()
    if any(p in t for p in ["spreading", "spread", "getting bigger", "expanded", "worsening"]):
        return True
    if any(p in t for p in ["not spreading", "no spread", "stable", "same size"]):
        return False
    return None

def extract_skin_triggers(text: str) -> Optional[List[str]]:
    t = expand_with_synonyms(text).lower()
    hits = [w for w in SKIN_TRIGGERS if w in t]
    return list(sorted(set(hits))) if hits else None

def extract_skin_systemic(text: str) -> Optional[List[str]]:
    t = expand_with_synonyms(text).lower()
    hits = [w for w in SKIN_SYSTEMIC_FLAGS if w in t]
    return list(sorted(set(hits))) if hits else None

def start_skin_flow():
    dialog_state["active_domain"] = "skin"
    dialog_state["stage"] = "ask_location"
    dialog_state["slots"] = {}
    return "Anwerne, I’m sorry you’re dealing with a yenpe issue. Where is the rash located? arrule."

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
            return "Anwerne, Where is the rash located? aye?"
        dialog_state["stage"] = "ask_appearance"
        return "Anwerne, What does it look like? arlke!"

    if stage == "ask_appearance":
        if not slots.get("appearance"):
            return "Nthenhe Could you describe the appearance? aye?"
        dialog_state["stage"] = "ask_duration"
        return "Nthenhe How long have you had this rash? arlke!"

    if stage == "ask_duration":
        if "duration" not in slots:
            return "Ayenge nhenhe, How long has this been present? arrule."
        dialog_state["stage"] = "ask_itch"
        return "Nthenhe How itchy is it on a scale of 1 to 10? arrule."

    if stage == "ask_itch":
        if "itch_severity" not in slots:
            return "Nthenhe On a scale of 1 to 10, how intense is the itch? arrule."
        dialog_state["stage"] = "ask_spread"
        return "Nthenhe Is it spreading or staying about the same? arrule."

    if stage == "ask_spread":
        if "spreading" not in slots:
            return "Werte, Is the rash spreading or staying the same? akaltye."
        dialog_state["stage"] = "ask_triggers"
        return "Werte, Have you recently started any new soap, detergent, cosmetics, medications, foods, or had insect bites/plant contact? aye?"

    if stage == "ask_triggers":
        dialog_state["stage"] = "ask_systemic"
        return "Ayenge nhenhe, Any of these present: fever, very painful rash, swelling of arrirnpirnpe/inngirre, arrakerte sores, red alknge, or trouble breathing? arrule."

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

    return "Werte, Thanks—please share a little more so I can assess it carefully. arrule."

# -------------- Classifier + Router --------------
def predict_tag(msg: str):
    if torch is None or model is None:
        # Fallback to simple keyword matching when PyTorch is not available
        msg_lower = msg.lower()
        for intent in intents_list:
            # Check both "patterns" and "text" keys for compatibility
            patterns = intent.get("patterns", intent.get("text", []))
            for pattern in patterns:
                if pattern.lower() in msg_lower:
                    return intent.get("tag", intent.get("intent", "general")), 0.8  # Return a reasonable confidence
        return "general", 0.5  # Default fallback
    
    tokens = tokenize(msg)
    tokens = [nltk_stem(t) for t in tokens]
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
    # Fast path: simple keyword rule to ensure Arrernte greeting 'werte' maps to Greeting
    if re.match(r"^\s*werte\b", user_text.strip(), flags=re.I):
        # If not already in a flow, return a canned Greeting response
        resp = canned_response_for_tag("Greeting")
        if resp:
            return resp

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
    if domain == "general":
        return continue_general_flow(user_text)

    # Otherwise classify new message
    tag, conf = predict_tag(user_text)

    # If user only sent a number 1-10, assume it's a severity answer – start general flow
    if re.fullmatch(r"\s*(10|[1-9])\s*", user_text):
        # Seed a general flow with severity captured
        _ = start_general_flow()
        # Pre-fill severity if not set
        sev = extract_severity(user_text)
        if sev is not None:
            dialog_state["slots"]["severity"] = sev
        return continue_general_flow("")

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
        if tag in GENERAL_INTENTS:
            return start_general_flow()

        # Otherwise, serve canned response
        resp = canned_response_for_tag(tag)
        if resp:
            return resp

    # Lightweight keyword trigger for skin/rash if classifier didn't catch it
    t = expand_with_synonyms(user_text).lower()
    if any(k in t for k in SKIN_KEYWORDS):
        return start_skin_flow()

    # Low confidence → move into general follow-up flow instead of giving up
    return start_general_flow()

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
