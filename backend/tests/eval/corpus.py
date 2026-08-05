"""The evaluation corpus: real PDFs, downloaded once and cached, plus the questions they answer.

Three papers on adjacent topics, so a question about one is a plausible miss into another.
"""

import urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parents[2] / ".eval-cache"

# name -> where to fetch it. Open-access preprints, fetched at eval time, never committed.
PAPERS = {
    "attention.pdf": "https://arxiv.org/pdf/1706.03762",
    "bert.pdf": "https://arxiv.org/pdf/1810.04805",
    "rag.pdf": "https://arxiv.org/pdf/2005.11401",
}

# (question, the one paper that answers it). Written from the papers, not from our own output.
QUESTIONS = [
    ("What is the scaling factor used in scaled dot-product attention?", "attention.pdf"),
    ("How many heads does the multi-head attention layer use?", "attention.pdf"),
    ("What positional encoding function does the Transformer use?", "attention.pdf"),
    ("What BLEU score was reached on English to German translation?", "attention.pdf"),
    ("How many layers are in the encoder stack?", "attention.pdf"),
    ("What optimizer and learning rate schedule were used for training?", "attention.pdf"),
    ("What is the masked language model pre-training objective?", "bert.pdf"),
    ("What percentage of tokens are masked during pre-training?", "bert.pdf"),
    ("What is next sentence prediction?", "bert.pdf"),
    ("What GLUE score did the large model achieve?", "bert.pdf"),
    ("Which corpora were used for pre-training?", "bert.pdf"),
    ("How does the WordPiece vocabulary work?", "bert.pdf"),
    ("What is the difference between the sequence and token variants of the model?", "rag.pdf"),
    ("Which retriever is used to fetch supporting passages?", "rag.pdf"),
    ("How is the non-parametric memory built from Wikipedia?", "rag.pdf"),
    ("What open-domain question answering datasets were evaluated?", "rag.pdf"),
    ("How does marginalising over retrieved documents work?", "rag.pdf"),
    ("Can the document index be replaced without retraining?", "rag.pdf"),
]


def fetch() -> dict[str, bytes]:
    """Download the corpus once. Raises rather than let a run score an empty index."""
    CACHE.mkdir(exist_ok=True)
    papers = {}
    for name, url in PAPERS.items():
        path = CACHE / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310
                path.write_bytes(response.read())
        papers[name] = path.read_bytes()
    return papers
