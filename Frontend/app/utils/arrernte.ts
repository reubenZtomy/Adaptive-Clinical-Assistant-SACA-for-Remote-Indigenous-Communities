export type ArrernteEntry = {
  english_meaning: string;
  arrernte_word: string;
  audio_url: string | null;
};

function parseCsv(text: string): ArrernteEntry[] {
  const rows: ArrernteEntry[] = [];
  // Simple CSV parser that handles quoted fields and commas
  const lines = text.split(/\r?\n/).filter(Boolean);
  if (lines.length === 0) return rows;
  // Expect first 3 headers: english_meaning, arrernte_word, audio_url
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    const cols: string[] = [];
    let current = "";
    let inQuotes = false;
    for (let c = 0; c < line.length; c++) {
      const ch = line[c];
      if (ch === '"') {
        if (inQuotes && line[c + 1] === '"') {
          current += '"';
          c++;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (ch === ',' && !inQuotes) {
        cols.push(current);
        current = "";
      } else {
        current += ch;
      }
    }
    cols.push(current);
    const english = (cols[0] || "").trim();
    const arrernte = (cols[1] || "").trim();
    const audio = (cols[2] || "").trim();
    if (!english && !arrernte) continue;
    rows.push({ english_meaning: english.replace(/^"|"$/g, ""), arrernte_word: arrernte.replace(/^"|"$/g, ""), audio_url: audio ? audio : null });
  }
  return rows;
}

export async function loadArrernteDictionary(): Promise<ArrernteEntry[]> {
  const res = await fetch("/arrernte_audio.csv");
  const text = await res.text();
  return parseCsv(text);
}

export function findByEnglish(entries: ArrernteEntry[], keyword: string): ArrernteEntry | undefined {
  const lower = keyword.toLowerCase();
  return entries.find((e) => e.english_meaning.toLowerCase().startsWith(lower));
}

export function playAudio(url: string | null) {
  if (!url) return;
  try {
    const audio = new Audio(url);
    audio.play().catch(() => {});
  } catch {}
}


