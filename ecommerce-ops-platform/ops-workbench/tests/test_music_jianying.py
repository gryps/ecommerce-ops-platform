from tests.current_workflow_helpers import *
from app.services.music_resources import (
    _douyin_media_url,
    _douyin_media_urls,
    _douyin_video_id,
    _ensure_audible_audio,
    _extract_shared_url,
    _is_douyin_url,
)


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
