"""Chat Engine - Orchestrates message sending, context building, and model invocation"""

from typing import Optional, Dict, Any
import logging

from agentos.core.chat.service import ChatService
from agentos.core.chat.context_builder import ContextBuilder, ContextBudget
from agentos.core.chat.commands import parse_command, get_registry
from agentos.core.coordinator.model_router import ModelRouter
from agentos.core.task.manager import TaskManager
from agentos.core.memory.service import MemoryService

# Import and register all slash commands
from agentos.core.chat.handlers import (
    register_summary_command,
    register_extract_command,
    register_task_command,
    register_model_command,
    register_context_command,
    register_stream_command,
    register_export_command
)

logger = logging.getLogger(__name__)


class ChatEngine:
    """Main engine for Chat Mode"""
    
    def __init__(
        self,
        chat_service: Optional[ChatService] = None,
        context_builder: Optional[ContextBuilder] = None,
        model_router: Optional[ModelRouter] = None,
        task_manager: Optional[TaskManager] = None,
        memory_service: Optional[MemoryService] = None
    ):
        """Initialize ChatEngine
        
        Args:
            chat_service: ChatService instance
            context_builder: ContextBuilder instance
            model_router: ModelRouter instance
            task_manager: TaskManager instance
            memory_service: MemoryService instance
        """
        self.chat_service = chat_service or ChatService()
        self.context_builder = context_builder or ContextBuilder()
        self.model_router = model_router or ModelRouter(policy={})
        self.task_manager = task_manager or TaskManager()
        self.memory_service = memory_service or MemoryService()
        
        # Register slash commands
        self._register_commands()
    
    def _register_commands(self):
        """Register all slash commands"""
        register_summary_command()
        register_extract_command()
        register_task_command()
        register_model_command()
        register_context_command()
        register_stream_command()
        register_export_command()
        logger.info("Registered slash commands")
    
    def send_message(
        self,
        session_id: str,
        user_input: str,
        stream: bool = False
    ) -> Dict[str, Any]:
        """Send a message and get response
        
        Args:
            session_id: Chat session ID
            user_input: User's input message
            stream: Whether to stream the response
        
        Returns:
            Response dictionary with message and metadata
        """
        logger.info(f"Processing message for session {session_id}")
        
        # 1. Save user message
        user_message = self.chat_service.add_message(
            session_id=session_id,
            role="user",
            content=user_input
        )
        
        # 2. Check if it's a slash command
        command, args, remaining = parse_command(user_input)
        
        if command:
            return self._execute_command(session_id, command, args, remaining)
        
        # 3. Normal message - build context
        session = self.chat_service.get_session(session_id)
        rag_enabled = session.metadata.get("rag_enabled", True)
        
        context_pack = self.context_builder.build(
            session_id=session_id,
            user_input=user_input,
            rag_enabled=rag_enabled,
            memory_enabled=True
        )
        
        # 4. Route to model
        model_route = session.metadata.get("model_route", "local")
        
        # 5. Get response from model
        if stream:
            # Return a stream generator
            return self._stream_response(session_id, context_pack, model_route)
        else:
            response_content = self._invoke_model(context_pack, model_route, session_id)
            
            # 6. Save assistant message
            assistant_message = self.chat_service.add_message(
                session_id=session_id,
                role="assistant",
                content=response_content,
                metadata={
                    "model_route": model_route,
                    "context_tokens": context_pack.metadata.get("total_tokens"),
                    "rag_chunks": len(context_pack.audit.get("rag_chunk_ids", [])),
                    "memory_facts": len(context_pack.audit.get("memory_ids", []))
                }
            )
            
            logger.info(f"Generated response for session {session_id}: {assistant_message.message_id}")
            
            return {
                "message_id": assistant_message.message_id,
                "content": response_content,
                "role": "assistant",
                "metadata": assistant_message.metadata,
                "context": context_pack.metadata
            }
    
    def _stream_response(
        self,
        session_id: str,
        context_pack: Any,
        model_route: str = "local"
    ):
        """Stream response from model

        Args:
            session_id: Session ID
            context_pack: ContextPack with assembled messages
            model_route: "local" or "cloud"

        Yields:
            Text chunks
        """
        logger.info(f"Streaming {model_route} model response")

        try:
            from agentos.core.chat.adapters import get_adapter

            # Get session to read provider/model preferences
            session = self.chat_service.get_session(session_id)

            logger.info(f"Session metadata: {session.metadata}")

            # Determine provider from session metadata (with fallback)
            provider = session.metadata.get("provider")
            if not provider:
                provider = "ollama" if model_route == "local" else "openai"
                logger.warning(f"No provider in metadata, using fallback: {provider}")

            # Get model name if specified
            model = session.metadata.get("model")

            logger.info(f"Using provider: {provider}, model: {model}")

            adapter = get_adapter(provider, model)
            
            # Check health
            is_healthy, status = adapter.health_check()
            if not is_healthy:
                yield f"⚠️ Model unavailable: {status}"
                return
            
            # Collect full response for saving
            full_response = []
            
            # Stream response
            for chunk in adapter.generate_stream(
                messages=context_pack.messages,
                temperature=0.7,
                max_tokens=2000
            ):
                full_response.append(chunk)
                yield chunk
            
            # Save complete message
            response_content = "".join(full_response)
            self.chat_service.add_message(
                session_id=session_id,
                role="assistant",
                content=response_content,
                metadata={
                    "model_route": model_route,
                    "context_tokens": context_pack.metadata.get("total_tokens"),
                    "streamed": True
                }
            )
        
        except Exception as e:
            logger.error(f"Streaming failed: {e}", exc_info=True)
            yield f"\n\n⚠️ Streaming error: {str(e)}"
    
    def _execute_command(
        self,
        session_id: str,
        command: str,
        args: list,
        remaining: Optional[str]
    ) -> Dict[str, Any]:
        """Execute a slash command
        
        Args:
            session_id: Session ID
            command: Command name
            args: Command arguments
            remaining: Remaining text after command
        
        Returns:
            Command result as response
        """
        logger.info(f"Executing command /{command} in session {session_id}")
        
        # Build command context
        context = {
            "session_id": session_id,
            "chat_service": self.chat_service,
            "task_manager": self.task_manager,
            "memory_service": self.memory_service
        }
        
        # Execute command
        registry = get_registry()
        result = registry.execute(command, args, context)
        
        # Save command result as assistant message
        if result.should_display:
            self.chat_service.add_message(
                session_id=session_id,
                role="assistant",
                content=result.message,
                metadata={
                    "command": f"/{command}",
                    "command_success": result.success,
                    "command_data": result.data
                }
            )
        
        return {
            "message_id": None,
            "content": result.message,
            "role": "assistant",
            "metadata": {
                "command": f"/{command}",
                "success": result.success
            },
            "context": {}
        }
    
    def _invoke_model(
        self,
        context_pack: Any,
        model_route: str = "local",
        session_id: Optional[str] = None
    ) -> str:
        """Invoke model to get response

        Args:
            context_pack: ContextPack with assembled messages
            model_route: "local" or "cloud"
            session_id: Optional session ID to get provider/model preferences

        Returns:
            Model response text
        """
        logger.info(f"Invoking {model_route} model")

        try:
            from agentos.core.chat.adapters import get_adapter

            messages = context_pack.messages

            # Determine provider and model from session metadata (with fallback)
            provider = None
            model = None

            if session_id:
                session = self.chat_service.get_session(session_id)
                logger.info(f"Session metadata: {session.metadata}")
                provider = session.metadata.get("provider")
                model = session.metadata.get("model")

            # Fallback to default providers
            if not provider:
                provider = "ollama" if model_route == "local" else "openai"
                logger.warning(f"No provider in metadata, using fallback: {provider}")

            logger.info(f"Using provider: {provider}, model: {model}")

            # Get adapter
            adapter = get_adapter(provider, model)
            
            # Check health
            is_healthy, status = adapter.health_check()
            if not is_healthy:
                return f"⚠️ Model unavailable: {status}\n\nPlease configure the model or try switching with `/model`"
            
            # Generate response
            response = adapter.generate(
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=False
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Model invocation failed: {e}", exc_info=True)
            return f"⚠️ Model invocation failed: {str(e)}"
    
    def create_session(
        self,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a new chat session
        
        Args:
            title: Session title
            metadata: Session metadata
        
        Returns:
            Session ID
        """
        session = self.chat_service.create_session(
            title=title,
            metadata=metadata
        )
        
        logger.info(f"Created new chat session: {session.session_id}")
        return session.session_id
