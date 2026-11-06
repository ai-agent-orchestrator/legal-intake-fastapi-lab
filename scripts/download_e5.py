"""Only network-enabled step: download pinned public model files, never corpus text."""
import argparse
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = "intfloat/multilingual-e5-large-instruct"
CACHE = ROOT.parent / "model-cache" / "huggingface"
PIN = ROOT / "rag-runtime" / "model.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["tokenizer", "weights"])
    args = parser.parse_args()
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["MEMVID_TELEMETRY"] = "0"
    from huggingface_hub import HfApi, snapshot_download

    if PIN.exists():
        config = json.loads(PIN.read_text(encoding="utf-8"))
        revision = config["pinnedRevision"]
    else:
        if args.phase != "tokenizer":
            raise RuntimeError("Pin and download tokenizer before weights")
        revision = HfApi().model_info(MODEL).sha
        if not revision or len(revision) != 40:
            raise RuntimeError("Expected immutable model commit SHA")
        config = {"embeddingModel": MODEL, "pinnedRevision": revision,
                  "dimension": 1024, "maxInputTokens": 512,
                  "queryInstruction": "Given a legal intake summary, retrieve relevant synthetic legal preparation guides.",
                  "source": "https://huggingface.co/" + MODEL + "/tree/" + revision}
        PIN.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    patterns = ["*.json", "sentencepiece.bpe.model"]
    if args.phase == "weights":
        patterns.append("model.safetensors")
    path = snapshot_download(MODEL, revision=revision, cache_dir=CACHE,
                             allow_patterns=patterns, max_workers=2)
    print(json.dumps({"phase": args.phase, "model": MODEL, "revision": revision,
                      "local_snapshot": path, "corpus_transmitted": False}, indent=2))


if __name__ == "__main__":
    main()
