"""Agent service for task processing and execution."""

import asyncio
from typing import Dict, Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.task import Task
from ..models.message import Message
from ..models.summary import Summary
from ..schemas.message import MessageCreate
from ..shared.task_types import TaskStatus, TaskType
from ..services.message_service import MessageService
from ..services.summary_service import SummaryService
from ..services.model_service import ModelService
from ..core.logging import get_logger

logger = get_logger(__name__)


class AgentService:
    """Service for AI agent task processing and execution."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.message_service = MessageService(db)
        self.summary_service = SummaryService(db)
        self.model_service = ModelService(db)
        self._active_tasks: Dict[UUID, asyncio.Task] = {}
    
    async def process_task(self, task_id: UUID) -> None:
        """Process a task by executing its steps and generating responses."""
        try:
            logger.info(f"Starting processing for task {task_id}")
            
            # Get the task
            task = await self.db.get(Task, task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return
            
            # Update task status to running
            task.status = TaskStatus.RUNNING
            await self.db.commit()
            
            # Process based on task type
            if task.task_type == TaskType.TEXT_GENERATION:
                await self._process_text_generation_task(task)
            elif task.task_type == TaskType.CODE_GENERATION:
                await self._process_code_generation_task(task)
            elif task.task_type == TaskType.DATA_ANALYSIS:
                await self._process_data_analysis_task(task)
            elif task.task_type == TaskType.CONTENT_CREATION:
                await self._process_content_creation_task(task)
            else:
                await self._process_general_task(task)
            
            # Mark task as completed
            task.status = TaskStatus.COMPLETED
            await self.db.commit()
            logger.info(f"Completed processing for task {task_id}")
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            # Update task status to failed
            task = await self.db.get(Task, task_id)
            if task:
                task.status = TaskStatus.FAILED
                await self.db.commit()
    
    async def _process_text_generation_task(self, task: Task) -> None:
        """Process text generation tasks."""
        # Get model recommendations
        recommendations = await self.model_service.get_model_recommendations(
            task_type=TaskType.TEXT_GENERATION,
            priority=task.priority,
            budget=task.budget
        )
        
        if not recommendations:
            raise ValueError("No suitable models found for text generation")
        
        # Use the top recommended model
        model_name = recommendations[0]["model"]["name"]
        
        # Generate response
        response_content = await self._generate_text_response(task.description, model_name)
        
        # Create response message
        message_data = MessageCreate(
            task_id=task.id,
            role="assistant",
            content=response_content,
            model_name=model_name,
            model_provider=recommendations[0]["model"]["provider"]
        )
        await self.message_service.create_message(message_data)
    
    async def _process_code_generation_task(self, task: Task) -> None:
        """Process code generation tasks."""
        # Get model recommendations
        recommendations = await self.model_service.get_model_recommendations(
            task_type=TaskType.CODE_GENERATION,
            priority=task.priority,
            budget=task.budget
        )
        
        if not recommendations:
            raise ValueError("No suitable models found for code generation")
        
        # Use the top recommended model
        model_name = recommendations[0]["model"]["name"]
        
        # Generate code
        code_content = await self._generate_code_response(task.description, model_name)
        
        # Create response message
        message_data = MessageCreate(
            task_id=task.id,
            role="assistant",
            content=code_content,
            model_name=model_name,
            model_provider=recommendations[0]["model"]["provider"]
        )
        await self.message_service.create_message(message_data)
    
    async def _process_data_analysis_task(self, task: Task) -> None:
        """Process data analysis tasks."""
        # Get model recommendations
        recommendations = await self.model_service.get_model_recommendations(
            task_type=TaskType.DATA_ANALYSIS,
            priority=task.priority,
            budget=task.budget
        )
        
        if not recommendations:
            raise ValueError("No suitable models found for data analysis")
        
        # Use the top recommended model
        model_name = recommendations[0]["model"]["name"]
        
        # Generate analysis
        analysis_content = await self._generate_analysis_response(task.description, model_name)
        
        # Create response message
        message_data = MessageCreate(
            task_id=task.id,
            role="assistant",
            content=analysis_content,
            model_name=model_name,
            model_provider=recommendations[0]["model"]["provider"]
        )
        await self.message_service.create_message(message_data)
    
    async def _process_content_creation_task(self, task: Task) -> None:
        """Process content creation tasks."""
        # Get model recommendations
        recommendations = await self.model_service.get_model_recommendations(
            task_type=TaskType.CONTENT_CREATION,
            priority=task.priority,
            budget=task.budget
        )
        
        if not recommendations:
            raise ValueError("No suitable models found for content creation")
        
        # Use the top recommended model
        model_name = recommendations[0]["model"]["name"]
        
        # Generate content
        content = await self._generate_content_response(task.description, model_name)
        
        # Create response message
        message_data = MessageCreate(
            task_id=task.id,
            role="assistant",
            content=content,
            model_name=model_name,
            model_provider=recommendations[0]["model"]["provider"]
        )
        await self.message_service.create_message(message_data)
    
    async def _process_general_task(self, task: Task) -> None:
        """Process general tasks."""
        # Get model recommendations
        recommendations = await self.model_service.get_model_recommendations(
            task_type=TaskType.TEXT_GENERATION,
            priority=task.priority,
            budget=task.budget
        )
        
        if not recommendations:
            raise ValueError("No suitable models found")
        
        # Use the top recommended model
        model_name = recommendations[0]["model"]["name"]
        
        # Generate response
        response_content = await self._generate_general_response(task.description, model_name)
        
        # Create response message
        message_data = MessageCreate(
            task_id=task.id,
            role="assistant",
            content=response_content,
            model_name=model_name,
            model_provider=recommendations[0]["model"]["provider"]
        )
        await self.message_service.create_message(message_data)
    
    async def _generate_text_response(self, prompt: str, model_name: str) -> str:
        """Generate text response using AI model."""
        # Simulate AI response generation
        await asyncio.sleep(1)  # Simulate processing time
        return f"Generated response for: {prompt[:50]}... (using {model_name})"
    
    async def _generate_code_response(self, prompt: str, model_name: str) -> str:
        """Generate code response using AI model."""
        # Simulate AI code generation
        await asyncio.sleep(2)  # Simulate processing time
        return f"# Generated code for: {prompt[:50]}...\n\n# Code implementation here (using {model_name})"
    
    async def _generate_analysis_response(self, prompt: str, model_name: str) -> str:
        """Generate data analysis response using AI model."""
        # Simulate AI analysis
        await asyncio.sleep(3)  # Simulate processing time
        return f"# Analysis for: {prompt[:50]}...\n\n# Data analysis results here (using {model_name})"
    
    async def _generate_content_response(self, prompt: str, model_name: str) -> str:
        """Generate content creation response using AI model."""
        # Simulate AI content creation
        await asyncio.sleep(2)  # Simulate processing time
        return f"# Created content for: {prompt[:50]}...\n\n# Content here (using {model_name})"
    
    async def _generate_general_response(self, prompt: str, model_name: str) -> str:
        """Generate general response using AI model."""
        # Simulate AI response
        await asyncio.sleep(1)  # Simulate processing time
        return f"Response to: {prompt[:50]}... (using {model_name})"
    
    async def cancel_task_processing(self, task_id: UUID) -> bool:
        """Cancel ongoing task processing."""
        if task_id in self._active_tasks:
            self._active_tasks[task_id].cancel()
            del self._active_tasks[task_id]
            return True
        return False
    
    async def get_active_tasks(self) -> Dict[UUID, Any]:
        """Get information about currently active tasks."""
        return {
            task_id: {
                "status": "running",
                "started_at": task.get_loop().time() if not task.done() else None
            }
            for task_id, task in self._active_tasks.items()
            if not task.done()
        }