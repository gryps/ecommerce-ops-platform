from .human_common import *

router = APIRouter()

@router.delete('/products/{product_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_human_product(product_id: int, admin: AdminUser=Depends(require_admin)) -> None:
    """Remove a product from current classification data without touching files."""
    with session_scope() as session:
        product = session.get(Product, product_id)
        if product is None or product.status == 'deleted':
            raise HTTPException(status_code=404, detail='产品不存在')
        before_status = product.status
        session.execute(delete(MediaAsset).where(MediaAsset.product_id == product.id))
        session.execute(delete(CopyContent).where(CopyContent.product_id == product.id))
        product.status = 'deleted'
        product.updated_at = utc_now()
        record_audit(session, actor_id=admin.id, action='human_product.delete', object_type='product', object_id=str(product.id), before={'status': before_status, 'name': product.name}, after={'status': 'deleted', 'current_materials_and_titles_removed': True})

