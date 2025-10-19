
from flask import Flask, request, jsonify
import re, difflib

app = Flask(__name__)

# ------------------------ Vocabulary ------------------------
# Canonical PHRASES (multi-token) → (canonical_english, category)
PHRASES = {
    # ---- Fever ----
    "ayenge fever nhenhe": ("fever", "Fever"),
    "arnterre arrkayeye": ("fever", "Fever"),                 # Arrernte fever
    "feeling hot": ("feeling hot", "Fever"),
    "ayenge feeling hot arlke": ("feeling hot", "Fever"),
    "temperature high": ("high temperature", "Fever"),
    "temperature high nhenhe": ("high temperature", "Fever"),
    "i have chills": ("chills", "Fever"),
    "arrkwethe": ("chills", "Fever"),                         # Arrernte chills
    "shivering": ("shivering", "Fever"),

    # ---- Respiratory / Cough ----
    "ayenge cough nhenhe": ("cough", "Respiratory"),
    "can't stop coughing": ("coughing a lot", "Respiratory"),
    "throat itchy": ("itchy throat", "Respiratory"),
    "ayenge feel breathless akaltye": ("shortness of breath", "Respiratory"),
    "shortness of breath": ("shortness of breath", "Respiratory"),
    "chest tight": ("chest tightness", "Respiratory"),
    "arlenye cough": ("dry cough", "Respiratory"),            # Arrernte dry cough
    "akngetyeme cough": ("productive cough (with mucus)", "Respiratory"),  # Arr bring up mucus
    "akalkelhe-ileme": ("bringing up mucus", "Respiratory"),
    "wheeze": ("wheezing", "Respiratory"),
    "wheezing": ("wheezing", "Respiratory"),
    "is ngkwinhe cough arlenye": ("dry cough", "Respiratory"),

    # ---- Headache / Pain ----
    "ayenge headache nhenhe": ("headache", "Headache"),
    "head hurts": ("headache", "Headache"),
    "head pressure": ("head pressure", "Headache"),
    "ayenge migraine arlke": ("migraine", "Headache"),
    "tyerre-irreme": ("dizziness", "Headache"),               # Arrernte dizziness
    "arnterre atnyeneme": ("head pain", "Headache"),          # Arr head pain

    # ---- Digestive / Stomach ----
    "ayenge atnerte pain nhenhe": ("stomach pain", "stomachache"),
    "ayenge atnerte atnyeneme": ("stomach pain", "stomachache"),  # Arr: stomach + pain
    "atnerte atnyeneme": ("stomach pain", "stomachache"),         # Arr: stomach pain
    "stomach pain": ("stomach pain", "stomachache"),
    "stomachache": ("stomach pain", "stomachache"),
    "stomach ache": ("stomach pain", "stomachache"),
    "belly ache": ("stomach pain", "stomachache"),
    "belly pain": ("stomach pain", "stomachache"),
    "tummy ache": ("stomach pain", "stomachache"),
    "abdominal pain": ("stomach pain", "stomachache"),
    "my stomach hurts": ("stomach pain", "stomachache"),
    "stomach hurts": ("stomach pain", "stomachache"),
    "feel nauseous": ("nausea", "stomachache"),
    "naja": ("nausea", "stomachache"),                          # Arr nausea (phonetic)
    "vomiting": ("vomiting", "stomachache"),
    "abmuy aknjalhindis": ("vomiting", "stomachache"),          # phonetic Arr phrase
    "diarrhea": ("diarrhea", "stomachache"),
    "alhui ahe stool": ("loose stool", "stomachache"),
    "apollenty stool": ("watery stool", "stomachache"),
    "bloated": ("bloating", "stomachache"),
    "bloating": ("bloating", "stomachache"),
    "loss of appetite": ("loss of appetite", "stomachache"),
    "anti-weekentu a rheem": ("loss of appetite", "stomachache"),
    "alhampui los aknjalhim apatite": ("loss of appetite", "stomachache"),

    # ---- Fatigue / General Weakness ----
    "no energy": ("low energy", "Fatigue"),
    "always exhausted": ("exhaustion", "Fatigue"),
    "feeling drained": ("fatigue", "Fatigue"),
    "ayenge tired nhenhe": ("tiredness", "Fatigue"),
    "arrantherre tyerrtye": ("weakness", "Fatigue"),          # Arr weak
}

# Single WORDS (tokens) → (canonical_english, category or None)
# Include Arrernte stems from your intents and glossary.
WORDS = {
    # discourse tokens (ignored semantically)
    "ayenge": (None, None), "anwerne": (None, None), "nhenhe": (None, None),
    "arlke": (None, None), "arrule": (None, None), "akaltye": (None, None),
    "werte": (None, None), "aye": (None, None),

    # Fever
    "fever": ("fever", "Fever"),
    "arrkayeye": ("fever", "Fever"),
    "hot": ("feeling hot", "Fever"),
    "temperature": ("high temperature", "Fever"),
    "chills": ("chills", "Fever"),
    "arrkwethe": ("chills", "Fever"),
    "shivering": ("shivering", "Fever"),

    # Respiratory
    "cough": ("cough", "Respiratory"),
    "coughing": ("cough", "Respiratory"),
    "breathless": ("shortness of breath", "Respiratory"),
    "wheeze": ("wheezing", "Respiratory"),
    "wheezing": ("wheezing", "Respiratory"),
    "throat": ("throat", "Respiratory"),
    "itchy": ("itchy throat", "Respiratory"),
    "arlenye": ("dry cough", "Respiratory"),
    "akngetyeme": ("with mucus", "Respiratory"),
    "akalkelhe-ileme": ("with mucus", "Respiratory"),
    "inwenge": ("chest", "Respiratory"),

    # Headache
    "headache": ("headache", "Headache"),
    "dizzy": ("dizziness", "Headache"),
    "tyerre-irreme": ("dizziness", "Headache"),
    "migraine": ("migraine", "Headache"),
    "pressure": ("pressure", "Headache"),
    "arnterre": ("head", "Headache"),
    "atnyeneme": ("pain", "Headache"),

    # Digestive
    "stomach": ("stomach", "stomachache"),
    "stomachache": ("stomach pain", "stomachache"),
    "stomach-ache": ("stomach pain", "stomachache"),
    "bellyache": ("stomach pain", "stomachache"),
    "belly": ("stomach", "stomachache"),
    "abdominal": ("stomach", "stomachache"),
    "tummy": ("stomach", "stomachache"),
    "atnerte": ("stomach", "stomachache"),
    "atnyeneme": ("pain", None),  # Arr: pain
    "nausea": ("nausea", "stomachache"),
    "nauseous": ("nausea", "stomachache"),
    "naja": ("nausea", "stomachache"),
    "vomiting": ("vomiting", "stomachache"),
    "abmuy": ("vomit", "stomachache"),
    "aknjalhindis": ("vomiting", "stomachache"),
    "diarrhea": ("diarrhea", "stomachache"),
    "stool": ("stool", "stomachache"),
    "alhui": ("loose stool", "stomachache"),
    "apollenty": ("watery stool", "stomachache"),
    "bloating": ("bloating", "stomachache"),
    "bloated": ("bloating", "stomachache"),
    "appetite": ("loss of appetite", "stomachache"),
    "apatite": ("loss of appetite", "stomachache"),

    # Fatigue
    "tired": ("tiredness", "Fatigue"),
    "fatigue": ("fatigue", "Fatigue"),
    "exhausted": ("exhaustion", "Fatigue"),
    "drained": ("fatigue", "Fatigue"),
    "weak": ("weakness", "Fatigue"),
    "tyerrtye": ("weakness", "Fatigue"),

    # Musculoskeletal extras (used in back/arms/legs contexts)
    "apetyewarre": ("stiffness", "General"),
    "aperrne": ("swelling", "General"),
    "mpwareke": ("numbness", "General"),
}

CATEGORIES = ["Fever","Respiratory","Headache","Digestive","Fatigue","General"]

# ------------------------ Utils ------------------------
def norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s\-]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def split_chunks(text: str):
    # split on commas, semicolons, " and ", or newlines
    parts = re.split(r"(?:,|;| and |\n)", text, flags=re.IGNORECASE)
    chunks = [p.strip() for p in parts if p and p.strip()]
    return chunks if chunks else [text]

def fuzzy_match_phrase(chunk: str, cutoff=0.80):
    keys = list(PHRASES.keys())
    target = norm(chunk)
    cand = difflib.get_close_matches(target, keys, n=1, cutoff=cutoff)
    if not cand:
        return "", 0.0, None, None
    key = cand[0]
    ratio = difflib.SequenceMatcher(None, target, key).ratio()
    canon, cat = PHRASES[key]
    return key, ratio, canon, cat

def word_level(chunk: str):
    words = norm(chunk).split()
    out = []
    for w in words:
        if w in WORDS:
            canon, cat = WORDS[w]
            if canon:  # ignore discourse tokens (mapped to None)
                out.append((w, 1.0, canon, cat))
            continue
        # fuzzy token match
        cand = difflib.get_close_matches(w, list(WORDS.keys()), n=1, cutoff=0.86)
        if cand:
            canon, cat = WORDS[cand[0]]
            if canon:
                score = difflib.SequenceMatcher(None, w, cand[0]).ratio()
                out.append((w, score, canon, cat))
    return out

def dedupe_preserve(seq, key=lambda x: x):
    seen = set()
    out = []
    for item in seq:
        k = key(item)
        if k in seen:
            continue
        seen.add(k)
        out.append(item)
    return out

# ------------------------ API ------------------------
@app.post("/analyze")
def analyze():
    data = request.get_json(silent=True) or {}
    raw = data.get("text") or ""
    chunks = split_chunks(raw)

    found = []  # list of dicts: input_span, canonical, category, score
    cat_scores = {c: 0.0 for c in CATEGORIES}

    for ch in chunks:
        # phrase pass
        key, ratio, canon, cat = fuzzy_match_phrase(ch)
        if canon:
            found.append({"input_span": ch, "canonical": canon, "category": cat, "score": round(ratio,3)})
            cat_scores[cat] += ratio
        else:
            # word pass
            matches = word_level(ch)
            for token, score, canon_w, cat_w in matches:
                cat = cat_w or "General"
                found.append({"input_span": token, "canonical": canon_w, "category": cat, "score": round(score,3)})
                cat_scores[cat] += score

    # Deduplicate by canonical form while preserving first occurrence
    found = dedupe_preserve(found, key=lambda d: d["canonical"])

    # Classification: choose category with highest score (ties → stable order)
    top_cat = max(cat_scores.items(), key=lambda kv: (kv[1], CATEGORIES.index(kv[0])))[0] if any(cat_scores.values()) else None

    # Build concatenated string from canonical keywords (English)
    canon_list = [d["canonical"] for d in found]
    if not canon_list:
        concatenated = ""
    elif len(canon_list) == 1:
        concatenated = canon_list[0]
    else:
        concatenated = ", ".join(canon_list[:-1]) + f", and {canon_list[-1]}"
    
    return jsonify({
        "input": raw,
        "keywords_found": found,
        "classification": {
            "top": top_cat,
            "scores": {k: round(v,3) for k,v in cat_scores.items()}
        },
        "concatenated_string": concatenated
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
