"""Lexical retrieval, with optional Pinecone hosted embeddings and rank fusion."""

import os
import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from .course import concepts, sources_for


def tokenize(text):
    words = re.findall(r"[a-z0-9_]+", text.lower())
    stop = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "what",
        "why",
        "how",
        "can",
        "i",
        "to",
        "of",
        "and",
        "or",
        "in",
        "it",
        "this",
        "that",
        "does",
        "do",
        "me",
        "explain",
        "please",
        "with",
    }
    return [word for word in words if word not in stop]


@lru_cache(maxsize=1)
def corpus():
    docs = []
    for c in concepts().values():
        text = "\n".join(
            [
                c["title"],
                c["definition"],
                c["explanation"],
                c["analogy"],
                c["example"],
                c["sql_connection"],
                c["remember"],
            ]
        )
        docs.append({"id": c["id"], "title": c["title"], "text": text[:6500], "sources": sources_for(c)})
    return docs, BM25Okapi([tokenize(d["text"]) for d in docs])


@lru_cache(maxsize=1)
def cloud_index():
    from pinecone import Pinecone

    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    return pc.Index(name=os.environ.get("PINECONE_INDEX", "signalstory-lessons-v1"))


def retrieve(question, concept_id=None, use_cloud=True):
    docs, index = corpus()
    scores = index.get_scores(tokenize(question))
    ranks = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:8]
    fused = {docs[i]["id"]: 1 / (60 + rank) for rank, i in enumerate(ranks, 1) if scores[i] > 0}
    mode = "BM25"
    if use_cloud and os.getenv("PINECONE_API_KEY"):
        try:
            result = cloud_index().search(
                namespace="lessons-v1",
                query={"top_k": 8, "inputs": {"text": question[:2500]}},
                fields=["concept_id"],
                timeout=6,
            )
            for rank, hit in enumerate(result.result.hits, 1):
                ident = hit.fields.get("concept_id", hit.id)
                if ident in concepts():
                    fused[ident] = fused.get(ident, 0) + 1 / (60 + rank)
            mode = "BM25 + Pinecone"
        except Exception:
            mode = "BM25 · cloud retrieval unavailable"
    if concept_id in concepts():
        fused[concept_id] = fused.get(concept_id, 0) + 0.035
    selected = sorted(fused, key=fused.get, reverse=True)[:4]
    lookup = {d["id"]: d for d in docs}
    return [lookup[ident] for ident in selected], mode
