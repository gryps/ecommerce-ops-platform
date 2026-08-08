"""retire model screening and review history

Revision ID: z59n1i3j6k80
Revises: z48m0h2i5j79
Create Date: 2026-07-31
"""

from alembic import op


revision = "z59n1i3j6k80"
down_revision = "z48m0h2i5j79"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The human-first workflow preserves material records, clips and tags. Only
    # obsolete model-screening/review artifacts and queued work are removed.
    op.execute("DELETE FROM wb_media_quality_issues")
    op.execute(
        """
        DELETE FROM wb_jobs
        WHERE job_type IN (
            'material_batch.quality_check',
            'material_batch.quality_scan',
            'media_asset.quality_check',
            'media_asset.generate_candidates',
            'material_batch.classify_products'
        )
        """
    )
    op.execute(
        """
        DELETE FROM wb_audit_events
        WHERE action LIKE 'media_asset.quality%%'
           OR action LIKE 'candidate_segment.review%%'
           OR action LIKE 'product_classification.review%%'
        """
    )
    op.execute(
        """
        UPDATE wb_media_assets
        SET quality_review_status = 'not_required',
            quality_review_note = '',
            quality_reviewed_at = NULL
        """
    )
    op.execute(
        """
        UPDATE wb_material_batches
        SET classification_status = 'not_required'
        WHERE classification_status IN (
            'pending', 'queued', 'processing', 'partially_completed', 'failed'
        )
        """
    )


def downgrade() -> None:
    # Deleted review history cannot be reconstructed. Schema rollback is a no-op.
    pass
