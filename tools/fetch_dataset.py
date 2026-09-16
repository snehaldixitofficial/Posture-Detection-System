from pathlib import Path

from datasets import load_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "hf_posture_dataset.csv"


def download_dataset():
    print("Downloading Khubaib01/ConfiDetect-Confidence-Posture-Dataset from Hugging Face...")
    dataset = load_dataset(
        "Khubaib01/ConfiDetect-Confidence-Posture-Dataset",
        split="train",
    )
    df = dataset.to_pandas()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Dataset successfully downloaded and saved to {OUTPUT_PATH}")
    print(f"Total records: {len(df)}")
    print("Unique posture labels:", sorted(df["posture"].dropna().unique()))


if __name__ == "__main__":
    download_dataset()
