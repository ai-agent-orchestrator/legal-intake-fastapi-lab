"""Local synthetic fixtures, fixed E5 tokenizer, stable paragraph-aware chunks."""
import hashlib
import json
import re
from pathlib import Path

from app.rag.schemas import Chunk

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "rag-runtime/model.json"
CACHE = ROOT.parent / "model-cache/huggingface"
CHUNKER_VERSION = "e5-paragraph-300-overlap40-v1"
MASKING_VERSION = "synthetic-pattern-v1"
POLICY_VERSION = "synthetic-guides-v1"


def model_config():
    return json.loads(PIN.read_text(encoding="utf-8"))


def load_tokenizer():
    from transformers import AutoTokenizer
    config = model_config()
    return AutoTokenizer.from_pretrained(config["embeddingModel"],
        revision=config["pinnedRevision"], cache_dir=CACHE, local_files_only=True,
        trust_remote_code=False)


def mask_synthetic(text: str) -> str:
    """Small learning-only patterns, not a production PII safety guarantee."""
    text = re.sub(r"\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b", "[PHONE]", text)
    return re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[EMAIL]", text)


def make_query(dto: dict) -> str:
    # Never include clientName. DTO validation belongs to the fixture validator.
    return mask_synthetic("\n".join(str(dto.get(k) or "") for k in
                                   ("caseType", "coreStatement", "desiredNextStep")))


def query_input(query: str) -> str:
    return f"Instruct: {model_config()['queryInstruction']}\nQuery: {query}"


def load_guides():
    catalog = json.loads((ROOT / "fixtures/rag/guides.json").read_text(encoding="utf-8"))
    return [{**entry, "text": (ROOT / entry["file"]).read_text(encoding="utf-8")}
            for entry in catalog]


def chunk_guides(guides, tokenizer, index_version="synthetic-v1") -> list[Chunk]:
    """300 total tokens including repeated title/special tokens; overlap <=40.

    Prefer paragraph endings in the last half of the window. Offsets preserve
    source characters; do not decode truncated Korean byte fragments. Title is
    included in every chunk. Overlap is a 40-token target (boundary dependent).
    """
    config = model_config()
    chunks = {}
    for guide in guides:
        text = mask_synthetic(guide["text"])
        title = guide["title"] + "\n\n"
        offsets = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)["offset_mapping"]
        budget = 300 - len(tokenizer.encode(title)) - 2
        start = 0
        while start < len(offsets):
            end = min(start + budget, len(offsets))
            if end < len(offsets):
                low = offsets[start + budget // 2][0]
                high = offsets[end - 1][1]
                boundary = text.rfind("\n\n", low, high)
                if boundary >= low:
                    while end > start + 1 and offsets[end - 1][1] > boundary:
                        end -= 1
            body = text[offsets[start][0]:offsets[end - 1][1]]
            while len(tokenizer.encode(title + body)) > 300:
                end -= 1
                body = text[offsets[start][0]:offsets[end - 1][1]]
            content = title + body
            digest = hashlib.sha256(content.encode()).hexdigest()
            key = f"{guide['documentId']}:{guide['sourceVersion']}:{CHUNKER_VERSION}:{start}:{digest[:16]}"
            metadata = {"documentId": guide["documentId"], "chunkId": key,
                "title": guide["title"], "caseType": guide["caseType"],
                "sourceVersion": guide["sourceVersion"], "chunkerVersion": CHUNKER_VERSION,
                "embeddingModel": config["embeddingModel"], "pinnedRevision": config["pinnedRevision"],
                "indexVersion": index_version, "tokenCount": len(tokenizer.encode(content)),
                "contentHash": digest, "maskingVersion": MASKING_VERSION, "policyVersion": POLICY_VERSION}
            chunks[key] = Chunk(content, metadata)
            if end == len(offsets):
                break
            start = max(start + 1, end - 40)
    return sorted(chunks.values(), key=lambda chunk: chunk.metadata["chunkId"])
