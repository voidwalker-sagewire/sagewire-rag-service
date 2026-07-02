Absolutely. This is exactly the kind of document we should have in every service repository.


---

SageWire RAG Service

How to Use

Version: 1.0.0

Domain

https://rag.sagewire.dev


---

Purpose

The SageWire RAG Service provides shared memory for SageWire applications.

Instead of every application maintaining its own document database, applications send documents to the RAG Service. The service stores them, performs semantic search, and answers questions using the stored knowledge.


---

Typical Workflow

Document
     │
     ▼
POST /ingest
     │
     ▼
Stored in Pinecone
     │
     ▼
POST /search
     │
     ▼
Relevant Context
     │
     ▼
POST /ask
     │
     ▼
AI Answer


---

Endpoint 1

Health Check

Verify the service is online.

curl https://rag.sagewire.dev/health

Expected response

{
  "service":"sagewire-rag-service",
  "status":"ok",
  "version":"1.0.0"
}


---

Endpoint 2

Ingest

Stores a document in the shared memory.

Request

curl -X POST https://rag.sagewire.dev/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "source_id":"tractor-manual-001",
    "title":"Hydraulic Manual",
    "text":"Replace the hydraulic filter every 250 hours."
  }'

Response

{
  "ok":true,
  "chunks_ingested":1,
  "source_id":"tractor-manual-001"
}


---

Endpoint 3

Search

Find relevant stored knowledge.

Request

curl -X POST https://rag.sagewire.dev/search \
  -H "Content-Type: application/json" \
  -d '{
    "query":"hydraulic filter",
    "top_k":3
  }'

Example Response

{
  "ok":true,
  "matches":[
    {
      "title":"Hydraulic Manual",
      "text":"Replace the hydraulic filter every 250 hours."
    }
  ]
}


---

Endpoint 4

Ask

Ask a question using the stored documents.

Request

curl -X POST https://rag.sagewire.dev/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question":"When should I replace the hydraulic filter?",
    "top_k":3
  }'

Example Response

{
  "ok":true,
  "answer":"Replace the hydraulic filter every 250 hours."
}


---

How Applications Use RAG

PTT Field Logger

Store transcripts.

Conversation
↓

RAG

↓

Ask questions later


---

HerdMate

Store:

Veterinary manuals

Feed guides

SOPs

Ranch procedures


Ask:

> "What's the withdrawal time for this vaccine?"




---

Dave

Store:

Medical references

Drug labels

Research papers


Ask:

> "What dosage is recommended?"




---

AI Filing Cabinet

Store:

PDFs

Receipts

Invoices

Documents


Ask:

> "Find every invoice mentioning RFID."




---

Good Uses

Company SOPs

Equipment manuals

Veterinary references

Meeting transcripts

Field notes

Research papers

Product documentation

Training material



---

Not Intended For

The RAG Service is shared memory, not permanent archival storage.

Large files should remain in Google Drive, object storage, or another document repository. The RAG Service stores searchable knowledge extracted from those documents.


---

SageWire Philosophy

Applications stay lightweight.

Knowledge lives in shared services.

One document can be used by many applications.

Build once.

Reuse everywhere.


---

Future Roadmap

Version 1.1

PDF ingestion

DOCX ingestion

OCR integration

Image captions

Automatic chunking improvements


Version 2.0

Multi-user namespaces

Permission controls

Conversation memory

Document citations

Source highlighting

Gateway integration



---

Example Workflow

PDF
        │
        ▼
OCR Service
        │
        ▼
RAG Service
        │
        ▼
Gateway
        │
        ▼
PTT
Dave
HerdMate
AI Filing Cabinet
Future Apps


---

 I think this document should become the template for every SageWire service: Purpose → Workflow → API → Examples → Philosophy → Roadmap. That consistency will make the platform much easier for both you and others to understand.
