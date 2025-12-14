"""
Pydantic models and schemas for the application.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Role of the message sender."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class InvestorProfile(BaseModel):
    """Investor profile data model."""

    id: Optional[str] = None
    name: str
    title: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    investment_focus: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "web_search"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "title": "Partner",
                "company": "VC Fund",
                "email": "john@vcfund.com",
                "investment_focus": ["health", "ai"]
            }
        }


class SearchResult(BaseModel):
    """Web search result model."""

    title: str
    url: str
    snippet: str
    relevance_score: Optional[float] = None


class ChatMessage(BaseModel):
    """Chat message model."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Chat request from user."""

    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None
    model_provider: Optional[str] = None  # e.g., "gemini", "openai"

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()

    model_config = {
        "protected_namespaces": ()
    }


class ChatResponse(BaseModel):
    """Chat response to user."""

    message: str
    investors: List[InvestorProfile] = Field(default_factory=list)
    search_results: List[SearchResult] = Field(default_factory=list)
    conversation_id: str
    sectors_discussed: List[str] = Field(default_factory=list)
    total_investors_found: int = 0
    model_used: Optional[str] = None
    processing_time_ms: Optional[int] = None

    model_config = {
        "protected_namespaces": ()
    }


class InvestorSearchRequest(BaseModel):
    """Request to search for investors."""

    sectors: List[str] = Field(..., min_length=1)
    location: Optional[str] = None
    stage: Optional[str] = None  # e.g., "seed", "series-a"
    limit: int = Field(default=10, ge=1, le=50)


class InvestorSearchResponse(BaseModel):
    """Response for investor search."""

    investors: List[InvestorProfile]
    total_found: int
    search_query: str
    processing_time_ms: Optional[int] = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    providers: Dict[str, bool] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Invalid input",
                    "details": {}
                }
            }
        }
