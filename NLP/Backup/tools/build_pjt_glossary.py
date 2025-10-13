# tools/build_pjt_glossary.py
from __future__ import annotations
from pathlib import Path
from urllib.parse import urljoin
import io, pandas as pd, requests
from bs4 import BeautifulSoup

OUT = Path("data/glossary_bootstrap.csv"); OUT.parent.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"}
SOURCES = {
    "lexibank": "https://lexibank.clld.org/languages/bowernpny-Pitjantjatjara",
    "asjp":     "https://asjp.clld.org/languages/PITJANTJATJARA_YANKUNTJATJARA",
    "clics":    "https://clics.clld.org/languages/bowernpny-Pitjantjatjara",
}
EN_COLS  = {"en","english","gloss","concept","gloss in source","parameter","meaning"}
PJT_COLS = {"pjt","pitjantjatjara","form","value","form in source","clics form"}

def get_html(url:str)->str:
    r=requests.get(url,headers=HEADERS,timeout=30); r.raise_for_status(); return r.text

def try_read_csv_bytes(b:bytes):
    out=[]
    for reader in (pd.read_csv, pd.read_table):
        try: out.append(reader(io.BytesIO(b)))
        except Exception: pass
    return out

def fetch_tables_from_downloads(base_url:str):
    html=get_html(base_url); soup=BeautifulSoup(html,"lxml"); dfs=[]
    for a in soup.find_all("a",href=True):
        href=a["href"].lower()
        if any(x in href for x in (".csv","format=csv","download=1","download_csv")):
            url=urljoin(base_url, a["href"])
            try:
                rb=requests.get(url,headers=HEADERS,timeout=30).content
                dfs+=try_read_csv_bytes(rb)
                print(f"[download] {url} -> {len(dfs)} total")
            except Exception as e:
                print(f"[download] fail {url}: {e}")
    return dfs

def fetch_tables_from_html(base_url:str):
    html=get_html(base_url)
    try:
        return pd.read_html(io.StringIO(html))
    except Exception:
        soup=BeautifulSoup(html,"lxml"); tables=[]
        for tbl in soup.find_all("table"):
            rows=[]; headers=[th.get_text(" ",strip=True) for th in tbl.find_all("th")]
            for tr in tbl.find_all("tr"):
                tds=[td.get_text(" ",strip=True) for td in tr.find_all("td")]
                if tds: rows.append(tds)
            if rows:
                width=max(len(r) for r in rows)
                if not headers: headers=[f"col{i}" for i in range(width)]
                headers=(headers+[f"col{i}" for i in range(100)])[:width]
                for r in rows:
                    while len(r)<width: r.append("")
                df=pd.DataFrame(rows,columns=[h.strip().lower() for h in headers])
                tables.append(df)
        return tables

def map_en_pjt(df:pd.DataFrame):
    cols=[str(c).strip().lower() for c in df.columns]
    en_idx=next((i for i,c in enumerate(cols) if c in EN_COLS),None)
    pj_idx=next((i for i,c in enumerate(cols) if c in PJT_COLS),None)
    if en_idx is not None and pj_idx is not None:
        sub=df.iloc[:,[en_idx,pj_idx]].copy(); sub.columns=["en","pjt"]; return sub
    if df.shape[1]>=2:
        cand=df.iloc[:,-2:].copy(); cand.columns=["pjt","en"]
        def score_ascii(series):
            s=" ".join(map(str, series.fillna("").tolist()))
            return sum(ch.isascii() and (ch.isalpha() or ch.isspace()) for ch in s)/max(1,len(s))
        if score_ascii(cand["en"])<score_ascii(cand["pjt"]):
            cand=cand.rename(columns={"pjt":"en","en":"pjt"})
        return cand
    return None

def clean(df:pd.DataFrame)->pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame(columns=["en","pjt"])
    df=df.dropna()
    df["en"]=df["en"].astype(str).str.strip().str.lower()
    df["pjt"]=df["pjt"].astype(str).str.strip()
    df=df[(df["en"]!="")&(df["pjt"]!="")]
    df=df.drop_duplicates(subset=["en"],keep="first")
    return df[["en","pjt"]]

def fetch_source(name,url):
    print(f"Fetching {name} …")
    dfs=[]
    try: dfs+=fetch_tables_from_downloads(url)
    except Exception as e: print("  download-scan failed:",e)
    try: dfs+=fetch_tables_from_html(url)
    except Exception as e: print("  html-parse failed:",e)
    mapped=[]
    for df in dfs:
        m=map_en_pjt(df)
        if m is not None and not m.empty: mapped.append(clean(m))
    if mapped:
        out=clean(pd.concat(mapped,ignore_index=True))
        print(f"  {name}: {len(out)} rows")
        return out
    print(f"  {name}: 0 rows")
    return pd.DataFrame(columns=["en","pjt"])

def main():
    frames=[fetch_source(k,u) for k,u in SOURCES.items()]
    merged=clean(pd.concat(frames,ignore_index=True))
    print("Rows collected:", len(merged))
    OUT.write_text(merged.to_csv(index=False),encoding="utf-8")
    print("Wrote", OUT)

if __name__=="__main__": main()
