from tests.current_workflow_helpers import *
from app.services.ai_video.workflow_registry import list_workflow_templates


def test_ai_video_workflow_registry_marks_comfyui_placeholder(tmp_path):
    workflows_dir = tmp_path / "workflows"
    workflows_dir.mkdir()
    (workflows_dir / "comfyui_business_workflow.example.json").write_text("{}", encoding="utf-8")

    templates = list_workflow_templates(workflows_dir)
    by_name = {template.name: template for template in templates}

    assert by_name["text_to_video"].default_engine == "vendor_video"
    assert by_name["image_to_video"].required_asset_kinds == ["product"]
    assert by_name["comfyui_business_workflow"].default_engine == "comfyui"
    assert by_name["comfyui_business_workflow"].available is False
    assert "example" in by_name["comfyui_business_workflow"].availability_note


def test_ai_video_project_asset_shot_and_task_flow(workbench_database, monkeypatch):
    monkeypatch.setattr(ai_video_repository, "path", workbench_database / "ai-video" / "databases" / "workbench.json")
    project = create_ai_video_project(
        ProductProject(
            name="珍珠发簪15秒宣传片",
            product_name="珍珠流苏发簪",
            selling_points="国风造型、轻盈不压发",
            audience="新中式穿搭用户",
            tone="清透、雅致、适合短视频投放",
        ),
        _admin=admin(),
    )
    upload = UploadFile(filename="product.png", file=io.BytesIO(b"png-bytes"))
    asset = upload_ai_video_asset(
        project_id=project.id,
        kind="product",
        name="主图",
        notes="正面商品图",
        file=upload,
        _admin=admin(),
    )
    assert Path(asset.file_path).read_bytes() == b"png-bytes"
    assert project.id in asset.file_path

    shots = create_director_shots({"project_id": project.id}, _admin=admin())
    assert len(shots) == 4
    assert shots[0].project_id == project.id
    assert "珍珠流苏发簪" in shots[0].prompt

    task = create_generation_task(
        GenerationTask(
            project_id=project.id,
            engine="comfyui",
            workflow_name="product_keyframe",
            prompt=shots[0].prompt,
            input_asset_ids=[asset.id],
        ),
        _admin=admin(),
    )
    assert task.status == "queued"
    assert task.input_asset_ids == [asset.id]
    with session_scope() as session:
        events = session.scalars(select(AiVideoTaskEvent).where(AiVideoTaskEvent.task_id == task.id)).all()
        assert [event.event_type for event in events] == ["created"]

    submitted = awaitable(submit_ai_video_task(task.id, _admin=admin()))
    assert submitted.status == "failed"
    assert "占位文件" in submitted.error
    event_types = [event.event_type for event in list_ai_video_task_events(task.id, _admin=admin())]
    assert event_types == ["created", "submit_failed"]


def test_ai_video_imports_approved_image_production_asset(workbench_database, monkeypatch):
    monkeypatch.setattr(ai_video_repository, "path", workbench_database / "ai-video" / "databases" / "workbench.json")
    project = create_ai_video_project(ProductProject(name="图片生产转宣传片", product_name="珍珠流苏发簪"), _admin=admin())
    output_path = workbench_database / "image-output.png"
    output_path.write_bytes(b"image-bytes")
    with session_scope() as session:
        product = CommerceImageProduct(product_code="IMG001", name="珍珠流苏发簪")
        session.add(product)
        session.flush()
        image_task = CommerceImageTask(
            product_id=product.id,
            template_id="white-bg",
            template_name="白底图",
            model="mock-image-model",
            prompt="prompt",
            negative_prompt="",
            output_images=[{"name": output_path.name, "path": str(output_path), "image_type": "白底图"}],
            status="archived",
            review_status="approved",
        )
        session.add(image_task)
        session.flush()
        task_id = image_task.id

    asset = import_asset_from_image_production(
        ImageProductionAssetImport(project_id=project.id, task_id=task_id, output_index=0),
        _admin=admin(),
    )

    assert asset.kind == "product"
    assert asset.file_path == str(output_path.resolve())
    assert asset.preview_url == f"/api/v1/images/tasks/{task_id}/outputs/0/file"
    assert "来自图片生产" in asset.notes
    request = build_video_request(
        GenerationTask(
            project_id=project.id,
            engine="vendor_video",
            workflow_name="image_to_video",
            prompt="生成宣传片",
            input_asset_ids=[asset.id],
        )
    )
    assert request.input_files[0].path == str(output_path.resolve())


def test_ai_video_project_names_are_unique_and_delete_cascades(workbench_database, monkeypatch):
    monkeypatch.setattr(ai_video_repository, "path", workbench_database / "ai-video" / "databases" / "workbench.json")
    project = create_ai_video_project(ProductProject(name="测试宣传片", product_name="商品A"), _admin=admin())
    with pytest.raises(HTTPException) as duplicate:
        create_ai_video_project(ProductProject(name=" 测试宣传片 ", product_name="商品B"), _admin=admin())
    assert duplicate.value.status_code == 409

    asset = upload_ai_video_asset(
        project_id=project.id,
        kind="product",
        name="主图",
        notes="",
        file=UploadFile(filename="product.png", file=io.BytesIO(b"png-bytes")),
        _admin=admin(),
    )
    create_director_shots({"project_id": project.id}, _admin=admin())
    task = create_generation_task(
        GenerationTask(
            project_id=project.id,
            engine="vendor_video",
            workflow_name="text_to_video",
            prompt="测试",
            input_asset_ids=[asset.id],
        ),
        _admin=admin(),
    )

    delete_ai_video_project(project.id, _admin=admin())
    store = ai_video_repository.load()
    assert not any(item.id == project.id for item in store.projects)
    assert not any(item.project_id == project.id for item in store.assets)
    assert not any(item.project_id == project.id for item in store.shots)
    assert not any(item.project_id == project.id for item in store.tasks)
    with pytest.raises(HTTPException) as missing_events:
        list_ai_video_task_events(task.id, _admin=admin())
    assert missing_events.value.status_code == 404


def test_ai_video_vendor_adapter_submit_and_refresh(workbench_database, monkeypatch):
    monkeypatch.setattr(ai_video_repository, "path", workbench_database / "ai-video" / "databases" / "workbench.json")
    project = create_ai_video_project(
        ProductProject(name="图生视频测试", product_name="珍珠流苏发簪"),
        _admin=admin(),
    )
    asset = upload_ai_video_asset(
        project_id=project.id,
        kind="product",
        name="首帧图",
        notes="",
        file=UploadFile(filename="start.png", file=io.BytesIO(b"png-bytes")),
        _admin=admin(),
    )

    class FakeVideoAdapter:
        async def submit(self, request):
            assert request.mode == "i2v"
            assert request.input_files[0].path == asset.file_path
            return StandardSubmitResult(
                provider="fake_video",
                provider_task_id="remote-001",
                status="running",
                raw_response={"id": "remote-001", "status": "running"},
            )

        async def get_status(self, provider_task_id):
            assert provider_task_id == "remote-001"
            return StandardTaskStatus(
                provider="fake_video",
                provider_task_id=provider_task_id,
                status="succeeded",
                output_paths=["https://example.test/output.mp4"],
                raw_response={"status": "succeeded"},
            )

    from app.services.ai_video.executor import refresh_generation_task, submit_generation_task

    task = create_generation_task(
        GenerationTask(
            project_id=project.id,
            engine="vendor_video",
            workflow_name="image_to_video",
            prompt="商品轻微旋转，镜头慢推",
            input_asset_ids=[asset.id],
        ),
        _admin=admin(),
    )
    submitted = awaitable(submit_generation_task(task.id, video_adapter=FakeVideoAdapter()))
    assert submitted.status == "running"
    assert submitted.provider_task_id == "remote-001"
    async def fake_download(url, target_dir, index):
        assert url == "https://example.test/output.mp4"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"output-{index + 1:02d}.mp4"
        target.write_bytes(b"video-bytes")
        return str(target)

    refreshed = awaitable(
        refresh_generation_task(
            task.id,
            video_adapter=FakeVideoAdapter(),
            output_downloader=fake_download,
        )
    )
    assert refreshed.status == "succeeded"
    assert len(refreshed.output_paths) == 1
    assert refreshed.output_paths[0].endswith("/output-01.mp4")
    assert Path(refreshed.output_paths[0]).read_bytes() == b"video-bytes"
    event_types = [event.event_type for event in list_ai_video_task_events(task.id, _admin=admin())]
    assert event_types == ["created", "submitted", "status_checked"]
