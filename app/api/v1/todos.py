from typing import Dict, List

from fastapi import APIRouter, Security
from app.shared.rate_limiter import limiter
from app.models.RequestsTodos import Todo
from app.models.ResponseTodos import TodosBase
from app.shared.messages import NOTFOUND, DELETED, UPDATED, CREATED
from app.services.todo_service import TodoService
from app.shared.auth import api_verifier
router = APIRouter(prefix="/todos", tags=["todos"])

service = TodoService()


@router.get("/", response_model=TodosBase)
@limiter.limit("5/minute")
async def get_todos(token: str = Security(api_verifier)) -> Dict[str, List[Todo]]:
    """
    Retrieve a list of todos.

    This endpoint fetches and returns all the todos available.

    :return: A dictionary containing the todos.
    :rtype: dict
    """
    todos = await service.get_todos()
    return {"todos": todos}


@router.get("/{todo_id}", response_model=None)
@limiter.limit("5/minute")
async def get_todo(todo_id: int,token: str = Security(api_verifier))-> Dict[str, Todo|str]:
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
    todo = await service.get_todo(todo_id)
    if todo is not None:
        return {"todo": todo}

    return {"message": NOTFOUND}


@router.post("/", response_model=None)
@limiter.limit("5/minute")
async def create_todo(todo: Todo,token: str = Security(api_verifier))-> Dict[str, str]:
    """
    Handles the creation of a new todo item and appends it to the existing list of todos.

    :param todo: The Todo object containing the details of the todo item to be created.
    :return: A dictionary indicating the success message upon todo creation.
    """
    await service.create_todo(todo)
    return {"message": CREATED}


@router.put("/{todo_id}", response_model=None)
@limiter.limit("5/minute")
async def update_todo(todo_id: int, todo_obj: Todo,token: str = Security(api_verifier))-> Dict[str, str]:
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
        return {"todo": updated}
    return {"message": NOTFOUND}



@router.delete("/{todo_id}", response_model=None)
@limiter.limit("5/minute")
async def delete_todo(todo_id: int,token: str = Security(api_verifier)) -> Dict[str, str]:
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
        return {"message": DELETED}

    return {"message": NOTFOUND}

