from tests.current_workflow_helpers import *


def test_qwen_audio_voice_preview_is_persisted_and_reused(workbench_database, monkeypatch):
    profile = ModelProfile(
        stage="speech_synthesis",
        label="字幕配音",
        model="qwen-audio-3.0-tts-plus",
    )
    monkeypatch.setattr(
        "app.api.v1.human_workflow_routes.voice_narrations.load_model_profiles", lambda: [profile]
    )
    calls = []
    def fake_generate(_text, target, **kwargs):
        calls.append(kwargs["voice"])
        assert kwargs["voice"] == "qwen-audio-3.0-tts-plus-longcanzhuyue"
        assert kwargs["business_step"] == "字幕配音音色试听"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"RIFF-preview")

    monkeypatch.setattr(
        "app.api.v1.human_workflow_routes.voice_narrations.generate_narration_audio", fake_generate
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
        "app.api.v1.human_workflow_routes.copies.prepare_uploaded_audio",
        lambda **_kwargs: prepared,
    )
    monkeypatch.setattr(
        "app.api.v1.human_workflow_routes.copies.recognize_narration_audio",
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
        "app.api.v1.human_workflow_routes.voice_narrations.load_model_profiles", lambda: [profile]
    )

    def fake_generate(text, target, **kwargs):
        assert text == "第一句。第二句。"
        assert kwargs["voice"] == "qwen-audio-3.0-tts-plus-longcanzhuyue"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"RIFF-generated")
        return {"model": profile.model, "voice": kwargs["voice"], "audio_bytes": target.stat().st_size}

    monkeypatch.setattr(
        "app.api.v1.human_workflow_routes.voice_narrations.generate_narration_audio", fake_generate
    )
    monkeypatch.setattr(
        "app.api.v1.human_workflow_routes.voice_narrations.generated_subtitle_cues",
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
        "ai_video_generation",
        "speech_recognition",
        "speech_synthesis",
    ]
    ai_video = next(item for item in profiles if item.stage == "ai_video_generation")
    assert ai_video.provider_type == "vendor_video_api"
    assert ai_video.protocol == "video_generation"
    assert {"text_to_video", "image_to_video", "remote_output"}.issubset(set(ai_video.capabilities))
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
