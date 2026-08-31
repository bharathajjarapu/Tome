"""SciFact from BEIR: a public retrieval benchmark, fetched as a zip and read with the stdlib.

BEIR ships plain jsonl and tsv, so no extra dependency is needed to read it. The cache lives
outside git. Only a slice is used, so the numbers compare runs against each other rather than
against a published leaderboard.
"""

import json
import urllib.request
import zipfile
from pathlib import Path

CACHE = Path(__file__).resolve().parents[2] / ".eval-cache"
URL = "https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip"

# A slice big enough to rank meaningfully and small enough to embed on a laptop.
QUERIES = 50
CORPUS = 800


def _download() -> Path:
    folder = CACHE / "scifact"
    if not folder.exists():
        CACHE.mkdir(exist_ok=True)
        archive = CACHE / "scifact.zip"
        if not archive.exists():
            with urllib.request.urlopen(URL, timeout=120) as response:  # noqa: S310
                archive.write_bytes(response.read())
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(CACHE)
    return folder


def _lines(path: Path) -> list[dict[str, str]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def load() -> tuple[dict[str, str], list[tuple[str, set[str]]]]:
    """Return the documents to index, and each query with the document ids that answer it."""
    folder = _download()

    relevant: dict[str, set[str]] = {}
    for row in (folder / "qrels" / "test.tsv").read_text().splitlines()[1:]:
        query, document, score = row.split("\t")
        if int(score) > 0:
            relevant.setdefault(query, set()).add(document)

    queries = {row["_id"]: row["text"] for row in _lines(folder / "queries.jsonl")}
    asked = [(queries[q], docs) for q, docs in list(relevant.items())[:QUERIES] if q in queries]

    # Every document an answer needs, then unrelated ones until the corpus is the right size.
    needed = {document for _, docs in asked for document in docs}
    corpus: dict[str, str] = {}
    for row in _lines(folder / "corpus.jsonl"):
        if row["_id"] in needed or len(corpus) < CORPUS:
            corpus[row["_id"]] = f"# {row['title']}\n\n{row['text']}"
    return corpus, asked
