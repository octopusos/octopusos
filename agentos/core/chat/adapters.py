"""Chat model adapters - Wrapper for invoking LLMs in Chat Mode"""

from typing import List, Dict, Any, Optional, Iterator
import logging
import os

logger = logging.getLogger(__name__)


class ChatModelAdapter:
    """Base class for chat model adapters"""
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> str:
        """Generate response from messages
        
        Args:
            messages: List of messages in OpenAI format
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
        
        Returns:
            Generated text
        """
        raise NotImplementedError
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Iterator[str]:
        """Generate response with streaming
        
        Args:
            messages: List of messages in OpenAI format
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Yields:
            Text chunks
        """
        raise NotImplementedError
    
    def health_check(self) -> tuple[bool, str]:
        """Check if adapter is available
        
        Returns:
            (is_available, status_message)
        """
        raise NotImplementedError


class OllamaChatAdapter(ChatModelAdapter):
    """Ollama adapter for Chat Mode (also used for llama.cpp and LM Studio)"""

    def __init__(self, model: str = "qwen2.5:14b", base_url: Optional[str] = None):
        """Initialize Ollama adapter

        Args:
            model: Model name
            base_url: Base URL (defaults to OLLAMA_HOST env var or http://localhost:11434)
        """
        self.model = model
        self.host = base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> str:
        """Generate response using Ollama"""
        try:
            import requests
        except ImportError:
            logger.error("requests library not installed")
            return "⚠️ Error: requests library required for Ollama"
        
        try:
            url = f"{self.host}/api/chat"
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get("message", {}).get("content", "")
        
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return f"⚠️ Ollama error: {str(e)}"
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Iterator[str]:
        """Generate response with streaming"""
        try:
            import requests
        except ImportError:
            yield "⚠️ Error: requests library required"
            return
        
        try:
            url = f"{self.host}/api/chat"
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = requests.post(url, json=payload, stream=True, timeout=60)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = line.decode('utf-8')
                        import json
                        chunk = json.loads(data)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except:
                        continue
        
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            yield f"⚠️ Ollama error: {str(e)}"
    
    def health_check(self) -> tuple[bool, str]:
        """Check Ollama availability"""
        try:
            import requests
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                
                # Check if our model exists
                model_exists = any(
                    name == self.model or name.startswith(f"{self.model}:")
                    for name in model_names
                )
                
                if model_exists:
                    return True, f"✓ Ollama ({self.model})"
                else:
                    return False, f"✗ Model {self.model} not found"
            
            return False, f"✗ Ollama service error ({response.status_code})"
        
        except Exception as e:
            return False, f"✗ Ollama unreachable: {str(e)}"


class OpenAIChatAdapter(ChatModelAdapter):
    """OpenAI adapter for Chat Mode"""
    
    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """Initialize OpenAI adapter
        
        Args:
            model: OpenAI model name
            api_key: API key (defaults to OPENAI_API_KEY env var)
            base_url: Base URL (for OpenAI-compatible services)
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.base_url = base_url
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        stream: bool = False
    ) -> str:
        """Generate response using OpenAI"""
        try:
            import openai
        except ImportError:
            logger.error("openai library not installed")
            return "⚠️ Error: openai library required"

        # Only check API key for actual OpenAI (not for local services with custom base_url)
        if not self.api_key and not self.base_url:
            return "⚠️ Error: OPENAI_API_KEY not configured"
        
        try:
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            logger.info(f"Creating OpenAI client with base_url={self.base_url}, model={self.model}")

            client = openai.OpenAI(**client_kwargs)

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}", exc_info=True)
            return f"⚠️ OpenAI error: {str(e)}"
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Iterator[str]:
        """Generate response with streaming"""
        try:
            import openai
        except ImportError:
            yield "⚠️ Error: openai library required"
            return

        # Only check API key for actual OpenAI (not for local services with custom base_url)
        if not self.api_key and not self.base_url:
            yield "⚠️ Error: OPENAI_API_KEY not configured"
            return
        
        try:
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url

            logger.info(f"Creating OpenAI client for streaming with base_url={self.base_url}, model={self.model}")

            client = openai.OpenAI(**client_kwargs)

            stream = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}", exc_info=True)
            yield f"⚠️ OpenAI error: {str(e)}"
    
    def health_check(self) -> tuple[bool, str]:
        """Check OpenAI availability"""
        # For custom base_url (llama.cpp, lmstudio), check endpoint instead of API key
        if self.base_url:
            try:
                import requests
                # Try to list models
                health_url = self.base_url.replace("/v1", "/health") if "/v1" in self.base_url else f"{self.base_url}/health"
                logger.debug(f"Health check URL: {health_url}")
                response = requests.get(health_url, timeout=5)
                logger.debug(f"Health check status: {response.status_code}")
                if response.status_code == 200:
                    return True, f"✓ Local Model ({self.model})"

                # Fallback: try models endpoint
                models_url = f"{self.base_url}/models"
                logger.debug(f"Models check URL: {models_url}")
                response = requests.get(models_url, timeout=5)
                logger.debug(f"Models check status: {response.status_code}")
                if response.status_code == 200:
                    return True, f"✓ Local Model ({self.model})"

                logger.error(f"Health check failed: {response.status_code} - {response.text[:200]}")
                return False, f"✗ Service error ({response.status_code})"
            except Exception as e:
                logger.error(f"Health check exception: {e}", exc_info=True)
                return False, f"✗ Service unreachable: {str(e)}"

        # For OpenAI API
        if not self.api_key:
            return False, "✗ OPENAI_API_KEY not configured"

        # Basic validation
        if not self.api_key.startswith("sk-"):
            return False, "✗ Invalid API key format"

        return True, f"✓ OpenAI ({self.model})"


def get_adapter(provider: str, model: Optional[str] = None) -> ChatModelAdapter:
    """Get chat model adapter

    Args:
        provider: Provider ID (e.g., "ollama", "llamacpp", "llamacpp:instance-name")
        model: Optional model name override

    Returns:
        ChatModelAdapter instance
    """
    # Parse provider:instance format
    if ":" in provider:
        provider_type, instance_id = provider.split(":", 1)
    else:
        provider_type = provider
        instance_id = None

    # Handle Ollama
    if provider_type == "ollama":
        model = model or "qwen2.5:14b"
        base_url = None

        # Get actual endpoint from registry
        try:
            from agentos.providers.registry import ProviderRegistry
            registry = ProviderRegistry.get_instance()

            if instance_id:
                # Specific instance requested
                provider_obj = registry.get(f"ollama:{instance_id}")
                if provider_obj and hasattr(provider_obj, 'endpoint'):
                    base_url = provider_obj.endpoint
                    logger.info(f"Using ollama instance endpoint: {base_url}")
            else:
                # No instance specified - find any available ollama instance
                from agentos.providers.base import ProviderState
                import asyncio
                all_providers = registry.list_all()
                for p in all_providers:
                    if p.id.startswith("ollama:") or p.id == "ollama":
                        status = p.get_cached_status()
                        if not status:
                            try:
                                status = asyncio.run(p.probe())
                            except:
                                continue

                        if status and status.state == ProviderState.READY:
                            base_url = p.endpoint
                            logger.info(f"Auto-selected ollama instance: {p.id} at {base_url}")
                            break

            if not base_url:
                base_url = "http://127.0.0.1:11434"
                logger.warning(f"No ollama instance found, using default: {base_url}")

        except Exception as e:
            logger.warning(f"Failed to get ollama endpoint: {e}", exc_info=True)
            base_url = "http://127.0.0.1:11434"

        return OllamaChatAdapter(model=model, base_url=base_url)

    # Handle llama.cpp (OpenAI-compatible)
    elif provider_type == "llamacpp":
        model = model or "local-model"
        base_url = None

        # Get actual endpoint from registry
        try:
            from agentos.providers.registry import ProviderRegistry
            registry = ProviderRegistry.get_instance()

            if instance_id:
                # Specific instance requested
                provider_obj = registry.get(f"llamacpp:{instance_id}")
                if provider_obj and hasattr(provider_obj, 'endpoint'):
                    base_url = provider_obj.endpoint
                    logger.info(f"Using llamacpp instance endpoint: {base_url}")
            else:
                # No instance specified - find instance that has this model
                from agentos.providers.base import ProviderState
                import asyncio
                import requests
                all_providers = registry.list_all()

                # Filter llamacpp instances
                llamacpp_providers = [p for p in all_providers if p.id.startswith("llamacpp:")]

                # If model is specified, find instance that has this model
                if model:
                    logger.info(f"Looking for llamacpp instance with model: {model}")
                    for p in llamacpp_providers:
                        # Check if provider is ready
                        status = p.get_cached_status()
                        if not status:
                            try:
                                status = asyncio.run(p.probe())
                            except:
                                continue

                        if not status or status.state != ProviderState.READY:
                            continue

                        # Check if this instance has the model
                        try:
                            response = requests.get(f"{p.endpoint}/v1/models", timeout=2)
                            if response.status_code == 200:
                                data = response.json()
                                models = [m.get("id") for m in data.get("data", [])]
                                logger.debug(f"Instance {p.id} has models: {models}")

                                if model in models:
                                    base_url = p.endpoint
                                    logger.info(f"✓ Found model '{model}' in instance: {p.id} at {base_url}")
                                    break
                        except Exception as e:
                            logger.debug(f"Failed to check models for {p.id}: {e}")
                            continue

                # Fallback: select first available instance
                if not base_url:
                    logger.warning(f"Model '{model}' not found in any instance, using first available")
                    for p in llamacpp_providers:
                        status = p.get_cached_status()
                        if not status:
                            try:
                                status = asyncio.run(p.probe())
                            except:
                                continue

                        if status and status.state == ProviderState.READY:
                            base_url = p.endpoint
                            logger.info(f"Auto-selected llamacpp instance: {p.id} at {base_url}")
                            break

            if not base_url:
                # Fallback to default port
                base_url = "http://127.0.0.1:8080"
                logger.warning(f"No llamacpp instance found, using default: {base_url}")

        except Exception as e:
            logger.warning(f"Failed to get llamacpp endpoint: {e}", exc_info=True)
            base_url = "http://127.0.0.1:8080"

        # llama.cpp uses OpenAI-compatible API
        return OpenAIChatAdapter(model=model, base_url=f"{base_url}/v1", api_key="dummy")

    # Handle LM Studio (OpenAI-compatible)
    elif provider_type == "lmstudio":
        model = model or "local-model"
        base_url = None

        # Get actual endpoint from registry
        try:
            from agentos.providers.registry import ProviderRegistry
            registry = ProviderRegistry.get_instance()

            if instance_id:
                # Specific instance requested
                provider_obj = registry.get(f"lmstudio:{instance_id}")
                if provider_obj and hasattr(provider_obj, 'endpoint'):
                    base_url = provider_obj.endpoint
                    logger.info(f"Using lmstudio instance endpoint: {base_url}")
            else:
                # No instance specified - find any available lmstudio instance
                from agentos.providers.base import ProviderState
                import asyncio
                all_providers = registry.list_all()
                for p in all_providers:
                    if p.id.startswith("lmstudio:") or p.id == "lmstudio":
                        status = p.get_cached_status()
                        if not status:
                            try:
                                status = asyncio.run(p.probe())
                            except:
                                continue

                        if status and status.state == ProviderState.READY:
                            base_url = p.endpoint
                            logger.info(f"Auto-selected lmstudio instance: {p.id} at {base_url}")
                            break

            if not base_url:
                base_url = "http://127.0.0.1:1234"
                logger.warning(f"No lmstudio instance found, using default: {base_url}")

        except Exception as e:
            logger.warning(f"Failed to get lmstudio endpoint: {e}", exc_info=True)
            base_url = "http://127.0.0.1:1234"

        return OpenAIChatAdapter(model=model, base_url=f"{base_url}/v1", api_key="dummy")

    # Handle OpenAI
    elif provider_type == "openai" or provider_type == "cloud":
        model = model or "gpt-4o-mini"
        return OpenAIChatAdapter(model=model)

    else:
        raise ValueError(f"Unknown provider: {provider}")
