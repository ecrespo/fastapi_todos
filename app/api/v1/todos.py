from typing import Dict, List

from fastapi import APIRouter, Security, Depends, Query, status, HTTPException

from app.shared.rate_limiter import limiter
from app.models.RequestsTodos import Todo
from app.models.ResponseTodos import PaginatedTodos, TodoResponse, MessageResponse, TaskEnqueuedResponse
from app.shared.messages import NOTFOUND, DELETED, UPDATED, CREATED
from app.services.todo_service import TodoService
from redis import asyncio as aioredis
from app.shared.redis_settings import get_redis_client
import math
from app.shared.auth import api_verifier, editor_required, admin_required, get_user_id_for_token, is_admin_token
from app.shared.cache_redis import _todo_key, _cache_get_json, _cache_set_json, _cache_delete
from app.shared.config import get_settings
router = APIRouter(prefix="/todos", tags=["todos"])

service = TodoService()

KEY_ALL_TODOS = "todos:all"


@router.get(
    "/",
    response_model=PaginatedTodos,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a paginated list of todos."
)
@limiter.limit("5/minute")
async def get_todos(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    size: int = Query(10, ge=1, le=100, description="Page size (1-100)"),
    token: str = Security(api_verifier),
    redis_client: aioredis.Redis = Depends(get_redis_client),
) -> Dict[str, List[Todo]]:
    """
    Retrieve a paginated list of todos.

    Admin users (or legacy tokens) see all todos. Non-admin users only see their own todos.
    """
    # Determine scope from token
    try:
        admin = await is_admin_token(token)
        user_id = None if admin else await get_user_id_for_token(token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    scope_prefix = KEY_ALL_TODOS if admin else f"todos:user:{user_id}"
    cache_key = f"{scope_prefix}:{page}:{size}"

    # Try cache first
    cached = await _cache_get_json(redis_client, cache_key)
    if cached and isinstance(cached, dict) and "todos" in cached and "pagination" in cached:
        return cached

    # Fallback to service with appropriate filtering
    items, total = await service.get_todos(page=page, size=size, user_id=None if admin else user_id)
    pages = math.ceil(total / size) if size > 0 else 0
    payload = {
        "todos": items,
        "pagination": {"total": total, "page": page, "size": size, "pages": pages},
    }
    # Cache normalized json-serializable shape
    try:
        serializable = {
            "todos": [t.model_dump(mode="json") for t in items],
            "pagination": {"total": total, "page": page, "size": size, "pages": pages},
        }
        await _cache_set_json(redis_client, cache_key, serializable)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    return payload


@router.get(
    "/{todo_id}",
    response_model=TodoResponse | MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific to-do item by its ID."
)
@limiter.limit("5/minute")
async def get_todo(todo_id: int, token: str = Security(api_verifier), redis_client: aioredis.Redis = Depends(get_redis_client)) -> Dict[str, Todo | str]:
    """
    Retrieves a specific to-do item by its ID. Searches through the
    list of to-do items and returns the item if found. If the item
    does not exist, an appropriate message is returned.

    :param todo_id: The unique identifier of the to-do item being requested.
    :type todo_id: int
    :return: A dictionary containing either the found to-do item or
             a message indicating that no to-do item was found.
    :rtype: Dict[str, Union[Todo, str]]
    """
    # Try cache first
    key = _todo_key(todo_id)
    cached = await _cache_get_json(redis_client, key)
    if cached is not None:
        return {"todo": cached}

    # Fallback to service
    todo = await service.get_todo(todo_id)
    if todo is not None:
        try:
            await _cache_set_json(redis_client, key, todo.model_dump(mode="json"))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(e))
        return {"todo": todo}

    return {"message": NOTFOUND}


# Internal reusable create flow for sync and Celery paths
async def _create_todo_internal(todo_dict: dict) -> None:
    todo = Todo(**todo_dict)
    await service.create_todo(todo)
    # Invalidate caches using the shared Redis client
    redis_client = get_redis_client()
    await _cache_delete(redis_client, KEY_ALL_TODOS, _todo_key(todo.id))


@router.post(
    "/",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Create a new todo item."
)
@limiter.limit("5/minute")
async def create_todo(todo: Todo, token: str = Security(api_verifier), _: None = Depends(editor_required), redis_client: aioredis.Redis = Depends(get_redis_client)) -> Dict[str, str]:
    """
    Handles the creation of a new todo item and appends it to the existing list of todos.

    Associates the todo with the user bound to the provided Bearer token (if any).

    :param todo: The Todo object containing the details of the todo item to be created.
    :return: A dictionary indicating the success message upon todo creation.
    """
    # Resolve user_id from token (may be None for legacy tokens)
    try:
        user_id = await get_user_id_for_token(token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    todo.user_id = user_id

    await service.create_todo(todo)
    # Invalidate caches
    await _cache_delete(redis_client, KEY_ALL_TODOS, _todo_key(todo.id))
    return {"message": CREATED}


@router.post(
    "/async",
    response_model=TaskEnqueuedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue a Celery task to create a new todo item."
)
@limiter.limit("5/minute")
async def create_todo_async(todo: Todo, token: str = Security(api_verifier)) -> Dict[str, str]:
    # Import task lazily to avoid heavy imports at module import time
    import os
    from app.tasks.todo_tasks import create_todo_task

    # Resolve user_id from token and include in payload
    try:
        user_id = await get_user_id_for_token(token)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    payload = todo.model_dump(mode="json")
    payload["user_id"] = user_id
    # If eager mode is enabled (as in tests), run synchronously to avoid broker dependency
    eager_env = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").strip().lower()
    eager = eager_env in {"1", "true", "yes", "on"}
    if eager:
        # Run inline using the same internal async flow used by the task
        from app.api.v1.todos import _create_todo_internal  # circular-safe import
        await _create_todo_internal(payload)
        task_id = "eager"
    else:
        # Import celery app lazily to avoid initializing it when not needed
        from app.shared.celery_app import celery_app
        result = create_todo_task.delay(payload)
        task_id = result.id
    # Respond with task id so clients can track it (if a result backend is used)
    return {"message": "enqueued", "task_id": task_id}


@router.put(
    "/{todo_id}",
    response_model=TodoResponse | MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing todo item by its ID."
)
@limiter.limit("5/minute")
async def update_todo(todo_id: int, todo_obj: Todo, token: str = Security(api_verifier), _: None = Depends(editor_required), redis_client: aioredis.Redis = Depends(get_redis_client)) -> Dict[str, Todo | str]:
    """
    Updates an existing todo item identified by its ID. This function iterates
    through the list of todos to find a matching ID, then updates the title
    and item attributes of the corresponding todo. If no matching todo is
    found, a message indicating the absence of the todo is returned.

    :param todo_id: The unique identifier of the todo item to be updated.
    :type todo_id: int
    :param todo_obj: The new values to update the todo, containing the title
        and item fields.
    :type todo_obj: Todo
    :return: A message indicating whether the todo was successfully updated
        or if no matching todo was found.
    :rtype: dict
    """
    updated = await service.update_todo(todo_id, todo_obj)
    if updated is not None:
        # Update the per-id cache and invalidate the list cache
        try:
            await _cache_set_json(redis_client, _todo_key(todo_id), updated.model_dump(mode="json"))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail=str(e))
        await _cache_delete(redis_client, KEY_ALL_TODOS)
        return {"todo": updated}
    return {"message": NOTFOUND}



@router.delete(
    "/{todo_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a specific todo item by its ID."
)
@limiter.limit("5/minute")
async def delete_todo(todo_id: int, token: str = Security(api_verifier), _: None = Depends(admin_required), redis_client: aioredis.Redis = Depends(get_redis_client)) -> Dict[str, str]:
    """
    Deletes a specific todo item by its unique identifier.

    This function iterates through the list of todos to find a match based on
    the provided `todo_id`. If a todo with the corresponding id is found, it
    is removed from the list and a success message is returned. If no matching
    todo is found, an appropriate response indicating no items were deleted
    is returned.

    :param todo_id: The unique identifier of the todo item to be deleted
    :type todo_id: int
    :return: A message indicating the success or failure of the deletion operation
    :rtype: dict
    """
    deleted = await service.delete_todo(todo_id)
    if deleted:
        await _cache_delete(redis_client, KEY_ALL_TODOS, _todo_key(todo_id))
        return {"message": DELETED}

    return {"message": NOTFOUND}

