"""Messages API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db_session
from ...core.logging import get_logger
from ...schemas.message import (
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageListResponse,
)
from ...services.message_service import MessageService
from ...shared.task_types import Role

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=MessageListResponse)
async def list_messages(
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of messages to return"),
    task_id: Optional[UUID] = Query(None, description="Filter by task ID"),
    role: Optional[Role] = Query(None, description="Filter by message role"),
    search: Optional[str] = Query(None, description="Search in message content"),
    db: AsyncSession = Depends(get_db_session),
) -> MessageListResponse:
    """List messages with optional filtering."""
    message_service = MessageService(db)
    
    messages, total = await message_service.list_messages(
        skip=skip,
        limit=limit,
        task_id=task_id,
        role=role,
        search=search,
    )
    
    return MessageListResponse(
        messages=[MessageResponse.model_validate(message) for message in messages],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Get a specific message by ID."""
    message_service = MessageService(db)
    
    message = await message_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return MessageResponse.model_validate(message)


@router.put("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: UUID,
    message_data: MessageUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """Update a message."""
    message_service = MessageService(db)
    
    message = await message_service.update_message(message_id, message_data)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return MessageResponse.model_validate(message)


@router.delete("/{message_id}")
async def delete_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Delete a message."""
    message_service = MessageService(db)
    
    success = await message_service.delete_message(message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {"message": "Message deleted successfully"}


@router.get("/{message_id}/content")
async def get_message_content(
    message_id: UUID,
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get message content blocks."""
    message_service = MessageService(db)
    
    message = await message_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    content_blocks = message.content
    
    # Filter by content type if specified
    if content_type:
        content_blocks = [
            block for block in content_blocks
            if isinstance(block, dict) and block.get("type") == content_type
        ]
    
    return {
        "message_id": str(message_id),
        "content_blocks": content_blocks,
        "total_blocks": len(content_blocks),
    }


@router.get("/{message_id}/text")
async def get_message_text(
    message_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get plain text content from a message."""
    message_service = MessageService(db)
    
    message = await message_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return {
        "message_id": str(message_id),
        "text_content": message.text_content,
        "word_count": len(message.text_content.split()) if message.text_content else 0,
    }


@router.get("/{message_id}/tool-uses")
async def get_message_tool_uses(
    message_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get tool use content blocks from a message."""
    message_service = MessageService(db)
    
    message = await message_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    tool_uses = message.get_tool_uses()
    
    return {
        "message_id": str(message_id),
        "tool_uses": tool_uses,
        "total_tool_uses": len(tool_uses),
    }


@router.get("/{message_id}/images")
async def get_message_images(
    message_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Get image content blocks from a message."""
    message_service = MessageService(db)
    
    message = await message_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    images = message.get_images()
    
    return {
        "message_id": str(message_id),
        "images": images,
        "total_images": len(images),
    }


@router.post("/{message_id}/mark-processed")
async def mark_message_processed(
    message_id: UUID,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Mark a message as processed."""
    message_service = MessageService(db)
    
    message = await message_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.mark_processed()
    await message_service.update_message(message_id, {})
    
    return {"message": "Message marked as processed"}


@router.post("/{message_id}/mark-failed")
async def mark_message_failed(
    message_id: UUID,
    error_message: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Mark a message processing as failed."""
    message_service = MessageService(db)
    
    message = await message_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.mark_processing_failed(error_message)
    await message_service.update_message(message_id, {})
    
    return {"message": "Message marked as failed"}


@router.put("/{message_id}/token-usage")
async def update_message_token_usage(
    message_id: UUID,
    input_tokens: int,
    output_tokens: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Update token usage for a message."""
    message_service = MessageService(db)
    
    message = await message_service.get_message(message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    message.update_token_usage(input_tokens, output_tokens)
    await message_service.update_message(message_id, {})
    
    return {
        "message": "Token usage updated",
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }