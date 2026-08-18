from __future__ import annotations

from fastapi import APIRouter

from .human_workflow_routes import ROUTERS
from .human_workflow_routes.human_common import (
    CopyIterationPayload,
    CopyLibraryPayload,
    CopyReviewPayload,
    JianyingDraftCreatePayload,
    JianyingDraftDirectoryPayload,
    JianyingDraftDuplicatePayload,
    MasterNamePayload,
    MaterialClassificationItemPayload,
    MaterialClassificationPayload,
    ModelNarrationPayload,
    NarrationConfirmPayload,
    ProductTagPayload,
    SourceDirectorySelectPayload,
    SourceImagePreviewPayload,
    VoicePreviewPayload,
)
from .human_workflow_routes.copies import (
    audio_to_copy,
    continue_copy_generation,
    create_copy_iteration,
    create_library_copy,
    delete_copy_iteration,
    delete_library_copy,
    list_copy_iterations,
    list_copy_library,
    review_generated_copy,
    update_library_copy,
)
from .human_workflow_routes.jianying import (
    confirm_jianying_draft_directory,
    delete_jianying_draft,
    generate_jianying_draft,
    get_jianying_draft_directory,
    get_jianying_draft_duplicate_count,
    list_jianying_drafts,
    reset_jianying_draft_duplicate_count,
)
from .human_workflow_routes.materials import (
    confirm_material_classification,
    get_classified_material_video,
    list_classified_materials,
)
from .human_workflow_routes.operations import operation_status
from .human_workflow_routes.products import delete_human_product
from .human_workflow_routes.source_files import (
    preview_image_source_file,
    select_image_source_files,
    select_source_directory,
)
from .human_workflow_routes.tags import (
    create_product_tag,
    create_tag_category,
    delete_global_tag,
    delete_tag_category,
    list_global_tags,
    list_tag_categories,
    update_global_tag,
    update_tag_category,
)
from .human_workflow_routes.voice_narrations import (
    confirm_narration,
    create_model_voice_narration,
    delete_narration,
    get_narration_audio,
    get_voice_catalog_item,
    list_narrations,
    list_voice_catalog,
    preview_model_voice,
)

router = APIRouter(prefix="/human", tags=["human-first-workflow"])
for child_router in ROUTERS:
    router.include_router(child_router)
