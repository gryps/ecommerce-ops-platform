from __future__ import annotations
from pathlib import Path
import shutil
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from app.api.v1.schemas import BootstrapRequest, BootstrapStatusResponse, LoginRequest, LoginResponse, MusicResourceLinkRequest, MusicResourceResponse, MusicResourceUpdateRequest, ProductCreateRequest, ProductResponse, ProductUpdateRequest, UserResponse
from app.ai import is_supported_speech_recognition_model, list_openai_compatible_models, load_model_profiles, models_for_profile_stage, save_model_profiles, test_openai_compatible_profile
from app.models import ModelProfile, ModelProfilesResponse, ModelProfilesUpdateRequest
from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import AdminUser, MediaAsset, MusicResource, Product
from app.services.audit import record_audit
from app.services.model_call_logs import clear_model_call_logs, model_call_log_detail, model_call_log_page, model_call_summary
from app.services.auth import bearer_token, bootstrap_admin, bootstrap_status, create_login_session, delete_login_session, require_admin
from app.services.music_resources import create_link_music, create_uploaded_music, delete_music_resource
from app.services.product_library import create_product, duplicate_product_name, product_code
from app.api.v1.human_workflow import router as human_workflow_router
router = APIRouter(prefix='/api/v1')
router.include_router(human_workflow_router)

@router.get('/model-profiles', response_model=ModelProfilesResponse)
def get_workbench_model_profiles(_admin: AdminUser=Depends(require_admin)) -> ModelProfilesResponse:
    return ModelProfilesResponse(profiles=load_model_profiles())

@router.put('/model-profiles', response_model=ModelProfilesResponse)
def update_workbench_model_profiles(payload: ModelProfilesUpdateRequest, _admin: AdminUser=Depends(require_admin)) -> ModelProfilesResponse:
    stored = {profile.stage: profile for profile in load_model_profiles(include_api_key=True)}
    for profile in payload.profiles:
        current = stored.get(profile.stage)
        if profile.model.strip() or profile.api_key.strip() or (current is not None and current.api_key.strip()):
            missing = []
            if not profile.base_url.strip():
                missing.append('接口地址')
            if not profile.model.strip():
                missing.append('模型名')
            has_key = profile.api_key.strip() or (current is not None and current.api_key.strip())
            if not has_key:
                missing.append('API Key')
            if missing:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{profile.label}：{'、'.join(missing)}必填")
            if profile.stage == 'speech_recognition' and not is_supported_speech_recognition_model(profile.model):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail='语音识别请选择非实时 qwen3-asr-flash；不能选择 realtime 或 filetrans 模型',
                )
    save_model_profiles(payload.profiles)
    return ModelProfilesResponse(profiles=load_model_profiles())

@router.put('/model-profiles/{stage}', response_model=ModelProfile)
def update_workbench_model_profile(stage: str, payload: ModelProfile, _admin: AdminUser=Depends(require_admin)) -> ModelProfile:
    stored_rows = load_model_profiles(include_api_key=True)
    stored = {profile.stage: profile for profile in stored_rows}
    if stage not in stored or payload.stage != stage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='业务模型不存在')
    current = stored[stage]
    missing = []
    if not payload.base_url.strip():
        missing.append('接口地址')
    if not payload.model.strip():
        missing.append('模型名')
    if not payload.api_key.strip() and not current.api_key.strip():
        missing.append('API Key')
    if missing:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"{payload.label}：{'、'.join(missing)}必填")
    if stage == 'speech_recognition' and not is_supported_speech_recognition_model(payload.model):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='语音识别请选择非实时 qwen3-asr-flash；不能选择 realtime 或 filetrans 模型',
        )
    merged = [payload if profile.stage == stage else profile for profile in stored_rows]
    save_model_profiles(merged)
    return next(profile for profile in load_model_profiles() if profile.stage == stage)

def _require_model_stage(stage: str) -> None:
    if stage not in {profile.stage for profile in load_model_profiles()}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='业务模型不存在')

@router.get('/model-profiles/call-logs/summaries')
def get_all_model_call_summaries(_admin: AdminUser=Depends(require_admin)) -> dict:
    return {'items': [model_call_summary(profile.stage) for profile in load_model_profiles()]}

@router.get('/model-profiles/{stage}/call-logs')
def get_model_call_logs(stage: str, page: int=1, _admin: AdminUser=Depends(require_admin)) -> dict:
    _require_model_stage(stage)
    return model_call_log_page(stage, page, 10)

@router.get('/model-profiles/{stage}/call-logs/{log_id}')
def get_model_call_log_detail(stage: str, log_id: str, _admin: AdminUser=Depends(require_admin)) -> dict:
    _require_model_stage(stage)
    try:
        return model_call_log_detail(stage, log_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

@router.delete('/model-profiles/{stage}/call-logs')
def delete_model_call_logs(stage: str, _admin: AdminUser=Depends(require_admin)) -> dict[str, int]:
    _require_model_stage(stage)
    return {'deleted': clear_model_call_logs(stage)}

@router.post('/model-profiles/test')
def test_workbench_model_profile(profile: ModelProfile, _admin: AdminUser=Depends(require_admin)) -> dict:
    if not profile.api_key:
        stored = next((item for item in load_model_profiles(include_api_key=True) if item.stage == profile.stage), None)
        if stored is not None:
            profile.api_key = stored.api_key
    return test_openai_compatible_profile(profile)

@router.post('/model-profiles/models')
def list_workbench_profile_models(profile: ModelProfile, _admin: AdminUser=Depends(require_admin)) -> dict[str, list[str]]:
    if not profile.api_key:
        stored = next((item for item in load_model_profiles(include_api_key=True) if item.stage == profile.stage), None)
        if stored is not None:
            profile.api_key = stored.api_key
    try:
        models = models_for_profile_stage(profile.stage, list_openai_compatible_models(profile))
        if not models:
            raise RuntimeError('当前模型列表中没有适用于音频转文案的非实时 qwen3-asr-flash 模型')
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {'models': models}

def user_response(user: AdminUser) -> UserResponse:
    return UserResponse(id=user.id, username=user.username, is_active=user.is_active)

def product_response(session, product: Product) -> ProductResponse:
    asset_count = session.scalar(select(func.count(MediaAsset.id)).where(MediaAsset.product_id == product.id)) or 0
    code = product_code(product.id)
    return ProductResponse(id=product.id, system_code=code, name=product.name, status=product.status, asset_count=asset_count, created_at=product.created_at, updated_at=product.updated_at)

def music_resource_response(resource: MusicResource) -> MusicResourceResponse:
    return MusicResourceResponse(id=resource.id, name=resource.name, source_type=resource.source_type, source_url=resource.source_url, file_path=resource.file_path, rights_confirmed=resource.rights_confirmed, status=resource.status, duration_seconds=resource.duration_seconds, custom_tags=list(resource.custom_tags or []), error=resource.error, created_at=resource.created_at, updated_at=resource.updated_at)

@router.get('/auth/status', response_model=BootstrapStatusResponse)
def get_auth_status() -> BootstrapStatusResponse:
    with session_scope() as session:
        return BootstrapStatusResponse(initialized=bootstrap_status(session))

@router.post('/auth/bootstrap', response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def bootstrap(payload: BootstrapRequest) -> UserResponse:
    with session_scope() as session:
        try:
            user = bootstrap_admin(session, payload.username, payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        return user_response(user)

@router.post('/auth/login', response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    with session_scope() as session:
        try:
            user, token, auth_session = create_login_session(session, payload.username, payload.password)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
        return LoginResponse(token=token, expires_at=auth_session.expires_at, user=user_response(user))

@router.get('/auth/me', response_model=UserResponse)
def me(admin: AdminUser=Depends(require_admin)) -> UserResponse:
    return user_response(admin)

@router.post('/auth/logout', status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def logout(request: Request, admin: AdminUser=Depends(require_admin)) -> Response:
    token = bearer_token(request)
    with session_scope() as session:
        delete_login_session(session, token, admin.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get('/products', response_model=list[ProductResponse])
def list_products(include_inactive: bool=True, _admin: AdminUser=Depends(require_admin)) -> list[ProductResponse]:
    with session_scope() as session:
        statement = select(Product).where(Product.status != 'deleted').order_by(Product.id)
        if not include_inactive:
            statement = statement.where(Product.status == 'active')
        products = session.scalars(statement).all()
        return [product_response(session, product) for product in products]

@router.get('/music-resources', response_model=list[MusicResourceResponse])
def list_music_resources(_admin: AdminUser=Depends(require_admin)) -> list[MusicResourceResponse]:
    with session_scope() as session:
        resources = session.scalars(select(MusicResource).order_by(MusicResource.created_at.desc())).all()
        return [music_resource_response(item) for item in resources]

@router.get('/music-resources/{resource_id}/audio', response_class=FileResponse)
def get_music_resource_audio(resource_id: str, _admin: AdminUser=Depends(require_admin)) -> FileResponse:
    with session_scope() as session:
        resource = session.get(MusicResource, resource_id)
        if resource is None:
            raise HTTPException(status_code=404, detail='音乐资源不存在')
        path = Path(resource.file_path).expanduser()
        if not resource.file_path or not path.is_file():
            raise HTTPException(status_code=404, detail='音乐文件尚未就绪')
        media_type = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.m4a': 'audio/mp4', '.aac': 'audio/aac', '.ogg': 'audio/ogg', '.flac': 'audio/flac'}.get(path.suffix.lower(), 'application/octet-stream')
        return FileResponse(path, media_type=media_type)

@router.post('/music-resources/link', response_model=MusicResourceResponse, status_code=status.HTTP_201_CREATED)
def add_link_music_resource(payload: MusicResourceLinkRequest, _admin: AdminUser=Depends(require_admin)) -> MusicResourceResponse:
    with session_scope() as session:
        try:
            resource = create_link_music(session, **payload.model_dump())
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return music_resource_response(resource)

@router.post('/music-resources/upload', response_model=MusicResourceResponse, status_code=status.HTTP_201_CREATED)
def add_uploaded_music_resource(music: UploadFile=File(...), name: str=Form(default=''), rights_confirmed: bool=Form(default=False), _admin: AdminUser=Depends(require_admin)) -> MusicResourceResponse:
    with session_scope() as session:
        try:
            resource = create_uploaded_music(session, name=name, filename=music.filename or 'music', stream=music.file, rights_confirmed=rights_confirmed)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return music_resource_response(resource)

@router.delete('/music-resources/{resource_id}', status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def remove_music_resource(resource_id: str, admin: AdminUser=Depends(require_admin)) -> Response:
    cleanup_root: Path | None = None
    with session_scope() as session:
        resource = session.get(MusicResource, resource_id)
        before = {'name': resource.name, 'source_type': resource.source_type, 'status': resource.status, 'file_path': resource.file_path} if resource is not None else {}
        try:
            result = delete_music_resource(session, resource_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        record_audit(session, actor_id=admin.id, action='music_resource.delete', object_type='music_resource', object_id=resource_id, before=before, after={'deleted': True})
        cleanup_root = Path(str(result['storage_root']))
    if cleanup_root is not None:
        shutil.rmtree(cleanup_root, ignore_errors=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.patch('/music-resources/{resource_id}', response_model=MusicResourceResponse)
def update_music_resource(resource_id: str, payload: MusicResourceUpdateRequest, admin: AdminUser=Depends(require_admin)) -> MusicResourceResponse:
    with session_scope() as session:
        resource = session.get(MusicResource, resource_id)
        if resource is None:
            raise HTTPException(status_code=404, detail='音乐资源不存在')
        before_name = resource.name
        before_tags = list(resource.custom_tags or [])
        resource.name = payload.name.strip()
        if payload.custom_tags is not None:
            normalized_tags = [' '.join(str(value).strip().split())[:40] for value in payload.custom_tags if str(value).strip()]
            resource.custom_tags = list(dict.fromkeys(normalized_tags))
        resource.updated_at = utc_now()
        record_audit(session, actor_id=admin.id, action='music_resource.rename', object_type='music_resource', object_id=resource.id, before={'name': before_name, 'custom_tags': before_tags}, after={'name': resource.name, 'custom_tags': list(resource.custom_tags or [])})
        return music_resource_response(resource)

@router.post('/products', response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(payload: ProductCreateRequest, admin: AdminUser=Depends(require_admin)) -> ProductResponse:
    with session_scope() as session:
        duplicate = duplicate_product_name(session, payload.name)
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'产品名称“{duplicate.name}”已存在，请直接选择已有产品')
        product = create_product(session, name=payload.name)
        record_audit(session, actor_id=admin.id, action='product.create', object_type='product', object_id=str(product.id), after={'system_code': product_code(product.id), 'name': product.name})
        return product_response(session, product)

@router.patch('/products/{product_id}', response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdateRequest, admin: AdminUser=Depends(require_admin)) -> ProductResponse:
    with session_scope() as session:
        product = session.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='产品不存在')
        if product.status == 'merged':
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='已合并产品不能修改')
        name = payload.name.strip()
        duplicate = duplicate_product_name(session, name, exclude_product_id=product.id)
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f'产品名称“{duplicate.name}”已存在')
        before = {'name': product.name}
        product.name = name
        product.updated_at = utc_now()
        record_audit(session, actor_id=admin.id, action='product.update', object_type='product', object_id=str(product.id), before=before, after={'name': name})
        session.flush()
        return product_response(session, product)
