"""Pinned memvid adapter: bounded writes, verified activation, manifest provenance."""
import hashlib
import json
import math
import os
import re
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.rag.schemas import Chunk, Evidence, RetrievalResult, RetrievalStatus, RetrievalUnavailable

PUT_BATCH = 8
DIMENSION = 1024


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_memvid():
    os.environ["MEMVID_TELEMETRY"] = "0"
    if os.environ.get("MEMVID_API_KEY"):
        raise RetrievalUnavailable()
    try:
        import memvid_sdk
        if memvid_sdk.is_telemetry_enabled():
            raise RetrievalUnavailable()
        return memvid_sdk
    except ImportError as error:
        raise RetrievalUnavailable() from error


def checked_vector(vector):
    values = [float(v) for v in vector]
    if len(values) != DIMENSION or not all(math.isfinite(v) for v in values):
        raise RetrievalUnavailable()
    if not math.isclose(sum(v * v for v in values), 1.0, abs_tol=1e-4):
        raise RetrievalUnavailable()
    return values


def checked_chunk(chunk):
    if (not chunk.text.strip() or not chunk.metadata.get("chunkId")
            or not chunk.metadata.get("documentId")
            or hashlib.sha256(chunk.text.encode()).hexdigest() != chunk.metadata.get("contentHash")):
        raise RetrievalUnavailable()
    return chunk


def _write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def publish_index(chunks, vectors, *, index_dir, index_version, embedding_model, pinned_revision):
    """Only activate after seal/reopen, exact vector count and EVERY self-top1 pass.

    Old active.json is never touched by a failed write/check. Immutable version
    files may remain for inspection; they are never used as a silent fallback.
    """
    index_dir = Path(index_dir)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", index_version):
        raise RetrievalUnavailable()
    chunks = [checked_chunk(c) for c in chunks]
    vectors = [checked_vector(v) for v in vectors]
    ids = [c.metadata["chunkId"] for c in chunks]
    if not chunks or len(chunks) != len(vectors) or len(set(ids)) != len(ids):
        raise RetrievalUnavailable()
    for c in chunks:
        if (c.metadata.get("embeddingModel"), c.metadata.get("pinnedRevision"), c.metadata.get("indexVersion")) != (
                embedding_model, pinned_revision, index_version):
            raise RetrievalUnavailable()
    index_dir.mkdir(parents=True, exist_ok=True)
    path = index_dir / (index_version + ".mv2")
    manifest_file = index_dir / (index_version + ".manifest.json")
    if path.exists() or manifest_file.exists():
        raise FileExistsError(index_version)
    sdk = load_memvid()
    mem = None
    try:
        mem = sdk.create(str(path), enable_vec=True, enable_lex=True)
        for start in range(0, len(chunks), PUT_BATCH):
            records = [{"title": c.metadata["chunkId"], "label": "synthetic-guide",
                        "text": c.text, "metadata": {}} for c in chunks[start:start+PUT_BATCH]]
            mem.put_many(records, embeddings=vectors[start:start+PUT_BATCH],
                         opts={"enable_embedding": False},
                         embedding_identity={"provider": "external", "model": embedding_model})
        mem.seal()
    except Exception as error:
        raise RetrievalUnavailable() from error
    finally:
        if mem is not None:
            mem.close()
    manifest = {"indexVersion": index_version, "file": path.name,
                "sha256": sha256_file(path), "embeddingModel": embedding_model,
                "pinnedRevision": pinned_revision, "dimension": DIMENSION, "normalization": "l2",
                "createdAt": datetime.now(timezone.utc).isoformat(),
                "chunks": [asdict(c) for c in chunks]}
    reopened = None
    try:
        reopened = sdk.use("basic", str(path), read_only=True, enable_vec=True, enable_lex=True)
        result = reopened.find("", mode="sem", k=len(chunks), query_embedding=vectors[0])
        hits = result["hits"]
        if (result.get("total_hits") != len(chunks) or len(hits) != len(chunks)
                or {h["title"] for h in hits} != set(ids)):
            raise RetrievalUnavailable()
        for chunk_id, vector in zip(ids, vectors):
            own = reopened.find("", mode="sem", k=1, query_embedding=vector)["hits"]
            if not own or own[0]["title"] != chunk_id:
                raise RetrievalUnavailable()
    except Exception as error:
        raise RetrievalUnavailable() from error
    finally:
        if reopened is not None:
            reopened.close()
    manifest["activationCheck"] = {"expected": len(chunks), "totalHits": len(hits),
                                   "selfTop1": len(chunks), "batchMaximum": PUT_BATCH}
    _write_json(manifest_file, manifest)
    pointer = {k: manifest[k] for k in ("indexVersion", "file", "sha256", "embeddingModel", "pinnedRevision", "createdAt")}
    pointer.update(manifest=manifest_file.name, manifestSha256=sha256_file(manifest_file))
    temporary = index_dir / ("active." + uuid4().hex + ".tmp")
    _write_json(temporary, pointer)
    os.replace(temporary, index_dir / "active.json")
    return manifest


class MemvidIndex:
    def __init__(self, index_dir, *, embedding_model, pinned_revision):
        self._mem = None
        directory = Path(index_dir).resolve()
        try:
            pointer = json.loads((directory / "active.json").read_text(encoding="utf-8"))
            for key in ("file", "manifest"):
                if Path(pointer[key]).name != pointer[key]:
                    raise RetrievalUnavailable()
            manifest_path = directory / pointer["manifest"]
            if sha256_file(manifest_path) != pointer["manifestSha256"]:
                raise RetrievalUnavailable()
            self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for key in ("indexVersion", "file", "sha256", "embeddingModel", "pinnedRevision", "createdAt"):
                if pointer[key] != self.manifest[key]:
                    raise RetrievalUnavailable()
            if (pointer["embeddingModel"], pointer["pinnedRevision"]) != (embedding_model, pinned_revision):
                raise RetrievalUnavailable()
            if sha256_file(directory / pointer["file"]) != pointer["sha256"]:
                raise RetrievalUnavailable()
            self.chunks = {c["metadata"]["chunkId"]: checked_chunk(Chunk(**c)) for c in self.manifest["chunks"]}
            self._mem = load_memvid().use("basic", str(directory / pointer["file"]),
                                         read_only=True, enable_vec=True, enable_lex=True)
        except Exception as error:
            raise RetrievalUnavailable() from error

    def search(self, *, mode, query="", query_vector=None):
        try:
            if mode == "vector":
                result = self._mem.find("", mode="sem", k=len(self.chunks),
                                        query_embedding=checked_vector(query_vector))
            elif mode == "lex":
                terms = lex_terms(query)
                if not terms:
                    return []
                result = self._mem.find(" OR ".join(terms), mode="lex", k=len(self.chunks))
            else:
                raise RetrievalUnavailable()
            best = {}
            for hit in result["hits"]:
                chunk = self.chunks[hit["title"]]
                evidence = Evidence(chunk.metadata["documentId"], chunk.metadata["chunkId"], float(hit["score"]))
                if not math.isfinite(evidence.score):
                    raise RetrievalUnavailable()
                old = best.get(evidence.document_id)
                if old is None or (evidence.score, evidence.chunk_id) > (old.score, old.chunk_id):
                    best[evidence.document_id] = evidence
            return sorted(best.values(), key=lambda e: (-e.score, e.document_id))
        except Exception as error:
            raise RetrievalUnavailable() from error

    def close(self):
        if self._mem is not None:
            self._mem.close()
            self._mem = None


def lex_terms(query):
    """OR baseline without case labels/masks/query operators; no morphology or RRF."""
    text = re.sub(r"\[[^\]]*\]", " ", query)
    excluded = {"CIVIL", "CRIMINAL", "FAMILY", "OTHER", "OR", "AND", "NOT"}
    return list(dict.fromkeys(term for term in re.findall(r"[^\W_]+", text, flags=re.UNICODE)
                             if len(term) >= 2 and term.upper() not in excluded))


def apply_rule(evidence, *, mode, index_version, tau_abs, tau_gap=0.0):
    if not evidence:
        status = RetrievalStatus.EMPTY
    elif evidence[0].score < tau_abs or (mode == "vector" and
            evidence[0].score - (evidence[1].score if len(evidence)>1 else 0.0) < tau_gap):
        status = RetrievalStatus.BELOW_THRESHOLD
    else:
        status = RetrievalStatus.OK
    return RetrievalResult(status, tuple(evidence[:3]) if status == RetrievalStatus.OK else (), mode, index_version)
