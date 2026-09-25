from fastapi import APIRouter

from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.services.knowledge_service import knowledge_service


router = APIRouter(
    prefix="/api",
    tags=["Chat"],
)


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest) -> ChatResponse:
    result = knowledge_service.search(request.message)

    return ChatResponse(
        answer=result["answer"],
        source=result["source"],
    )
