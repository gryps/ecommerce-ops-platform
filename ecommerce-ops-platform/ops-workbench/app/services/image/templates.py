from __future__ import annotations


IMAGE_TEMPLATES: tuple[dict[str, object], ...] = (
    {
        "id": "main-white",
        "name": "白底主图",
        "image_type": "generated_main",
        "aspect_ratio": "1:1",
        "scene": "生成一张电商白底商品主图。画面干净，产品居中，背景纯白或接近纯白，柔和摄影棚光线，产品边缘清晰，材质细节清楚。",
        "negative": "不要添加额外装饰，不要改变珠子数量，不要改变金属颜色，不要改变流苏方向，不要生成多余产品。",
        "recommended_models": ["通义万相", "腾讯混元"],
        "input_image_types": ["source_images"],
    },
    {
        "id": "scene-chinese",
        "name": "中式环境图",
        "image_type": "generated_scene",
        "aspect_ratio": "4:5",
        "scene": "生成一张高级中式风格电商环境图。发簪放置在浅色绸缎、木质首饰盘或简洁梳妆台上，画面优雅、干净、有自然柔光。",
        "negative": "背景不要喧宾夺主，不要遮挡产品，不要改变产品结构，不要出现文字、水印或 logo。",
        "recommended_models": ["即梦/Seedream", "腾讯混元", "通义万相"],
        "input_image_types": ["source_images"],
    },
    {
        "id": "wearing",
        "name": "佩戴图",
        "image_type": "generated_wearing",
        "aspect_ratio": "4:5",
        "scene": "生成一张发簪佩戴图。模特为黑色或深棕色盘发，发簪自然插入发髻，露出完整装饰部分和合理长度的簪杆，画面干净、自然、真实。",
        "negative": "不要把发簪变成发夹、发钗或普通头饰，不要遮挡主要装饰，不要增加珠子，不要改变流苏数量。",
        "recommended_models": ["即梦/Seedream", "腾讯混元"],
        "input_image_types": ["source_images"],
    },
    {
        "id": "mobile-detail",
        "name": "手机竖屏商详图",
        "image_type": "generated_mobile_detail",
        "aspect_ratio": "9:16",
        "scene": "生成一张 9:16 手机竖屏电商详情图。画面上方展示发簪整体，下方留出可排版空间或展示材质细节，适合淘宝、抖音、小红书商品详情页。",
        "negative": "不要出现无关文字、水印、logo，不要改变颜色、装饰数量、流苏位置和簪杆比例。",
        "recommended_models": ["通义万相"],
        "input_image_types": ["source_images"],
    },
)


def list_templates() -> list[dict[str, object]]:
    return [dict(item) for item in IMAGE_TEMPLATES]


def template_by_id(template_id: str) -> dict[str, object]:
    for item in IMAGE_TEMPLATES:
        if item["id"] == template_id:
            return dict(item)
    raise LookupError("图片模板不存在")
