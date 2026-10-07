import argparse
from pathlib import Path

from .dataset import MODEL_PATH, MODEL_URL, clean, extract, qc, record, record_session
from .features import LABELS


def main():
    parser = argparse.ArgumentParser(description="Controlled RF/SVM/XGBoost posture experiment")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download-model", help="Download the identical Pose Tasks asset used offline and live")
    download.add_argument("--output", default=str(MODEL_PATH))
    r = commands.add_parser("record", help="Record one protocol-labeled webcam take")
    r.add_argument("--subject", required=True)
    r.add_argument("--posture", choices=LABELS, required=True)
    r.add_argument("--take", type=int, default=1)
    r.add_argument("--seconds", type=float, default=60)
    r.add_argument("--trim", type=float, default=5)
    r.add_argument("--camera", type=int, default=0)
    r.add_argument("--dataset", default="dataset")
    session = commands.add_parser("record-session", help="Guide a participant through all four postures and journal the session")
    session.add_argument("--subject", required=True)
    session.add_argument("--takes", type=int, default=2)
    session.add_argument("--start-take", type=int, default=1)
    session.add_argument("--seconds", type=float, default=60)
    session.add_argument("--trim", type=float, default=5)
    session.add_argument("--camera", type=int, default=0)
    session.add_argument("--dataset", default="dataset")
    session.add_argument("--model", default=str(MODEL_PATH))
    session.add_argument("--extract-after", action="store_true")
    e = commands.add_parser("extract", help="Extract traceable features from stable labeled video intervals")
    e.add_argument("--manifest", default="dataset/manifest.csv")
    e.add_argument("--model", default=str(MODEL_PATH))
    e.add_argument("--output", default="data/research")
    e.add_argument("--sample-fps", type=float, default=5)
    e.add_argument("--visibility", type=float, default=.65)
    q = commands.add_parser("qc", help="Produce skeleton samples and a review CSV")
    q.add_argument("--extraction", default="data/research")
    q.add_argument("--per-class", type=int, default=50)
    q.add_argument("--seed", type=int, default=42)
    c = commands.add_parser("clean", help="Require video/frame review before publishing training data")
    c.add_argument("--extraction", default="data/research")
    c.add_argument("--output", default="data/research/features_clean.csv")
    t = commands.add_parser("train", help="Compare all three models with subject-independent evaluation")
    t.add_argument("--data", default="data/research/features_clean.csv")
    t.add_argument("--output", default="results/experiment_01")
    t.add_argument("--mode", choices=("loso", "holdout", "pilot"), default="loso")
    t.add_argument("--split", help="Predeclared holdout subject split JSON")
    t.add_argument("--tune", action="store_true", help="Small identical-budget subject-validation parameter search")
    t.add_argument("--seed", type=int, default=42)
    s = commands.add_parser("serve", help="Serve the browser and a selected model on loopback")
    s.add_argument("--model", default="results/experiment_01/best_model.joblib")
    s.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    try:
        if args.command == "download-model":
            from urllib.request import urlopen
            import shutil
            output = Path(args.output)
            if output.exists():
                raise ValueError("model already exists; preserving the research asset")
            output.parent.mkdir(parents=True, exist_ok=True)
            temporary = output.with_suffix(".download")
            with urlopen(MODEL_URL, timeout=30) as response, temporary.open("wb") as file:
                shutil.copyfileobj(response, file)
            temporary.replace(output)
            print(f"Saved {output}")
        elif args.command == "train":
            if args.mode == "pilot":
                from .pilot import train
            else:
                from .train import train
            train(args)
        elif args.command == "serve":
            from .server import serve
            serve(args)
        else:
            {"record": record, "record-session": record_session, "extract": extract, "qc": qc, "clean": clean}[args.command](args)
    except (ValueError, OSError) as e:
        parser.exit(2, f"Error: {e}\n")


if __name__ == "__main__":
    main()
