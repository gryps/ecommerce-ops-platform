from __future__ import annotations

from app.services.ai_video.models import ProductProject, Shot


def draft_shots(project: ProductProject) -> list[Shot]:
    product = project.product_name or project.name
    selling_points = project.selling_points or "核心卖点清晰呈现"
    tone = project.tone or "真实、高级、适合电商投放"
    audience = project.audience or "目标消费者"
    return [
        Shot(
            project_id=project.id,
            order=1,
            title="产品建立",
            duration_seconds=2.5,
            visual_goal=f"用干净画面建立 {product} 的第一印象。",
            camera="低机位慢推，产品居中，浅景深。",
            prompt=f"{product} product hero shot, {tone}, clean ecommerce studio lighting, premium commercial video keyframe",
            required_asset_kinds=["product", "reference"],
        ),
        Shot(
            project_id=project.id,
            order=2,
            title="卖点证明",
            duration_seconds=3.0,
            visual_goal=f"用细节镜头证明：{selling_points}",
            camera="微距切换到中景，局部高光扫过材质。",
            prompt=f"macro detail shot of {product}, show selling points: {selling_points}, believable product advertising, high texture",
            required_asset_kinds=["product", "prop"],
        ),
        Shot(
            project_id=project.id,
            order=3,
            title="场景转化",
            duration_seconds=3.5,
            visual_goal=f"让 {audience} 看到真实使用场景和情绪价值。",
            camera="人物手部或半身入镜，环境自然运动，镜头轻微跟随。",
            prompt=f"{product} used by target audience {audience}, lifestyle scene, {tone}, cinematic ecommerce advertising",
            required_asset_kinds=["character", "environment", "product"],
        ),
        Shot(
            project_id=project.id,
            order=4,
            title="收束成片",
            duration_seconds=2.0,
            visual_goal="回到产品和品牌利益点，形成可投放的结尾画面。",
            camera="俯拍到正面定格，留出字幕和价格利益点区域。",
            prompt=f"{product} final packshot, clean background, commercial end frame, room for Chinese subtitles and CTA, {tone}",
            required_asset_kinds=["product", "keyframe"],
        ),
    ]
