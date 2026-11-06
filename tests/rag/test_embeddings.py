from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from app.rag.embeddings import E5Embedder


def test_final_input_length_rejects_before_inference():
    embedder = E5Embedder.__new__(E5Embedder)
    embedder.tokenizer = SimpleNamespace(encode=lambda text:list(range(513)))
    embedder.model = SimpleNamespace(encode=Mock())
    with pytest.raises(ValueError,match="512"):
        embedder.encode(["synthetic question"],queries=True)
    embedder.model.encode.assert_not_called()


def test_nonfinite_embedding_is_not_published_as_a_vector():
    embedder = E5Embedder.__new__(E5Embedder)
    embedder.tokenizer = SimpleNamespace(encode=lambda text:[1,2,3])
    embedder.model = SimpleNamespace(encode=lambda *a,**k:np.full((1,1024),np.nan))
    with pytest.raises(ValueError,match="Invalid E5"):
        embedder.encode(["synthetic document"])
