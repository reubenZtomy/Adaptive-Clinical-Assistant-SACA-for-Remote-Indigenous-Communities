from faster_whisper import WhisperModel
from pathlib import Path
import os
from rich import print

# Read config (optional)
MODEL_SIZE = os.getenv("MODEL_SIZE", "medium")   # tiny, base, small, medium, large-v3
COMPUTE_TYPE = os.getenv("COMPUTE_TYPE", "float16")  # float16 works great on RTX 4060
DEVICE = os.getenv("DEVICE", "cuda")  # 'cuda' or 'cpu'

def transcribe(audio_path: str, language: str | None = None) -> str:
    model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
    segments, info = model.transcribe(
        audio_path,
        language=language,             # e.g., "en"; None lets it auto-detect
        vad_filter=True,
        beam_size=5,
        best_of=5
    )
    print(f"[bold green]Detected language:[/bold green] {info.language} (prob={info.language_probability:.2f})")
    txt = []
    for seg in segments:
        txt.append(seg.text)
    return "".join(txt).strip()

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("audio", help="Path to audio file (wav/mp3/m4a)")
    p.add_argument("--lang", default=None, help="Force language code (e.g., en)")
    args = p.parse_args()

    audio = Path(args.audio)
    if not audio.exists():
        raise SystemExit(f"Audio not found: {audio}")

    text = transcribe(str(audio), language=args.lang)
    print("\n[bold]Transcription:[/bold]\n")
    print(text)
