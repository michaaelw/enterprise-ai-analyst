"""Document ingestion endpoint."""
from __future__ import annotations

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from src.models import Document
from src.api.dependencies import get_state

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["ingest"])


class IngestRequest(BaseModel):
    content: str
    source: str = ""
    metadata: dict[str, object] = {}


class IngestResponse(BaseModel):
    document_id: str
    chunks_created: int


@router.post("/ingest", response_model=IngestResponse)
async def ingest_endpoint(request: IngestRequest) -> IngestResponse:
    state = get_state()

    document = Document(content=request.content, source=request.source, metadata=request.metadata)
    chunks = await state.ingestion_pipeline.ingest(document)

    logger.info("document_ingested", document_id=str(document.id), chunks=len(chunks))

    return IngestResponse(document_id=str(document.id), chunks_created=len(chunks))
