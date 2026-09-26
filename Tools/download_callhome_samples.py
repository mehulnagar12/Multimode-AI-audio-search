import os
import json
from itertools import islice

# Increase HF download timeout
os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "120"

from datasets import load_dataset, Audio


# ============================================================
# Configuration
# ============================================================

OUTPUT_DIR = "data/callhome"
NUM_SAMPLES = 10

HF_TOKEN = os.environ["HF_TOKEN"]

AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
METADATA_DIR = os.path.join(OUTPUT_DIR, "metadata")

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(METADATA_DIR, exist_ok=True)


# ============================================================
# Detect audio format from file header
# ============================================================

def detect_audio_extension(data: bytes) -> str:

    # WAV
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ".wav"

    # FLAC
    if data[:4] == b"fLaC":
        return ".flac"

    # MP3 - ID3 header
    if data[:3] == b"ID3":
        return ".mp3"

    # MP3 - frame sync
    if (
        len(data) >= 2
        and data[0] == 0xFF
        and (data[1] & 0xE0) == 0xE0
    ):
        return ".mp3"

    raise ValueError(
        f"Unknown audio format. Header: {data[:20]!r}"
    )


# ============================================================
# Load CALLHOME English
# ============================================================

print("Loading CALLHOME English dataset...")

ds = load_dataset(
    "talkbank/callhome",
    "eng",
    split="data",
    streaming=True,
    token=HF_TOKEN
)


# ============================================================
# IMPORTANT:
# Disable Hugging Face audio decoding.
#
# This avoids:
# TorchCodec -> PyTorch -> FFmpeg
#
# We want the original audio bytes.
# ============================================================

ds = ds.cast_column(
    "audio",
    Audio(decode=False)
)


print("Dataset loaded.")
print("Features:")
print(ds.features)


# ============================================================
# Download first 10 conversations
# ============================================================

for i, sample in enumerate(islice(ds, NUM_SAMPLES)):

    print(f"\nProcessing conversation {i + 1}/{NUM_SAMPLES}")

    audio = sample["audio"]

    # Original encoded audio
    audio_bytes = audio["bytes"]

    if audio_bytes is None:
        raise ValueError(
            f"No audio bytes found for conversation {i}"
        )

    # Detect actual audio format
    extension = detect_audio_extension(audio_bytes)

    filename = f"call_{i:03d}{extension}"

    audio_path = os.path.join(
        AUDIO_DIR,
        filename
    )

    metadata_path = os.path.join(
        METADATA_DIR,
        f"call_{i:03d}.json"
    )


    # ========================================================
    # Save original audio
    # ========================================================

    with open(audio_path, "wb") as f:
        f.write(audio_bytes)


    # ========================================================
    # Save diarization metadata
    # ========================================================

    metadata = {
        "source_file": filename,

        "timestamps_start":
            sample["timestamps_start"],

        "timestamps_end":
            sample["timestamps_end"],

        "speakers":
            sample["speakers"]
    }


    with open(
        metadata_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            metadata,
            f,
            indent=2,
            ensure_ascii=False
        )


    # ========================================================
    # Logging
    # ========================================================

    size_mb = len(audio_bytes) / (1024 * 1024)

    speakers = sorted(
        set(sample["speakers"])
    )

    print(f"Audio:    {audio_path}")
    print(f"Metadata: {metadata_path}")
    print(f"Format:   {extension}")
    print(f"Size:     {size_mb:.2f} MB")
    print(f"Segments: {len(sample['speakers'])}")
    print(f"Speakers: {speakers}")


# ============================================================
# Finished
# ============================================================

print("\n================================")
print("Download complete")
print("================================")

print(f"\nAudio files:")
print(AUDIO_DIR)

print(f"\nMetadata files:")
print(METADATA_DIR)