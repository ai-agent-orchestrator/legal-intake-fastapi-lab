"""Actual pinned E5, CPU-only, local files only; no fake embedding fallback."""
import time

from app.rag.corpus import CACHE, load_tokenizer, model_config, query_input


class E5Embedder:
    def __init__(self):
        import torch
        from sentence_transformers import SentenceTransformer
        torch.set_num_threads(4)
        config = model_config()
        self.tokenizer = load_tokenizer()
        self.model = SentenceTransformer(config["embeddingModel"], revision=config["pinnedRevision"],
            cache_folder=str(CACHE), device="cpu", local_files_only=True, trust_remote_code=False,
            model_kwargs={"dtype":torch.float32})
        self.model.max_seq_length = 512

    def encode(self, texts, *, queries=False, batch_size=2):
        import numpy as np
        if not 1 <= batch_size <= 2:
            raise ValueError("Batch size must be 1 or 2")
        inputs = [query_input(t) for t in texts] if queries else list(texts)
        lengths = [len(self.tokenizer.encode(text)) for text in inputs]
        if not inputs or max(lengths) > 512:
            raise ValueError("Empty input or final E5 token length exceeds 512; no silent truncation")
        started = time.perf_counter()
        matrix = self.model.encode(inputs, batch_size=batch_size, normalize_embeddings=True,
                                   convert_to_numpy=True, show_progress_bar=False)
        elapsed = time.perf_counter() - started
        if (matrix.shape != (len(inputs),1024) or not np.isfinite(matrix).all()
                or not np.allclose(np.linalg.norm(matrix,axis=1),1,atol=1e-4)):
            raise ValueError("Invalid E5 shape/finite values/normalization")
        return matrix, {"device":"cpu","dtype":"float32","batchSize":batch_size,"torchThreads":4,
                        "count":len(inputs),"dimension":1024,"maxFinalTokens":max(lengths),
                        "encodeSeconds":elapsed,"meanEmbeddingMs":1000*elapsed/len(inputs),
                        "queryInstructionApplied":queries,"normalized":True,"actualE5":True}
