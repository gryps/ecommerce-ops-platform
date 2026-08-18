from tests.current_workflow_helpers import *


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
