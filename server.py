import os
import time
import hashlib
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone

load_dotenv()

SERVICE_NAME = "sagewire-rag-service"
SERVICE_VERSION = "1.0.0"
START_TIME = time.time()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "")
RAG_NAMESPACE = os.getenv("RAG_NAMESPACE", "sagewire-rag-v1")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

app = Flask(__name__)

openai_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
pinecone_client = Pinecone(api_key=PINECONE_API_KEY) if PINECONE_API_KEY else None
pinecone_index = pinecone_client.Index(PINECONE_INDEX_NAME) if pinecone_client and PINECONE_INDEX_NAME else None


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    text = (text or "").strip()
    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start = end - overlap
        if start <= 0 and end >= len(text):
            break
        if start >= len(text):
            break

    return chunks


def require_index():
    if not pinecone_index:
        raise RuntimeError("PINECONE_API_KEY or PINECONE_INDEX_NAME is not configured")
    return pinecone_index


def make_chunk_id(source_id, chunk_number, chunk_text_value):
    raw = f"{source_id}:{chunk_number}:{chunk_text_value}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{source_id}-{chunk_number}-{digest}"


def normalize_search_results(results):
    matches = []

    # Pinecone search() response usually exposes result["hits"].
    hits = []

    if isinstance(results, dict):
        hits = results.get("result", {}).get("hits", []) or results.get("hits", [])
    else:
        try:
            hits = results.get("result", {}).get("hits", [])
        except Exception:
            hits = []

    for hit in hits:
        fields = hit.get("fields", {}) or {}
        matches.append({
            "id": hit.get("_id") or hit.get("id"),
            "score": hit.get("_score") or hit.get("score"),
            "source_id": fields.get("source_id"),
            "title": fields.get("title"),
            "chunk_number": fields.get("chunk_number"),
            "text": fields.get("text")
        })

    return matches


@app.get("/health")
def health():
    return jsonify({
        "service": SERVICE_NAME,
        "status": "ok",
        "version": SERVICE_VERSION
    })


@app.get("/info")
def info():
    return jsonify({
        "service": SERVICE_NAME,
        "name": "SageWire RAG Service",
        "description": "Shared retrieval-augmented generation service for SageWire applications.",
        "version": SERVICE_VERSION,
        "namespace": RAG_NAMESPACE,
        "pinecone_index": PINECONE_INDEX_NAME,
        "pinecone_embedding": "llama-text-embed-v2 integrated embedding",
        "chat_model": CHAT_MODEL,
        "status": "online"
    })


@app.get("/version")
def version():
    return jsonify({
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION
    })


@app.get("/metrics")
def metrics():
    return jsonify({
        "service": SERVICE_NAME,
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "pinecone_index_configured": bool(PINECONE_INDEX_NAME),
        "namespace": RAG_NAMESPACE
    })


@app.post("/ingest")
def ingest():
    try:
        index = require_index()
        data = request.get_json(force=True)

        source_id = str(data.get("source_id") or f"source-{int(time.time())}")
        title = data.get("title") or source_id
        text = data.get("text") or ""
        metadata_extra = data.get("metadata") or {}

        chunks = chunk_text(text)

        if not chunks:
            return jsonify({"ok": False, "error": "No text provided"}), 400

        records = []

        for i, chunk in enumerate(chunks):
            record = {
                "_id": make_chunk_id(source_id, i, chunk),
                "text": chunk,
                "source_id": source_id,
                "title": title,
                "chunk_number": i,
                "created_at": utc_now()
            }

            for key, value in metadata_extra.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    record[key] = value

            records.append(record)

        # Pinecone integrated embedding index:
        # upsert_records converts the configured text field into vectors automatically.
        index.upsert_records(
            RAG_NAMESPACE,
            records
        )

        return jsonify({
            "ok": True,
            "service": SERVICE_NAME,
            "source_id": source_id,
            "title": title,
            "chunks_ingested": len(records),
            "namespace": RAG_NAMESPACE
        })

    except Exception as err:
        return jsonify({"ok": False, "error": str(err)}), 500


@app.post("/search")
def search():
    try:
        index = require_index()
        data = request.get_json(force=True)

        query = data.get("query") or ""
        top_k = int(data.get("top_k") or 5)

        if not query.strip():
            return jsonify({"ok": False, "error": "query is required"}), 400

        results = index.search(
            namespace=RAG_NAMESPACE,
            query={
                "inputs": {"text": query},
                "top_k": top_k
            },
            fields=["text", "source_id", "title", "chunk_number", "created_at"]
        )

        matches = normalize_search_results(results)

        return jsonify({
            "ok": True,
            "query": query,
            "matches": matches
        })

    except Exception as err:
        return jsonify({"ok": False, "error": str(err)}), 500


@app.post("/ask")
def ask():
    try:
        if not openai_client:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        index = require_index()
        data = request.get_json(force=True)

        question = data.get("question") or ""
        top_k = int(data.get("top_k") or 5)

        if not question.strip():
            return jsonify({"ok": False, "error": "question is required"}), 400

        results = index.search(
            namespace=RAG_NAMESPACE,
            query={
                "inputs": {"text": question},
                "top_k": top_k
            },
            fields=["text", "source_id", "title", "chunk_number", "created_at"]
        )

        matches = normalize_search_results(results)

        contexts = []
        sources = []

        for match in matches:
            if match.get("text"):
                contexts.append(match["text"])
                sources.append({
                    "id": match.get("id"),
                    "score": match.get("score"),
                    "source_id": match.get("source_id"),
                    "title": match.get("title"),
                    "chunk_number": match.get("chunk_number")
                })

        context_text = "\n\n---\n\n".join(contexts)

        answer_result = openai_client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are SageWire RAG. Answer using the provided context. "
                        "If the context does not contain the answer, say what is missing. "
                        "Be concise and practical."
                    )
                },
                {
                    "role": "user",
                    "content": f"Context:\n{context_text}\n\nQuestion:\n{question}"
                }
            ]
        )

        answer = answer_result.choices[0].message.content or ""

        return jsonify({
            "ok": True,
            "question": question,
            "answer": answer,
            "sources": sources
        })

    except Exception as err:
        return jsonify({"ok": False, "error": str(err)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5004)
