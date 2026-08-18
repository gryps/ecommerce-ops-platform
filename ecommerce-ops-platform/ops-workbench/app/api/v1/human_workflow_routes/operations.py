from .human_common import *

router = APIRouter()

@router.get('/operation-status/{operation_id}')
def operation_status(operation_id: str, _admin: AdminUser=Depends(require_admin)) -> dict[str, Any]:
    state = get_operation(operation_id)
    if state is None:
        return {'operation_id': operation_id, 'kind': '', 'status': 'unknown', 'detail': ''}
    return {'operation_id': state.operation_id, 'kind': state.kind, 'status': state.status, 'detail': state.detail, 'updated_at': state.updated_at}

