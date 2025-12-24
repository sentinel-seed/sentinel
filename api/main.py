"""
Sentinel AI REST API

FastAPI-based REST API for Sentinel AI alignment services.

Endpoints:
    GET  /                  - API info
    GET  /health            - Health check
    GET  /seed/{level}      - Get alignment seed
    POST /validate          - Validate text through THS gates
    POST /validate/request  - Pre-validate a request
    POST /chat              - Chat with seed injection
    POST /benchmark         - Run safety benchmark

Run with:
    uvicorn api.main:app --reload
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os

from sentinelseed import Sentinel, SeedLevel
from sentinelseed.validators import THSPValidator

# Create app
app = FastAPI(
    title="Sentinel AI API",
    description="AI Alignment as a Service - The Guardian Against Machine Independence",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
sentinel = Sentinel(seed_level=SeedLevel.STANDARD)
validator = THSPValidator()


# Request/Response models
class SeedResponse(BaseModel):
    level: str
    content: str
    token_estimate: int


class ValidateRequest(BaseModel):
    text: str = Field(..., description="Text to validate", min_length=1)


class ValidateResponse(BaseModel):
    is_safe: bool
    violations: List[str]
    gates: Dict[str, Any]


class ValidateInputRequest(BaseModel):
    request: str = Field(..., description="User request to pre-validate")


class ValidateInputResponse(BaseModel):
    should_proceed: bool
    risk_level: str
    concerns: List[str]


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    seed_level: str = Field("standard", description="Seed level (minimal, standard, full)")
    provider: str = Field("openai", description="LLM provider")
    model: Optional[str] = Field(None, description="Model name")
    conversation: Optional[List[Dict[str, str]]] = Field(None, description="Conversation history")
    validate_response: bool = Field(True, description="Whether to validate response")


class ChatResponse(BaseModel):
    response: str
    model: str
    provider: str
    seed_level: str
    validation: Optional[Dict[str, Any]] = None


class BenchmarkRequest(BaseModel):
    seed_level: str = Field("standard", description="Seed level to test")
    provider: str = Field("openai", description="LLM provider")
    model: Optional[str] = Field(None, description="Model name")
    suite: str = Field("basic", description="Test suite (basic, advanced, all)")


class BenchmarkResponse(BaseModel):
    total_tests: int
    passed: int
    failed: int
    pass_rate: float
    by_category: Dict[str, Any]
    results: Optional[List[Dict[str, Any]]] = None


# Endpoints
@app.get("/")
async def root():
    """API info."""
    return {
        "name": "Sentinel AI API",
        "version": "0.1.0",
        "description": "AI Alignment as a Service",
        "documentation": "/docs",
        "endpoints": {
            "GET /seed/{level}": "Get alignment seed",
            "POST /validate": "Validate text through THS gates",
            "POST /validate/request": "Pre-validate user request",
            "POST /chat": "Chat with seed injection",
            "POST /benchmark": "Run safety benchmark",
        }
    }


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/seed/{level}", response_model=SeedResponse)
async def get_seed(level: str):
    """
    Get alignment seed content.

    Args:
        level: Seed level (minimal, standard, full)

    Returns:
        Seed content and metadata
    """
    try:
        seed_level = SeedLevel(level.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid seed level. Options: minimal, standard, full"
        )

    content = sentinel.get_seed(seed_level)

    return SeedResponse(
        level=level,
        content=content,
        token_estimate=len(content) // 4
    )


@app.post("/validate", response_model=ValidateResponse)
async def validate_text(request: ValidateRequest):
    """
    Validate text through THSP (Truth-Harm-Scope-Purpose) gates with jailbreak pre-filter.

    Use this to check if an LLM response contains problematic content.
    """
    result = validator.validate(request.text)

    return ValidateResponse(
        is_safe=result["is_safe"],
        violations=result.get("violations", []),
        gates={
            **result.get("gates", {}),
            "jailbreak_detected": result.get("jailbreak_detected", False),
        }
    )


@app.post("/validate/request", response_model=ValidateInputResponse)
async def validate_request(request: ValidateInputRequest):
    """
    Pre-validate a user request before sending to LLM.

    Checks for jailbreak attempts, harmful requests, etc.
    """
    result = sentinel.validate_request(request.request)

    return ValidateInputResponse(
        should_proceed=result["should_proceed"],
        risk_level=result["risk_level"],
        concerns=result["concerns"]
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with automatic seed injection.

    Requires API key for the specified provider
    (set OPENAI_API_KEY or ANTHROPIC_API_KEY environment variable).
    """
    try:
        # Create sentinel with requested settings
        chat_sentinel = Sentinel(
            seed_level=request.seed_level,
            provider=request.provider,
            model=request.model,
        )

        # Call chat
        result = chat_sentinel.chat(
            message=request.message,
            conversation=request.conversation,
            validate_response=request.validate_response,
        )

        return ChatResponse(
            response=result["response"],
            model=result["model"],
            provider=result["provider"],
            seed_level=result["seed_level"],
            validation=result.get("validation"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/benchmark", response_model=BenchmarkResponse)
async def run_benchmark(request: BenchmarkRequest):
    """
    Run safety benchmark against a seed.

    Note: This endpoint makes multiple API calls and may take time.
    """
    # For now, return a mock response
    # Full implementation would use benchmark_runner.py
    return BenchmarkResponse(
        total_tests=0,
        passed=0,
        failed=0,
        pass_rate=0.0,
        by_category={},
        results=None
    )


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
