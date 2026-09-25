import uuid
from fastapi import APIRouter
from app.ai.schemas import AIRecommendationRequest
from app.services.incident_service import IncidentService
from app.utils.latency import get_tracker, clear_tracker

# NOTE: ContextBuilder and AIService are no longer invoked directly by the router.
# The production recommendation flow now routes through IncidentService, which
# delegates to the LangGraph multi-agent graph (weather -> alert -> infrastructure
# -> route -> coordinator). AIService lives inside the coordinator_node in nodes.py.
# from app.ai.context_builder import ContextBuilder   # unused - kept for compatibility
# from app.ai.ai_service import AIService              # unused - kept for compatibility
# from app.config.settings import settings

router = APIRouter(prefix="/api/ai", tags=["AI"])
_incident_service = IncidentService()


@router.post("/recommendation")
async def get_recommendation(req: AIRecommendationRequest) -> dict:
    request_id = str(uuid.uuid4())[:8]
    tracker = get_tracker(request_id)
    tracker.mark("request_received")
    print(f"[DEBUG-LATENCY] Request {request_id} started", flush=True)

    try:
        response = await _incident_service.get_recommendation(
            question=req.question,
            lat=req.lat,
            lng=req.lng,
            incident_id=req.incident_id,
            _tracker=tracker,
        )
        tracker.end("total_request", {"has_incident_id": bool(req.incident_id)})
        print(f"[DEBUG-LATENCY] Request {request_id} calling log_summary", flush=True)
        tracker.log_summary()
        print(f"[DEBUG-LATENCY] Request {request_id} log_summary done", flush=True)
        return response.model_dump()
    finally:
        print(f"[DEBUG-LATENCY] Request {request_id} clearing tracker", flush=True)
        clear_tracker(request_id)
