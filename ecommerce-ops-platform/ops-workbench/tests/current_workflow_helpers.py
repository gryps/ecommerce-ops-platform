from __future__ import annotations

import uuid
import json
import io
import asyncio
from datetime import datetime as dt
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException
from starlette.datastructures import UploadFile
from sqlalchemy import inspect, select

from app.ai import load_model_profiles, models_for_profile_stage, save_model_profiles
from app.api.v1.human_workflow import (
    CopyIterationPayload,
    CopyLibraryPayload,
    CopyReviewPayload,
    ModelNarrationPayload,
    MasterNamePayload,
    ProductTagPayload,
    audio_to_copy,
    create_copy_iteration,
    create_model_voice_narration,
    continue_copy_generation,
    create_product_tag,
    create_tag_category,
    delete_copy_iteration,
    delete_human_product,
    delete_library_copy,
    delete_jianying_draft,
    delete_narration,
    delete_tag_category,
    list_global_tags,
    list_copy_iterations,
    list_copy_library,
    list_voice_catalog,
    operation_status,
    preview_model_voice,
    review_generated_copy,
    update_library_copy,
    VoicePreviewPayload,
)
from app.api.v1.image_production import (
    SourceAssetProductCreateRequest,
    create_product_from_source_assets,
    delete_image_product,
)
from app.api.v1.ai_video_production import (
    create_director_shots,
    create_generation_task,
    create_project as create_ai_video_project,
    delete_project as delete_ai_video_project,
    import_asset_from_image_production,
    list_task_events as list_ai_video_task_events,
    submit_task as submit_ai_video_task,
    upload_asset as upload_ai_video_asset,
)
from app.api.v1.operations import add_operations_product, edit_operations_product, get_operations_overview
from app.api.v1.operations.schemas import OpsProductPayload
from app.api.v1.model_profiles import update_workbench_model_profile
from app.api.v1.products import add_product, list_products
from app.api.v1.schemas import ProductCreateRequest
from app.config import settings
from app.core.database import init_workbench_schema, reset_engine_for_tests, session_scope
from app.domain.models import (
    AiVideoTaskEvent,
    CopyContent,
    CommerceImageGroup,
    CommerceImageProduct,
    CommerceImageSourceAsset,
    CommerceImageTask,
    JianyingDraft,
    MediaAsset,
    MediaAssetTag,
    MusicResource,
    NarrationAsset,
    Product,
    ShotTag,
    TagCategory,
    VoicePreviewAsset,
)
from app.main import app
from app.models import ModelProfile
from app.services.ai_video.models import GenerationTask, ImageProductionAssetImport, ProductProject
from app.services.ai_video.executor import build_video_request
from app.services.ai_video.provider_adapters import StandardSubmitResult, StandardTaskStatus
from app.services.ai_video.store import repository as ai_video_repository
from app.services.auth import (
    bootstrap_admin,
    bootstrap_status,
    change_admin_password,
    create_login_session,
    delete_login_session,
    update_admin_profile,
)
from app.services.jianying_drafts import (
    create_jianying_draft,
    detect_jianying_draft_directory,
    duplicate_jianying_draft_usage_count,
    reset_jianying_draft_duplicate_counter,
    save_jianying_draft_directory,
)
from app.services.material_classification_move import (
    ClassificationItem,
    classify_and_move_originals,
)
from app.services.model_call_logs import (
    model_call_log_detail,
    model_call_log_page,
    record_business_model_call,
)
from app.services.music_resources import (
    _ensure_audible_audio,
    _douyin_media_url,
    _douyin_media_urls,
    _douyin_video_id,
    _extract_shared_url,
    _is_douyin_url,
    delete_music_resource,
)
from app.services.operation_state import begin_operation, finish_operation
from app.services.product_library import create_product
from app.services.speech_synthesis import generate_narration_audio
from app.services.speech_recognition import recognize_narration_audio
from app.services.voice_catalog import voice_catalog_item, voice_catalog_page


@pytest.fixture
def workbench_database(tmp_path, monkeypatch):
    monkeypatch.setattr(
        settings,
        "workbench_database_url",
        f"sqlite:///{tmp_path / 'workbench.db'}",
    )
    monkeypatch.setattr(settings, "mount_roots", [tmp_path])
    monkeypatch.setattr(settings, "workspace_dir", tmp_path / "workspace")
    reset_engine_for_tests()
    init_workbench_schema()
    yield tmp_path
    reset_engine_for_tests()


def admin():
    return type("Admin", (), {"id": None})()


def awaitable(value):
    return asyncio.run(value)
