# SageWire RAG Service

Shared Retrieval-Augmented Generation service for SageWire applications.

## Purpose

SageWire RAG gives SageWire apps a shared document memory service.

Apps should not each build their own memory system. They should call one reusable RAG service.

## Version

Service Version: `1.0.0`

API Version: `v1 internal`

## Endpoints

### Identity

GET /health  
GET /info  
GET /version  
GET /metrics  

### RAG

POST /ingest  
POST /search  
POST /ask  

## Environment Variables

```txt
OPENAI_API_KEY=
PINECONE_API_KEY=
PINECONE_INDEX_NAME=
RAG_NAMESPACE=sagewire-rag-v1
EMBEDDING_MODEL=text-embedding-3-small
CHAT_MODEL=gpt-4o-mini
CHUNK_SIZE=1200
CHUNK_OVERLAP=150
