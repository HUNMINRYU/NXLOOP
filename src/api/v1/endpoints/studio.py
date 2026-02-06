
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.studio_service import StudioService

router = APIRouter()


# 의존성 주입 도우미
def get_studio_service():
    from config.dependencies import get_services

    return StudioService(get_services().gemini_client)


class DraftRequest(BaseModel):
    product_name: str
    product_desc: str
    hook_text: str
    style: str | None = "Cinematic"
    brand_kit: dict | None = None
    camera_movement: str | None = None
    composition: str | None = None
    lighting_mood: str | None = None


class RefineRequest(BaseModel):
    original_prompt: str
    user_feedback: str
    brand_kit: dict | None = None


@router.post("/draft")
async def create_draft(
    request: DraftRequest, service: StudioService = Depends(get_studio_service)
):
    """
    제품 정보를 바탕으로 스튜디오용 초안 프롬프트 생성
    """
    try:
        result = await service.generate_draft_prompts(
            product_name=request.product_name,
            product_desc=request.product_desc,
            hook_text=request.hook_text,
            style=request.style,
            camera_movement=request.camera_movement,
            composition=request.composition,
            lighting_mood=request.lighting_mood,
            brand_kit=request.brand_kit,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refine")
async def refine_prompt(
    request: RefineRequest, service: StudioService = Depends(get_studio_service)
):
    """
    사용자의 피드백을 반영하여 프롬프트를 실시간으로 고도화
    """
    try:
        result = await service.refine_prompt(
            original_prompt=request.original_prompt,
            user_feedback=request.user_feedback,
            brand_kit=request.brand_kit,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
