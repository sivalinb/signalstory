"""Explicit operator command: create a dedicated index and upload public course excerpts."""

import os

from dotenv import load_dotenv
from pinecone import Pinecone

from signalstory.course import ROOT
from signalstory.retrieval import corpus


def main():
    load_dotenv(ROOT / ".env", override=False)
    pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])
    name = os.getenv("PINECONE_INDEX", "signalstory-lessons-v1")
    if name not in pc.list_indexes().names():
        pc.create_index_for_model(
            name=name,
            cloud="aws",
            region="us-east-1",
            embed={"model": "llama-text-embed-v2", "field_map": {"text": "text"}},
            timeout=60,
        )
    index = pc.Index(name=name)
    docs, _ = corpus()
    records = [{"_id": d["id"], "concept_id": d["id"], "text": d["text"]} for d in docs]
    for start in range(0, len(records), 40):
        index.upsert_records(namespace="lessons-v1", records=records[start : start + 40], timeout=30)
    print(f"Uploaded {len(records)} public course records to {name}/lessons-v1.")


if __name__ == "__main__":
    main()
