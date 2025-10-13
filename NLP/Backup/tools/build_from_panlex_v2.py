from __future__ import annotations
from pathlib import Path
import time, requests, pandas as pd

API = "https://api.panlex.org/v2/"
HEAD = {"User-Agent": "pit-asr-bootstrap/0.1 (+local)"}

SEED_EN = [
    "hello","doctor","hospital","clinic","medicine","pain","fever","head","stomach","chest",
    "shortness of breath","cough","vomit","diarrhea","dizziness","nausea","water","food",
    "today","tomorrow","where","nearest","help","emergency","mother","father","child",
    "boy","girl","man","woman","old","young","painkiller","headache","stomach ache"
]

OUT = Path("data/glossary_panlex.csv")
OUT.parent.mkdir(parents=True, exist_ok=True)

def post(path: str, payload: dict) -> dict:
    time.sleep(0.12)
    r = requests.post(API + path, json=payload, headers=HEAD, timeout=30)
    r.raise_for_status()
    return r.json()

def get_uids(lang_code: str) -> list[str]:
    js = post("langvar", {"lang_code": lang_code, "limit": 200})
    return [lv["uid"] for lv in js.get("result", [])]

def get_expr_id(src_uid: str, word: str) -> int | None:
    # exact, then degraded
    js = post("expr", {"uid": src_uid, "txt": word})
    res = js.get("result", [])
    if not res:
        js = post("expr", {"uid": src_uid, "txt_degr": word.lower()})
        res = js.get("result", [])
        if not res:
            return None
    word_l = word.lower()
    for e in res:
        if str(e.get("txt","")).lower() == word_l:
            return e["id"]
    return res[0]["id"]

def get_translations(tgt_uid: str, expr_id: int) -> list[str]:
    js = post("expr", {"uid": tgt_uid, "trans_expr": expr_id})
    return [str(e.get("txt","")).strip() for e in js.get("result", []) if e.get("txt")]

def main():
    eng_uids = get_uids("eng")
    eng_uid = next((u for u in eng_uids if u.endswith("-000")), eng_uids[0])
    pjt_uids = get_uids("pjt")
    if not pjt_uids:
        print("No pjt varieties found in PanLex.")
        return
    print("Using ENG:", eng_uid, "PJT varieties:", len(pjt_uids))

    rows = []
    for w in SEED_EN:
        expr_id = get_expr_id(eng_uid, w)
        if not expr_id:
            print("no expr:", w); continue

        found = None
        for pjt_uid in pjt_uids:
            try:
                pjts = get_translations(pjt_uid, expr_id)
                if pjts:
                    found = pjts[0]
                    break
            except Exception:
                pass
        if found:
            rows.append({"en": w.lower().strip(), "pjt": found, "pjt_uid": pjt_uid})
        else:
            print("no trans:", w)

    df = pd.DataFrame(rows)
    if not df.empty:
        df["en"]  = df["en"].astype(str).str.strip().str.lower()
        df["pjt"] = df["pjt"].astype(str).str.strip()
        df = df[(df["en"]!="") & (df["pjt"]!="")].drop_duplicates(subset=["en"], keep="first")

    df.to_csv(OUT, index=False, encoding="utf-8")
    print(f"Wrote {OUT} with {len(df)} rows.")

if __name__ == "__main__":
    main()
