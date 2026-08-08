from __future__ import annotations

import uuid
import json
import io
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
from app.api.v1.router import add_product, list_products, update_workbench_model_profile
from app.api.v1.schemas import ProductCreateRequest
from app.config import settings
from app.core.database import init_workbench_schema, reset_engine_for_tests, session_scope
from app.domain.models import (
    CopyContent,
    CommerceImageGroup,
    CommerceImageProduct,
    CommerceImageSourceAsset,
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


def test_openapi_exposes_only_current_workflow():
    paths = set(app.openapi()["paths"])
    assert "/api/v1/human/material-classifications" in paths
    assert "/api/v1/human/jianying-drafts" in paths
    assert "/api/v1/music-resources/upload" in paths
    assert "/api/v1/model-profiles" in paths
    assert "/api/v1/human/operation-status/{operation_id}" in paths
    assert "/api/v1/human/voice-preview" in paths
    assert "/api/v1/human/voice-catalog" in paths
    assert "/api/v1/human/voice-catalog/{sequence}" in paths
    assert "/api/v1/human/copies/audio-to-text" in paths
    assert "/api/v1/human/narrations/human-voice" not in paths
    assert "/api/v1/human/voice-options" not in paths
    retired_fragments = (
        "rough-cut",
        "material-batches",
        "candidate-segments",
        "production-mixes",
        "production-templates",
        "music-beat-schemes",
        "hot-links",
        "similarity",
        "unattended",
        "framework",
    )
    assert not [path for path in paths if any(value in path for value in retired_fragments)]


def test_tracked_operation_reports_progress_and_rejects_duplicate():
    operation_id = uuid.uuid4().hex
    begin_operation(operation_id, "copy_generation")
    assert operation_status(operation_id, _admin=admin())["status"] == "processing"
    with pytest.raises(ValueError, match="已经提交"):
        begin_operation(operation_id, "copy_generation")
    finish_operation(operation_id, "completed", "已生成 5 条候选")
    result = operation_status(operation_id, _admin=admin())
    assert result["status"] == "completed"
    assert result["detail"] == "已生成 5 条候选"


def test_qwen_audio_voice_preview_is_persisted_and_reused(workbench_database, monkeypatch):
    profile = ModelProfile(
        stage="speech_synthesis",
        label="字幕配音",
        model="qwen-audio-3.0-tts-plus",
    )
    monkeypatch.setattr(
        "app.api.v1.human_workflow.load_model_profiles", lambda: [profile]
    )
    calls = []
    def fake_generate(_text, target, **kwargs):
        calls.append(kwargs["voice"])
        assert kwargs["voice"] == "qwen-audio-3.0-tts-plus-longcanzhuyue"
        assert kwargs["business_step"] == "字幕配音音色试听"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"RIFF-preview")

    monkeypatch.setattr(
        "app.api.v1.human_workflow.generate_narration_audio", fake_generate
    )
    response = preview_model_voice(
        VoicePreviewPayload(voice_sequence=1), _admin=admin()
    )
    assert response.media_type == "audio/wav"
    assert Path(response.path).read_bytes() == b"RIFF-preview"
    second = preview_model_voice(VoicePreviewPayload(voice_sequence=1), _admin=admin())
    assert Path(second.path).read_bytes() == b"RIFF-preview"
    assert calls == ["qwen-audio-3.0-tts-plus-longcanzhuyue"]
    with session_scope() as session:
        stored = session.get(VoicePreviewAsset, 1)
        assert stored is not None and stored.audio_bytes == len(b"RIFF-preview")


def test_qwen_asr_uses_chat_completions_with_base64_audio(tmp_path, monkeypatch):
    profile = ModelProfile(
        stage="speech_recognition",
        label="音频转文案",
        base_url="https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        model="qwen3-asr-flash",
        api_key="sk-test",
    )
    monkeypatch.setattr("app.services.speech_recognition.load_model_profiles", lambda **_kwargs: [profile])
    monkeypatch.setattr("app.services.speech_recognition._prepare_asr_data_uri", lambda _path: "data:audio/mpeg;base64,SUQz")
    monkeypatch.setattr("app.services.speech_recognition.record_business_model_call", lambda **_kwargs: None)
    requests = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "识别后的文案"}}]}

    def fake_post(url, **kwargs):
        requests.append((url, kwargs))
        return Response()

    monkeypatch.setattr("app.services.speech_recognition.httpx.post", fake_post)
    source = tmp_path / "input.wav"
    source.write_bytes(b"RIFF-audio")
    result = recognize_narration_audio(source)
    assert result["text"] == "识别后的文案"
    assert requests[0][0].endswith("/compatible-mode/v1/chat/completions")
    payload = requests[0][1]["json"]
    assert payload["model"] == "qwen3-asr-flash"
    assert payload["messages"][0]["content"][0] == {
        "type": "input_audio",
        "input_audio": {"data": "data:audio/mpeg;base64,SUQz"},
    }
    assert "files" not in requests[0][1]


def test_qwen_asr_retries_provider_internal_errors(tmp_path, monkeypatch):
    profile = ModelProfile(
        stage="speech_recognition",
        label="音频转文案",
        base_url="https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        model="qwen3-asr-flash",
        api_key="sk-test",
    )
    monkeypatch.setattr("app.services.speech_recognition.load_model_profiles", lambda **_kwargs: [profile])
    monkeypatch.setattr("app.services.speech_recognition._prepare_asr_data_uri", lambda _path: "data:audio/mpeg;base64,SUQz")
    monkeypatch.setattr("app.services.speech_recognition.time.sleep", lambda _seconds: None)
    logs = []
    monkeypatch.setattr("app.services.speech_recognition.record_business_model_call", lambda **kwargs: logs.append(kwargs))
    attempts = []

    def fake_post(url, **kwargs):
        attempts.append((url, kwargs))
        if len(attempts) < 3:
            request = httpx.Request("POST", url)
            response = httpx.Response(
                500,
                request=request,
                json={
                    "error": {"message": "internal error", "code": "internal_error"},
                    "request_id": f"retry-{len(attempts)}",
                },
            )
            response.raise_for_status()
        return httpx.Response(
            200,
            request=httpx.Request("POST", url),
            json={
                "request_id": "success-3",
                "choices": [{"message": {"content": "重试后识别成功"}}],
            },
        )

    monkeypatch.setattr("app.services.speech_recognition.httpx.post", fake_post)
    source = tmp_path / "input.wav"
    source.write_bytes(b"RIFF-audio")
    result = recognize_narration_audio(source, call_id="same-operation")

    assert result["text"] == "重试后识别成功"
    assert len(attempts) == 3
    assert [item["attempt_number"] for item in logs] == [1, 2, 3]
    assert [item["success"] for item in logs] == [False, False, True]
    assert logs[0]["output_payload"]["provider_request_id"] == "retry-1"
    assert logs[-1]["output_payload"]["provider_request_id"] == "success-3"


def test_speech_recognition_model_list_excludes_incompatible_asr_protocols():
    assert models_for_profile_stage(
        "speech_recognition",
        [
            "qwen3-asr-flash-realtime",
            "qwen3-asr-flash-filetrans",
            "qwen3-asr-flash",
            "qwen3-asr-flash-2026-02-10",
            "qwen-plus",
        ],
    ) == ["qwen3-asr-flash", "qwen3-asr-flash-2026-02-10"]


def test_speech_recognition_profile_rejects_realtime_model(workbench_database):
    with pytest.raises(HTTPException) as raised:
        update_workbench_model_profile(
            "speech_recognition",
            ModelProfile(
                stage="speech_recognition",
                label="音频转文案",
                base_url="https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
                model="qwen3-asr-flash-realtime",
                api_key="sk-test",
            ),
            _admin=admin(),
        )
    assert raised.value.status_code == 422
    assert "不能选择 realtime 或 filetrans" in str(raised.value.detail)


def test_qwen_asr_rejects_realtime_model_before_request(tmp_path, monkeypatch):
    profile = ModelProfile(
        stage="speech_recognition",
        label="音频转文案",
        base_url="https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        model="qwen3-asr-flash-realtime",
        api_key="sk-test",
    )
    monkeypatch.setattr("app.services.speech_recognition.load_model_profiles", lambda **_kwargs: [profile])
    monkeypatch.setattr("app.services.speech_recognition.record_business_model_call", lambda **_kwargs: None)
    monkeypatch.setattr(
        "app.services.speech_recognition.httpx.post",
        lambda *_args, **_kwargs: pytest.fail("不应向 chat/completions 提交 realtime 模型"),
    )
    with pytest.raises(RuntimeError, match="不能使用带 realtime 或 filetrans"):
        recognize_narration_audio(tmp_path / "unused.wav")


def test_qwen_audio_synthesis_uses_workspace_tts_endpoint(tmp_path, monkeypatch):
    profile = ModelProfile(
        stage="speech_synthesis",
        label="字幕配音",
        base_url="https://workspace.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        model="qwen-audio-3.0-tts-plus",
        api_key="sk-test",
    )
    monkeypatch.setattr(
        "app.services.speech_synthesis.load_model_profiles",
        lambda include_api_key=False: [profile],
    )
    monkeypatch.setattr(
        "app.services.speech_synthesis.record_business_model_call", lambda **_: None
    )
    requests = []

    class FakeResponse:
        def __init__(self, body):
            self.body = body

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return self.body

    def fake_open(_profile, request, *, timeout):
        assert timeout == 120
        requests.append(request)
        if len(requests) == 1:
            return FakeResponse(json.dumps({"request_id": "req-1", "output": {"audio": {"url": "https://audio.example/preview.wav"}}}).encode())
        return FakeResponse(b"RIFF-workspace-audio")

    monkeypatch.setattr(
        "app.services.speech_synthesis._profile_urlopen", fake_open
    )
    target = tmp_path / "voice.wav"
    result = generate_narration_audio("试听文案", target, voice="longanlingxin")
    assert requests[0].full_url == "https://workspace.cn-beijing.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer"
    sent = json.loads(requests[0].data)
    assert sent == {"model": "qwen-audio-3.0-tts-plus", "input": {"text": "试听文案", "voice": "longanlingxin", "format": "wav", "sample_rate": 24000}}
    assert requests[1].full_url == "https://audio.example/preview.wav"
    assert target.read_bytes() == b"RIFF-workspace-audio"
    assert result["voice"] == "longanlingxin"


def test_official_voice_catalog_has_stable_sequences_and_filters():
    first = voice_catalog_item(1)
    last = voice_catalog_item(597)
    assert first and first["name"] == "龙璨竹月"
    assert first["voice"] == "qwen-audio-3.0-tts-plus-longcanzhuyue"
    assert last and last["sequence"] == 597
    page = voice_catalog_page(page=1, page_size=20)
    assert page["total"] == 597
    assert len(page["items"]) == 20
    assert page["items"][0]["sequence"] == 1
    filtered = voice_catalog_page(query="平实质朴音", gender="女")
    assert filtered["total"] >= 1
    assert all(item["gender"] == "女" for item in filtered["items"])
    assert page["genders"] == ["女", "男"]
    assert page["ages"] == sorted(page["ages"], key=int)
    assert "日常对话" in page["scenarios"]
    age_filtered = voice_catalog_page(age="6")
    assert age_filtered["total"] >= 1
    assert all(str(item["age"]) == "6" for item in age_filtered["items"])
    scenario_filtered = voice_catalog_page(scenario="日常对话")
    assert scenario_filtered["total"] >= 1
    assert all(item["scenario"] == "日常对话" for item in scenario_filtered["items"])
    assert voice_catalog_page(query="26")["total"] >= 1
    assert voice_catalog_page(query="中文")["total"] >= 1


def test_audio_to_copy_accepts_local_media_without_creating_narration(workbench_database, monkeypatch):
    prepared = workbench_database / "prepared.wav"
    prepared.write_bytes(b"RIFF-audio")
    monkeypatch.setattr(
        "app.api.v1.human_workflow.prepare_uploaded_audio",
        lambda **_kwargs: prepared,
    )
    monkeypatch.setattr(
        "app.api.v1.human_workflow.recognize_narration_audio",
        lambda *_args, **_kwargs: {"text": "识别后可修改的文案", "model": "asr-test"},
    )
    result = audio_to_copy(
        share_url="",
        media=UploadFile(filename="source.mp4", file=io.BytesIO(b"video")),
        _admin=admin(),
    )
    assert result["text"] == "识别后可修改的文案"
    with session_scope() as session:
        assert session.scalar(select(NarrationAsset)) is None


def test_model_voice_sequence_resolves_catalog_without_asr(workbench_database, monkeypatch):
    profile = ModelProfile(
        stage="speech_synthesis", label="字幕配音", model="qwen-audio-3.0-tts-plus"
    )
    monkeypatch.setattr(
        "app.api.v1.human_workflow.load_model_profiles", lambda: [profile]
    )

    def fake_generate(text, target, **kwargs):
        assert text == "第一句。第二句。"
        assert kwargs["voice"] == "qwen-audio-3.0-tts-plus-longcanzhuyue"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"RIFF-generated")
        return {"model": profile.model, "voice": kwargs["voice"], "audio_bytes": target.stat().st_size}

    monkeypatch.setattr(
        "app.api.v1.human_workflow.generate_narration_audio", fake_generate
    )
    monkeypatch.setattr(
        "app.api.v1.human_workflow.generated_subtitle_cues",
        lambda text, _path: [{"text": text, "start_seconds": 0, "end_seconds": 3}],
    )
    created = create_model_voice_narration(
        ModelNarrationPayload(approved_text="第一句。第二句。", voice_sequence=1),
        _admin=admin(),
    )
    assert created["recognized_text"] == "第一句。第二句。"
    assert created["metadata"]["voice_catalog"] == {"sequence": 1, "name": "龙璨竹月"}
    assert "recognition_model" not in created["metadata"]

    audio_path = Path(settings.workspace_dir) / "narrations" / created["id"] / "generated.wav"
    assert audio_path.is_file()
    delete_narration(created["id"], _admin=admin())
    assert not audio_path.exists()
    with session_scope() as session:
        assert session.get(NarrationAsset, created["id"]) is None


def test_auth_bootstrap_login_and_logout(workbench_database):
    with session_scope() as session:
        assert bootstrap_status(session) is False
        user = bootstrap_admin(session, "admin", "long-test-password", "管理员", "13800000000")
        user_id = user.id
        assert user.display_name == "管理员"
        assert user.phone == "13800000000"
    with session_scope() as session:
        updated = update_admin_profile(session, user_id, "运营负责人", "13900000000")
        assert updated.display_name == "运营负责人"
        assert updated.phone == "13900000000"
    with session_scope() as session:
        change_admin_password(session, user_id, "long-test-password", "longer-test-password")
    with session_scope() as session:
        user, token, auth_session = create_login_session(
            session, "admin", "longer-test-password"
        )
        assert user.id == user_id
        assert auth_session.token_hash != token
        session_id = auth_session.id
    with session_scope() as session:
        delete_login_session(session, token, user_id)
    with session_scope() as session:
        from app.domain.models import AuthSession

        assert session.get(AuthSession, session_id) is None


def test_model_profiles_only_contain_current_bailian_stages(workbench_database):
    profiles = load_model_profiles(include_api_key=True)
    assert [item.stage for item in profiles] == [
        "copywriting",
        "image_analysis",
        "image_generation",
        "speech_recognition",
        "speech_synthesis",
    ]
    profiles[0].api_key = "sk-current-test-key"
    profiles[0].model = "qwen-test"
    save_model_profiles(profiles)
    masked = load_model_profiles()
    assert masked[0].api_key == ""
    assert masked[0].has_api_key is True
    assert masked[0].api_key_mask.endswith("-key")


def test_model_profile_can_be_saved_independently(workbench_database):
    before = load_model_profiles(include_api_key=True)
    target = next(item for item in before if item.stage == "speech_recognition")
    target.base_url = "https://workspace.example/compatible-mode/v1"
    target.model = "qwen3-asr-flash"
    target.api_key = "sk-independent"
    stored = update_workbench_model_profile(target.stage, target, _admin=admin())
    assert stored.stage == "speech_recognition"
    assert stored.model == "qwen3-asr-flash"
    assert stored.api_key == ""
    after = load_model_profiles(include_api_key=True)
    assert next(item for item in after if item.stage == "copywriting").model == next(item for item in before if item.stage == "copywriting").model
    assert next(item for item in after if item.stage == "speech_synthesis").model == next(item for item in before if item.stage == "speech_synthesis").model
    assert next(item for item in after if item.stage == "speech_recognition").api_key == "sk-independent"


def test_current_schema_does_not_create_retired_tables(workbench_database):
    from app.core.database import get_engine

    tables = set(inspect(get_engine()).get_table_names())
    assert "wb_media_assets" in tables
    assert "wb_copy_contents" in tables
    assert "wb_copy_analysis_records" in tables
    assert "wb_copy_iteration_batches" in tables
    assert "wb_copy_candidates" in tables
    assert "wb_jianying_drafts" in tables
    assert "wb_voice_preview_assets" in tables
    assert not tables.intersection(
        {
            "wb_jobs",
            "wb_material_batches",
            "wb_candidate_segments",
            "wb_production_mixes",
            "wb_production_templates",
            "wb_music_beat_schemes",
            "wb_voice_presets",
            "wb_copy_generation_batches",
            "wb_title_strategies",
        }
    )


def test_product_create_rejects_normalized_duplicate_name(workbench_database):
    add_product(ProductCreateRequest(name="玉簪产品"), admin=admin())
    with pytest.raises(HTTPException) as exc_info:
        add_product(ProductCreateRequest(name=" 玉 簪 产 品 "), admin=admin())
    assert exc_info.value.status_code == 409
    assert "已存在" in str(exc_info.value.detail)


def test_human_product_delete_removes_links_without_touching_files_or_tags(
    workbench_database,
):
    original = workbench_database / "original.mp4"
    original.write_bytes(b"video")
    with session_scope() as session:
        product = create_product(session, name="待删除产品")
        category = TagCategory(name="动作", normalized_name="动作")
        session.add(category)
        session.flush()
        tag = ShotTag(name="手持", normalized_name="手持", category_id=category.id)
        asset = MediaAsset(
            product_id=product.id,
            filename=original.name,
            source_path=str(original),
            original_source_path=str(original),
        )
        session.add_all([tag, asset])
        session.flush()
        product_id, tag_id = product.id, tag.id
    delete_human_product(product_id, admin=admin())
    assert all(item.id != product_id for item in list_products(_admin=admin()))
    assert original.is_file()
    with session_scope() as session:
        assert session.get(Product, product_id).status == "deleted"
        assert session.get(MediaAsset, asset.id) is None
        assert session.get(ShotTag, tag_id) is not None


def test_global_tags_are_unique_per_category_and_category_delete_cascades(
    workbench_database,
):
    scene = create_tag_category(MasterNamePayload(name="场景"), _admin=admin())
    action = create_tag_category(MasterNamePayload(name="动作"), _admin=admin())
    scene_tag = create_product_tag(
        ProductTagPayload(category_id=scene["id"], name="展示"), _admin=admin()
    )
    action_tag = create_product_tag(
        ProductTagPayload(category_id=action["id"], name="展示"), _admin=admin()
    )
    assert scene_tag["id"] != action_tag["id"]
    assert list_global_tags(category_id=scene["id"], _admin=admin())["total"] == 1
    delete_tag_category(scene["id"], _admin=admin())
    with session_scope() as session:
        assert session.get(TagCategory, scene["id"]) is None
        assert session.get(ShotTag, scene_tag["id"]) is None
        assert session.get(ShotTag, action_tag["id"]) is not None


def test_confirmed_classification_moves_and_renames_original_video(
    workbench_database, monkeypatch
):
    source_root = workbench_database / "incoming"
    source_root.mkdir()
    source = source_root / "camera001.MP4"
    source.write_bytes(b"original-video")
    monkeypatch.setattr(
        "app.services.material_classification_move.probe_video",
        lambda _path: {"duration_seconds": 3.2, "width": 1080, "height": 1920},
    )
    with session_scope() as session:
        product = Product(name="红色发簪", status="active")
        category = TagCategory(name="动作", normalized_name="动作")
        session.add_all([product, category])
        session.flush()
        tag = ShotTag(name="手持展示", normalized_name="手持展示", category_id=category.id)
        session.add(tag)
        session.flush()
        assets = classify_and_move_originals(
            session,
            product_id=product.id,
            source_dir=str(source_root),
            items=[ClassificationItem(source_path=str(source), tag_ids=[tag.id])],
        )
        asset_id = assets[0].id
        assert assets[0].filename == "红色发簪-手持展示.mp4"
        assert session.scalar(
            select(MediaAssetTag).where(MediaAssetTag.asset_id == asset_id)
        ) is not None
    assert not source.exists()
    assert (source_root / "红色发簪" / "红色发簪-手持展示.mp4").is_file()


def test_classification_rejects_two_tags_from_same_category(workbench_database):
    source_root = workbench_database / "duplicate-category"
    source_root.mkdir()
    source = source_root / "camera001.mp4"
    source.write_bytes(b"video")
    with session_scope() as session:
        product = Product(name="同分类校验产品", status="active")
        category = TagCategory(name="场景", normalized_name="场景")
        session.add_all([product, category])
        session.flush()
        first = ShotTag(name="室内", normalized_name="室内", category_id=category.id)
        second = ShotTag(name="户外", normalized_name="户外", category_id=category.id)
        session.add_all([first, second])
        session.flush()
        with pytest.raises(ValueError, match="同一标签分类下只能选择一个标签名称"):
            classify_and_move_originals(
                session,
                product_id=product.id,
                source_dir=str(source_root),
                items=[
                    ClassificationItem(
                        source_path=str(source), tag_ids=[first.id, second.id]
                    )
                ],
            )
    assert source.is_file()


def test_copy_library_update_and_delete(workbench_database):
    with session_scope() as session:
        copy = CopyContent(
            content_text="修改前文案",
            normalized_content="修改前文案",
            source="manual",
        )
        session.add(copy)
        session.flush()
        copy_id = copy.id
    updated = update_library_copy(
        copy_id,
        CopyLibraryPayload(content="修改后文案", product_id=None),
        _admin=admin(),
    )
    assert updated["content"] == "修改后文案"
    assert [item["content"] for item in list_copy_library(_admin=admin())["items"]] == [
        "修改后文案"
    ]
    assert delete_library_copy(copy_id, _admin=admin())["deleted"] is True
    assert list_copy_library(_admin=admin())["items"] == []


def test_copy_iteration_saves_original_reviews_five_and_history_delete_preserves_library(workbench_database, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.human_workflow.analyze_and_generate_copies",
        lambda **_: {
            "language_analysis": {"language_style": "口语", "word_preference": "简洁", "emotional_tone": "真诚", "appeal_focus": "体验"},
            "audience_analysis": {"age": "25-35", "gender": "不限", "interests": "生活方式", "spending_level": "中等", "psychological_state": "希望省心"},
            "expert_role": "真实体验型短视频编导",
            "copies": [f"迭代文案{i}" for i in range(1, 6)],
        },
    )
    created = create_copy_iteration(CopyIterationPayload(reference_text="参考原文"), _admin=admin())
    assert len(created["batches"][0]["copies"]) == 5
    assert created["language_analysis"]["language_style"] == "口语"
    library = list_copy_library(_admin=admin())
    assert [item["content"] for item in library["items"]] == ["参考原文"]
    candidate = created["batches"][0]["copies"][0]
    with pytest.raises(HTTPException) as exc_info:
        review_generated_copy(
            candidate["id"], CopyReviewPayload(status="not_adopted", reason=""), admin=admin()
        )
    assert exc_info.value.status_code == 400
    review_generated_copy(candidate["id"], CopyReviewPayload(status="adopted"), admin=admin())
    for item in created["batches"][0]["copies"][1:]:
        review_generated_copy(item["id"], CopyReviewPayload(status="not_adopted", reason="表达太泛"), admin=admin())
    monkeypatch.setattr(
        "app.api.v1.human_workflow.continue_copy_iteration",
        lambda **kwargs: [f"继续文案{i}" for i in range(1, 6)]
        if any(item["reason"] == "表达太泛" for item in kwargs["reviewed_feedback"])
        else [],
    )
    continued = continue_copy_generation(created["id"], _admin=admin())
    assert len(continued["batches"]) == 2
    assert len(continued["batches"][1]["copies"]) == 5
    assert list_copy_iterations(_admin=admin())["total"] == 1
    adopted_library = next(item for item in list_copy_library(_admin=admin())["items"] if item["content"] == "迭代文案1")
    delete_library_copy(adopted_library["id"], _admin=admin())
    assert list_copy_iterations(_admin=admin())["items"][0]["batches"][0]["copies"][0]["content"] == "迭代文案1"
    delete_copy_iteration(created["id"], _admin=admin())
    assert list_copy_iterations(_admin=admin())["total"] == 0
    assert {item["content"] for item in list_copy_library(_admin=admin())["items"]} == {"参考原文"}


def test_copy_iteration_without_input_requires_adopted_library(workbench_database):
    with pytest.raises(HTTPException) as exc_info:
        create_copy_iteration(CopyIterationPayload(), _admin=admin())
    assert exc_info.value.status_code == 400
    assert "先输入一条参考文案" in str(exc_info.value.detail)


def test_model_call_log_redacts_secrets(workbench_database):
    record_business_model_call(
        stage="copywriting",
        label="文案生成",
        provider="openai_compatible",
        model="qwen-test",
        input_payload={"api_key": "sk-secret-value", "prompt": "测试"},
        output_payload={"variants": ["结果"]},
        success=True,
        duration_ms=12,
        usage={"total_tokens": 10},
        business_step="标题生成",
    )
    page = model_call_log_page("copywriting", 1, 10)
    assert page["total"] == 1
    detail = model_call_log_detail("copywriting", page["items"][0]["id"])
    assert "api_key" not in detail["input_payload"]


def test_music_ingest_rejects_silent_audio(monkeypatch, tmp_path):
    target = tmp_path / "source.wav"
    target.write_bytes(b"RIFF")
    monkeypatch.setattr(
        "app.services.music_resources.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stderr=b"max_volume: -91.0 dB", stdout=b""),
    )
    with pytest.raises(RuntimeError, match="静音"):
        _ensure_audible_audio(target)

    monkeypatch.setattr(
        "app.services.music_resources.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stderr=b"max_volume: -3.5 dB", stdout=b""),
    )
    _ensure_audible_audio(target)


def test_music_share_parser_only_accepts_trusted_douyin_media_hosts():
    document = (
        '<link href="https://www.douyin.com/video/7182928410656771365">'
        '<source src="https://v26-web.douyinvod.com/path/video/?a=1&amp;b=2">'
    )
    assert _is_douyin_url("https://v.douyin.com/example/") is True
    assert _is_douyin_url("https://example.com/video/1") is False
    assert _extract_shared_url("复制 https://v.douyin.com/example/ 打开") == (
        "https://v.douyin.com/example/"
    )
    assert _douyin_video_id(document) == "7182928410656771365"
    assert _douyin_media_url(document).startswith("https://v26-web.douyinvod.com/")
    assert _douyin_media_url('<source src="https://attacker.example/a.mp4">') == ""
    multiple = (
        '<link href="https://v1-web.douyinvod.com/placeholder.mp4">'
        '<video controls src="https://v2-web.douyinvod.com/actual-video.mp4"></video>'
        '<audio src="https://sf5-hl-cdn-tos.douyinstatic.com/obj/ies-music/background.mp3"></audio>'
    )
    assert _douyin_media_urls(multiple) == [
        "https://sf5-hl-cdn-tos.douyinstatic.com/obj/ies-music/background.mp3",
        "https://v2-web.douyinvod.com/actual-video.mp4",
        "https://v1-web.douyinvod.com/placeholder.mp4",
    ]
    assert _douyin_media_url('<img src="https://p3-dy.byteimg.com/cover/image.jpeg">') == ""


def test_music_delete_is_blocked_when_jianying_draft_references_it(
    workbench_database,
):
    with session_scope() as session:
        music = MusicResource(
            name="背景音乐", source_type="upload", rights_confirmed=True, status="ready"
        )
        session.add(music)
        session.flush()
        session.add(
            JianyingDraft(
                name="历史草稿",
                music_resource_id=music.id,
                status="ready",
            )
        )
        session.flush()
        with pytest.raises(ValueError, match="剪映草稿引用"):
            delete_music_resource(session, music.id)


def test_jianying_draft_writes_video_free_directory_and_increments_name(
    workbench_database,
    monkeypatch,
):
    destination = workbench_database / "jianying-drafts"
    destination.mkdir()
    narration_audio = workbench_database / "narration.wav"
    narration_audio.write_bytes(b"narration")
    music_audio = workbench_database / "music.wav"
    music_audio.write_bytes(b"music")
    class FixedDateTime:
        @classmethod
        def now(cls):
            return dt(2026, 8, 3, 12, 34, 56)
    monkeypatch.setattr("app.services.jianying_drafts.datetime", FixedDateTime)
    with session_scope() as session:
        copy = CopyContent(
            content_text="草稿文案",
            normalized_content="草稿文案",
            source="manual",
        )
        narration = NarrationAsset(
            approved_text="第一句。第二句。",
            status="approved",
            audio_path=str(narration_audio),
            metadata_json={"duration_seconds": 3.0},
            subtitle_cues=[
                {"text": "第一句", "start_seconds": 0, "end_seconds": 1.5},
                {"text": "第二句", "start_seconds": 1.5, "end_seconds": 3.0},
            ],
        )
        music = MusicResource(
            name="背景音乐",
            source_type="upload",
            rights_confirmed=True,
            status="ready",
            file_path=str(music_audio),
            duration_seconds=4.0,
        )
        session.add_all([copy, narration, music])
        session.flush()
        draft = create_jianying_draft(
            session,
            name="可用草稿",
            destination_dir=str(destination),
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
            created_by=None,
        )
        draft_path = Path(draft.draft_path)
        assert draft_path.name == "可用草稿-20260803-123456"
        assert draft.snapshot["copy"]["text"] == "草稿文案"
        assert draft.snapshot["duration_microseconds"] == 4_000_000
        assert draft.snapshot["duplicate_usage_count_before_create"] == 0
        content = json.loads((draft_path / "draft_content.json").read_text(encoding="utf-8"))
        assert content["materials"]["videos"] == []
        assert all(not track["segments"] for track in content["tracks"] if track["type"] == "video")
        assert content["duration"] == 4_000_000
        assert (draft_path / "assets" / "audio").is_dir()
        text_tracks = [track for track in content["tracks"] if track["type"] == "text"]
        assert len(text_tracks) == 2
        copy_segments = [
            segment
            for track in text_tracks
            for segment in track["segments"]
            if segment["role"] == "copy"
        ]
        subtitle_segments = [
            segment
            for track in text_tracks
            for segment in track["segments"]
            if segment["role"] == "subtitle"
        ]
        assert copy_segments[0]["target_timerange"] == {"start": 0, "duration": 3_000_000}
        assert [segment["target_timerange"]["duration"] for segment in subtitle_segments] == [1_500_000, 1_500_000]
        assert not any(
            any(segment["role"] == "copy" for segment in track["segments"])
            and any(segment["role"] == "subtitle" for segment in track["segments"])
            for track in text_tracks
        )
        music_segments = [
            segment
            for track in content["tracks"]
            if track["type"] == "audio"
            for segment in track["segments"]
            if segment["role"] == "music"
        ]
        assert music_segments[0]["target_timerange"]["duration"] == 4_000_000
        assert (draft_path / "draft_meta_info.json").is_file()
        assert duplicate_jianying_draft_usage_count(
            session,
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
        ) == 1

        second = create_jianying_draft(
            session,
            name="可用草稿",
            destination_dir=str(destination),
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
            created_by=None,
        )
        assert Path(second.draft_path).name == "可用草稿-20260803-123456-2"
        assert second.snapshot["duplicate_usage_count_before_create"] == 1
        assert duplicate_jianying_draft_usage_count(
            session,
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
        ) == 2
        assert reset_jianying_draft_duplicate_counter(
            session,
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
        ) == 0
        assert duplicate_jianying_draft_usage_count(
            session,
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
        ) == 0
        third = create_jianying_draft(
            session,
            name="可用草稿",
            destination_dir=str(destination),
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
            created_by=None,
        )
        assert Path(third.draft_path).name == "可用草稿-20260803-123456-3"
        assert third.snapshot["duplicate_usage_count_before_create"] == 0
        assert duplicate_jianying_draft_usage_count(
            session,
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
        ) == 1
        session.delete(third)
        session.flush()
        assert duplicate_jianying_draft_usage_count(
            session,
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=music.id,
        ) == 1


def test_jianying_draft_directory_setting_and_copy_only_duration(workbench_database):
    destination = workbench_database / "confirmed-drafts"
    destination.mkdir()
    with session_scope() as session:
        saved = save_jianying_draft_directory(session, str(destination))
        detected = detect_jianying_draft_directory(session)
        assert saved == str(destination.resolve())
        assert detected["path"] == str(destination.resolve())
        copy = CopyContent(
            content_text="只有文案",
            normalized_content="只有文案",
            source="manual",
        )
        session.add(copy)
        session.flush()
        draft = create_jianying_draft(
            session,
            name="",
            destination_dir=detected["path"],
            copy_content_id=copy.id,
            narration_asset_id=None,
            music_resource_id=None,
            created_by=None,
        )
        content = json.loads((Path(draft.draft_path) / "draft_content.json").read_text(encoding="utf-8"))
        assert content["duration"] == 5_000_000
        assert draft.snapshot["duration_source"] == "copy_only_default"


def test_jianying_draft_clamps_bad_subtitle_cues_to_narration_duration(workbench_database, monkeypatch):
    destination = workbench_database / "jianying-bad-cues"
    destination.mkdir()
    narration_audio = workbench_database / "bad-cues.wav"
    narration_audio.write_bytes(b"narration")
    monkeypatch.setattr("app.services.jianying_drafts._probe_audio_duration_seconds", lambda _path: 12.13)
    with session_scope() as session:
        copy = CopyContent(
            content_text="异常字幕测试文案",
            normalized_content="异常字幕测试文案",
            source="manual",
        )
        narration = NarrationAsset(
            approved_text="第一句。第二句。",
            status="approved",
            audio_path=str(narration_audio),
            metadata_json={},
            subtitle_cues=[
                {"text": "第一句", "start_seconds": 0, "end_seconds": 33068.134},
                {"text": "第二句", "start_seconds": 33068.134, "end_seconds": 44739.241},
            ],
        )
        session.add_all([copy, narration])
        session.flush()
        draft = create_jianying_draft(
            session,
            name="异常字幕草稿",
            destination_dir=str(destination),
            copy_content_id=copy.id,
            narration_asset_id=narration.id,
            music_resource_id=None,
            created_by=None,
        )
        content = json.loads((Path(draft.draft_path) / "draft_content.json").read_text(encoding="utf-8"))
        assert content["duration"] == 12_130_000
        text_segments = [
            segment
            for track in content["tracks"]
            if track["type"] == "text"
            for segment in track["segments"]
        ]
        assert [segment["role"] for segment in text_segments] == ["copy", "subtitle"]
        assert text_segments[0]["target_timerange"] == {"start": 0, "duration": 12_130_000}
        assert text_segments[1]["target_timerange"] == {"start": 0, "duration": 12_130_000}
        assert draft.snapshot["duration_microseconds"] == 12_130_000


def test_delete_jianying_draft_removes_record_only(workbench_database):
    draft_dir = workbench_database / "existing-draft"
    draft_dir.mkdir()
    with session_scope() as session:
        draft = JianyingDraft(name="历史草稿", draft_path=str(draft_dir), status="ready")
        session.add(draft)
        session.flush()
        draft_id = draft.id

    delete_jianying_draft(draft_id, _admin=admin())

    with session_scope() as session:
        assert session.get(JianyingDraft, draft_id) is None
    assert draft_dir.is_dir()


def test_image_source_assets_create_product_without_public_batch_routes(workbench_database):
    paths = set(app.openapi()["paths"])
    assert "/api/v1/images/source-assets/create-product" in paths
    assert "/api/v1/images/source-assets/create-product-group" not in paths
    assert "/api/v1/images/batches" not in paths
    assert not [path for path in paths if "/api/v1/images/groups/" in path]

    source_file = workbench_database / "source-asset.jpg"
    source_file.write_bytes(b"image-bytes")
    with session_scope() as session:
        asset = CommerceImageSourceAsset(
            file_name="source-asset.jpg",
            storage_path=str(source_file),
        )
        session.add(asset)
        session.flush()
        asset_id = asset.id

    result = create_product_from_source_assets(
        SourceAssetProductCreateRequest(
            name="珍珠发簪",
            source_asset_ids=[asset_id],
        ),
        _admin=admin(),
    )

    assert result["product"]["name"] == "珍珠发簪"
    assert result["product"]["reference_count"] == 1
    assert result["product"]["source_images"][0]["asset_id"] == asset_id
    with session_scope() as session:
        asset = session.get(CommerceImageSourceAsset, asset_id)
        product = session.get(CommerceImageProduct, result["product"]["id"])
        source_group = session.scalar(select(CommerceImageGroup).where(CommerceImageGroup.product_id == product.id))
        assert asset.status == "assigned"
        assert product.product_code.startswith("IMG")
        assert source_group is not None
        assert source_group.status == "assigned"


def test_image_product_delete_returns_source_assets_to_unassigned(workbench_database):
    source_file = workbench_database / "return-source.jpg"
    source_file.write_bytes(b"image-bytes")
    with session_scope() as session:
        asset = CommerceImageSourceAsset(
            file_name="return-source.jpg",
            storage_path=str(source_file),
        )
        session.add(asset)
        session.flush()
        asset_id = asset.id

    created = create_product_from_source_assets(
        SourceAssetProductCreateRequest(
            name="退回原图测试",
            source_asset_ids=[asset_id],
        ),
        _admin=admin(),
    )
    product_id = created["product"]["id"]

    delete_image_product(product_id, delete_source_assets=False, _admin=admin())

    with session_scope() as session:
        product = session.get(CommerceImageProduct, product_id)
        asset = session.get(CommerceImageSourceAsset, asset_id)
        source_group = session.scalar(select(CommerceImageGroup).where(CommerceImageGroup.product_id.is_(None)))
        assert product.status == "deleted"
        assert asset.status == "unassigned"
        assert source_group is not None
        assert source_group.status == "unassigned"
    assert source_file.is_file()
