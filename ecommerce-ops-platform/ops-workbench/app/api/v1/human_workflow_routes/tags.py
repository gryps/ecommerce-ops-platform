from .human_common import *

router = APIRouter()

@router.get('/tag-categories')
def list_tag_categories(q: str='', limit: int=20, offset: int=0, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        categories = list(session.scalars(select(TagCategory).order_by(TagCategory.name)).all())
        if q.strip():
            categories = [item for item in categories if _similarity(q, item.name) >= 0.35]
            categories.sort(key=lambda item: (-_similarity(q, item.name), item.name))
        total = len(categories)
        rows = categories[max(0, offset):max(0, offset) + max(1, min(limit, 5000))]
        return {'items': [_category_dict(item) for item in rows], 'total': total}

@router.post('/tag-categories', status_code=status.HTTP_201_CREATED)
def create_tag_category(payload: MasterNamePayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    name = ' '.join(payload.name.strip().split())
    normalized = normalize_tag_name(name)
    with session_scope() as session:
        if session.scalar(select(TagCategory).where(TagCategory.normalized_name == normalized)):
            raise HTTPException(status_code=409, detail='标签分类已存在')
        item = TagCategory(name=name, normalized_name=normalized)
        session.add(item)
        session.flush()
        return _category_dict(item)

@router.patch('/tag-categories/{category_id}')
def update_tag_category(category_id: str, payload: MasterNamePayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    name = ' '.join(payload.name.strip().split())
    normalized = normalize_tag_name(name)
    with session_scope() as session:
        item = session.get(TagCategory, category_id)
        if item is None:
            raise HTTPException(status_code=404, detail='标签分类不存在')
        duplicate = session.scalar(select(TagCategory).where(TagCategory.normalized_name == normalized, TagCategory.id != item.id))
        if duplicate:
            raise HTTPException(status_code=409, detail='标签分类已存在')
        item.name = name
        item.normalized_name = normalized
        item.updated_at = utc_now()
        session.flush()
        return _category_dict(item)

@router.delete('/tag-categories/{category_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_tag_category(category_id: str, _admin: AdminUser=Depends(require_admin)) -> None:
    with session_scope() as session:
        item = session.get(TagCategory, category_id)
        if item is None:
            raise HTTPException(status_code=404, detail='标签分类不存在')
        session.delete(item)

@router.get('/tags')
def list_global_tags(category_id: str | None=None, q: str='', limit: int=20, offset: int=0, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    with session_scope() as session:
        category = session.get(TagCategory, category_id) if category_id else None
        statement = select(ShotTag)
        if category_id and category is None:
            raise HTTPException(status_code=404, detail='标签分类不存在')
        if category:
            statement = statement.where(ShotTag.category_id == category.id)
        tags = list(session.scalars(statement.order_by(ShotTag.name)).all())
        if q.strip():
            tags = [item for item in tags if _similarity(q, item.name) >= 0.35]
            tags.sort(key=lambda item: (-_similarity(q, item.name), item.name))
        categories = {item.id: item.name for item in session.scalars(select(TagCategory)).all()}
        total = len(tags)
        rows = tags[max(0, offset):max(0, offset) + max(1, min(limit, 5000))]
        return {'items': [_tag_dict(item, categories.get(item.category_id, '')) for item in rows], 'total': total}

@router.patch('/tags/{tag_id}')
def update_global_tag(tag_id: str, payload: MasterNamePayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    name = ' '.join(payload.name.strip().split())
    normalized = normalize_tag_name(name)
    with session_scope() as session:
        tag = session.get(ShotTag, tag_id)
        if tag is None:
            raise HTTPException(status_code=404, detail='标签不存在')
        duplicate = session.scalar(select(ShotTag).where(ShotTag.category_id == tag.category_id, ShotTag.normalized_name == normalized, ShotTag.id != tag.id))
        if duplicate:
            raise HTTPException(status_code=409, detail='当前分类下标签名称已存在')
        tag.name = name
        tag.normalized_name = normalized
        tag.updated_at = utc_now()
        category = session.get(TagCategory, tag.category_id)
        session.flush()
        return _tag_dict(tag, category.name if category else '')

@router.delete('/tags/{tag_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_global_tag(tag_id: str, _admin: AdminUser=Depends(require_admin)) -> None:
    with session_scope() as session:
        tag = session.get(ShotTag, tag_id)
        if tag is None:
            raise HTTPException(status_code=404, detail='标签不存在')
        session.delete(tag)

@router.post('/tags', status_code=status.HTTP_201_CREATED)
def create_product_tag(payload: ProductTagPayload, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    name = ' '.join(payload.name.strip().split())
    normalized = normalize_tag_name(name)
    with session_scope() as session:
        category = session.get(TagCategory, payload.category_id)
        if category is None:
            raise HTTPException(status_code=404, detail='标签分类不存在')
        tag = session.scalar(select(ShotTag).where(ShotTag.category_id == category.id, ShotTag.normalized_name == normalized))
        if tag is None:
            tag = ShotTag(name=name, normalized_name=normalized, category_id=category.id)
            session.add(tag)
            session.flush()
        else:
            raise HTTPException(status_code=409, detail='当前分类下标签名称已存在')
        session.flush()
        return _tag_dict(tag, category.name)

