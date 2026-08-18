from tests.current_workflow_helpers import *


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
        "app.api.v1.human_workflow_routes.copies.analyze_and_generate_copies",
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
        "app.api.v1.human_workflow_routes.copies.continue_copy_iteration",
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
        input_payload={"api_key": "dummy-redacted-value", "prompt": "测试"},
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

