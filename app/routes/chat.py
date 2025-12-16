"""
Chat API routes.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import logging
import json

from app.models import (
    ChatRequest,
    ChatResponse,
    InvestorSearchRequest,
    InvestorSearchResponse,
    InvestorProfile,
    HealthResponse,
    ErrorResponse,
)
from app.services import ChatService, InvestorService
from app.core.exceptions import AppException
from app.core.providers import registry
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["chat"])

# Service instances (will be properly initialized via dependency injection)
_chat_service: ChatService = None
_investor_service: InvestorService = None


async def get_chat_service() -> ChatService:
    """Dependency for getting chat service."""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
        await _chat_service.initialize()
    return _chat_service


async def get_investor_service() -> InvestorService:
    """Dependency for getting investor service."""
    global _investor_service
    if _investor_service is None:
        _investor_service = InvestorService()
    return _investor_service


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Process a chat message and stream the AI response using Server-Sent Events.

    Event types:
    - start: Initial metadata with conversation_id
    - status: Status updates (e.g., searching for investors)
    - investors_found: New investors discovered
    - content_start: Response generation starting
    - content: Text chunk from AI
    - done: Final metadata with all accumulated data
    - error: Error occurred
    """
    async def generate_stream():
        try:
            async for chunk in chat_service.process_message_stream(request):
                data = json.dumps(chunk, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except Exception as e:
            logger.error(f"Stream error: {e}")
            error_data = json.dumps({"type": "error", "error": str(e)})
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={500: {"model": ErrorResponse}}
)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Process a chat message and return AI response with investor data.

    Optionally specify `model_provider` to use different LLM:
    - `gemini` (default)
    - `openai` (requires OPENAI_API_KEY)
    """
    try:
        return await chat_service.process_message(request)
    except AppException as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post(
    "/search-investors",
    response_model=InvestorSearchResponse,
    responses={500: {"model": ErrorResponse}}
)
async def search_investors(
    request: InvestorSearchRequest,
    investor_service: InvestorService = Depends(get_investor_service)
):
    """Search for investors based on sectors and location."""
    try:
        import time
        start_time = time.time()

        investors, search_results = await investor_service.find_investors(
            sectors=request.sectors,
            location=request.location,
            num_results=request.limit
        )

        processing_time = int((time.time() - start_time) * 1000)

        return InvestorSearchResponse(
            investors=investors,
            total_found=len(investors),
            search_query=" ".join(request.sectors),
            processing_time_ms=processing_time
        )
    except AppException as e:
        raise HTTPException(status_code=500, detail=e.to_dict())
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Get conversation summary and all found investors."""
    summary = chat_service.get_conversation_summary(conversation_id)

    if not summary:
        raise HTTPException(status_code=404, detail="Conversation not found")

    investors = chat_service.get_conversation_investors(conversation_id)

    return {
        "summary": summary,
        "investors": [inv.model_dump() for inv in investors]
    }


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    chat_service: ChatService = Depends(get_chat_service)
):
    """Delete a conversation from memory."""
    success = chat_service.clear_conversation(conversation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"message": "Conversation deleted successfully"}


@router.get("/conversations")
async def list_conversations():
    """List all active conversations."""
    from app.services.memory_service import get_memory_service

    memory = get_memory_service()
    return {"conversations": memory.list_conversations()}


@router.get("/providers")
async def list_providers():
    """List all available providers."""
    settings = get_settings()
    llm_providers = registry.list_providers("llm")
    search_providers = registry.list_providers("search")
    scraper_providers = registry.list_providers("scraper")

    configured_llms = [
        provider for provider in llm_providers
        if settings.is_provider_configured(provider)
    ]
    search_ready = {
        provider: bool(
            settings.google_search_api_key and settings.google_search_engine_id)
        for provider in search_providers
    }
    scraper_ready = {provider: True for provider in scraper_providers}

    return {
        "llm_providers": llm_providers,
        "configured_llm_providers": configured_llms,
        "search_providers": search_providers,
        "search_ready": search_ready,
        "scraper_providers": scraper_providers,
        "scraper_ready": scraper_ready
    }


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint with provider status."""
    from datetime import datetime

    settings = get_settings()
    providers_status = {}

    # Check LLM providers
    for provider in registry.list_providers("llm"):
        providers_status[f"llm.{provider}"] = settings.is_provider_configured(
            provider)

    # Check search providers
    for provider in registry.list_providers("search"):
        providers_status[f"search.{provider}"] = bool(
            settings.google_search_api_key and settings.google_search_engine_id
        )

    # Scraper providers (assumed available if registered)
    for provider in registry.list_providers("scraper"):
        providers_status[f"scraper.{provider}"] = True

    return HealthResponse(
        status="healthy",
        version="2.0.0",
        providers=providers_status,
        timestamp=datetime.utcnow()
    )
