from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.ai import (
    is_supported_speech_recognition_model,
    list_openai_compatible_models,
    load_model_profiles,
    models_for_profile_stage,
    save_model_profiles,
    test_openai_compatible_profile,
)
from app.domain.models import AdminUser
from app.models import ModelProfile, ModelProfilesResponse, ModelProfilesUpdateRequest
from app.services.auth import require_admin
from app.services.model_call_logs import clear_model_call_logs, model_call_log_detail, model_call_log_page, model_call_summary

router = APIRouter(prefix="/model-profiles", tags=["model-profiles"])


def _validate_profile(profile: ModelProfile, current: ModelProfile | None) -> None:
    if profile.model.strip() or profile.api_key.strip() or (current is not None and current.api_key.strip()):
        missing = []
        if not profile.base_url.strip():
            missing.append("接口地址")
        if not profile.model.strip():
            missing.append("模型名")
        has_key = profile.api_key.strip() or (current is not None and current.api_key.strip())
        if not has_key:
            missing.append("API Key")
        if missing:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{profile.label}：{'、'.join(missing)}必填")
        if profile.stage == "speech_recognition" and not is_supported_speech_recognition_model(profile.model):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="语音识别请选择非实时 qwen3-asr-flash；不能选择 realtime 或 filetrans 模型",
            )


def _stored_profile_with_key(stage: str) -> ModelProfile | None:
    return next((item for item in load_model_profiles(include_api_key=True) if item.stage == stage), None)


def _require_model_stage(stage: str) -> None:
    if stage not in {profile.stage for profile in load_model_profiles()}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="业务模型不存在")


@router.get("", response_model=ModelProfilesResponse)
def get_workbench_model_profiles(_admin: AdminUser = Depends(require_admin)) -> ModelProfilesResponse:
    return ModelProfilesResponse(profiles=load_model_profiles())


@router.put("", response_model=ModelProfilesResponse)
def update_workbench_model_profiles(payload: ModelProfilesUpdateRequest, _admin: AdminUser = Depends(require_admin)) -> ModelProfilesResponse:
    stored = {profile.stage: profile for profile in load_model_profiles(include_api_key=True)}
    for profile in payload.profiles:
        _validate_profile(profile, stored.get(profile.stage))
    save_model_profiles(payload.profiles)
    return ModelProfilesResponse(profiles=load_model_profiles())


@router.put("/{stage}", response_model=ModelProfile)
def update_workbench_model_profile(stage: str, payload: ModelProfile, _admin: AdminUser = Depends(require_admin)) -> ModelProfile:
    stored_rows = load_model_profiles(include_api_key=True)
    stored = {profile.stage: profile for profile in stored_rows}
    if stage not in stored or payload.stage != stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="业务模型不存在")
    _validate_profile(payload, stored[stage])
    merged = [payload if profile.stage == stage else profile for profile in stored_rows]
    save_model_profiles(merged)
    return next(profile for profile in load_model_profiles() if profile.stage == stage)


@router.get("/call-logs/summaries")
def get_all_model_call_summaries(_admin: AdminUser = Depends(require_admin)) -> dict:
    return {"items": [model_call_summary(profile.stage) for profile in load_model_profiles()]}


@router.get("/{stage}/call-logs")
def get_model_call_logs(stage: str, page: int = 1, _admin: AdminUser = Depends(require_admin)) -> dict:
    _require_model_stage(stage)
    return model_call_log_page(stage, page, 10)


@router.get("/{stage}/call-logs/{log_id}")
def get_model_call_log_detail(stage: str, log_id: str, _admin: AdminUser = Depends(require_admin)) -> dict:
    _require_model_stage(stage)
    try:
        return model_call_log_detail(stage, log_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{stage}/call-logs")
def delete_model_call_logs(stage: str, _admin: AdminUser = Depends(require_admin)) -> dict[str, int]:
    _require_model_stage(stage)
    return {"deleted": clear_model_call_logs(stage)}


@router.post("/test")
def test_workbench_model_profile(profile: ModelProfile, _admin: AdminUser = Depends(require_admin)) -> dict:
    if not profile.api_key:
        stored = _stored_profile_with_key(profile.stage)
        if stored is not None:
            profile.api_key = stored.api_key
    return test_openai_compatible_profile(profile)


@router.post("/models")
def list_workbench_profile_models(profile: ModelProfile, _admin: AdminUser = Depends(require_admin)) -> dict[str, list[str]]:
    if not profile.api_key:
        stored = _stored_profile_with_key(profile.stage)
        if stored is not None:
            profile.api_key = stored.api_key
    try:
        models = models_for_profile_stage(profile.stage, list_openai_compatible_models(profile))
        if not models:
            raise RuntimeError("当前模型列表中没有适用于音频转文案的非实时 qwen3-asr-flash 模型")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"models": models}
