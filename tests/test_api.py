# tests/test_api.py
import os
import pytest
import pytest_asyncio
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock, ANY

# Ensure correct path for imports if running pytest from root
import sys
# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# Now import from the correct location
from market_research.api.openai_api import OpenAIAPI
from market_research.api.api_tool_factory import ApiToolFactory
from openai import OpenAIError, APIConnectionError # Import relevant OpenAI errors
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

# --- Fixtures ---

# Fixture for ApiToolFactory (can be empty for these tests)
@pytest.fixture
def mock_tool_factory():
    return ApiToolFactory() # Or a MagicMock if preferred

# Fixture for a mocked OpenAI client
@pytest_asyncio.fixture
async def mock_openai_client():
    mock_client = MagicMock()
    # Mock the chat.completions.create method to be an AsyncMock
    mock_client.chat.completions.create = AsyncMock()
    return mock_client

# Fixture for OpenAIAPI instance with mocked client and factory
@pytest_asyncio.fixture
async def openai_api_instance(mock_tool_factory):
    # Temporarily set env var for testing initialization
    os.environ["OPENAI_API_KEY"] = "test_key_from_env"
    # Use patch context manager for the OpenAI client instantiation
    with patch('market_research.api.openai_api.OpenAI', return_value=MagicMock()) as mock_openai_constructor:
        api = OpenAIAPI(tool_factory=mock_tool_factory, model=API_MODEL)
        # Replace the client instance created inside __init__ with our finer-grained mock
        api.client = MagicMock()
        api.client.chat.completions.create = AsyncMock() # Ensure the method is async mock
        yield api # Use yield for fixture setup/teardown
    # Clean up env var if needed
    del os.environ["OPENAI_API_KEY"]


# --- Helper Function to Create Mock Completion ---
def create_mock_completion(content: str = None, tool_calls: list = None, finish_reason="stop") -> ChatCompletion:
    """Creates a mock ChatCompletion object."""
    message_dict = {"role": "assistant"}
    if content:
        message_dict["content"] = content
    if tool_calls:
        message_dict["tool_calls"] = tool_calls # Assuming tool_calls is already in the correct structure

    # Create mock objects matching the structure expected by the code
    mock_tool_calls = None
    if tool_calls:
         mock_tool_calls = []
         for tc_data in tool_calls:
              # Ensure function attribute is present only if type is 'function'
              func_mock = None
              if tc_data.get("type") == "function" and tc_data.get("function"):
                   func_mock = MagicMock(name=tc_data["function"]["name"], arguments=tc_data["function"]["arguments"])
              mock_tool_calls.append(
                   MagicMock(id=tc_data.get("id"), type=tc_data.get("type"), function=func_mock)
              )

    message = ChatCompletionMessage(
        role="assistant",
        content=content,
        tool_calls=mock_tool_calls
    )
    choice = Choice(index=0, message=message, finish_reason=finish_reason, logprobs=None) # Added logprobs=None
    completion = ChatCompletion(
        id="chatcmpl-mock-" + os.urandom(4).hex(),
        choices=[choice],
        created=1677652288, # Example timestamp
        model=API_MODEL,
        object="chat.completion",
        system_fingerprint="fp_mock", # Example fingerprint
        usage=None # Usage can be None or a mock object
    )
    return completion


# --- Test Cases ---

@pytest.mark.asyncio
async def test_api_initialization_success_env(mock_tool_factory):
    """Test successful initialization using environment variable."""
    os.environ["OPENAI_API_KEY"] = "test_key_123"
    try:
        # Patch the OpenAI client constructor during init
        with patch('market_research.api.openai_api.OpenAI') as mock_constructor:
            api = OpenAIAPI(tool_factory=mock_tool_factory)
            assert api.api_key == "test_key_123"
            mock_constructor.assert_called_once_with(api_key="test_key_123")
            assert api.model == API_MODEL # Default model
            assert api.tool_factory is mock_tool_factory
    finally:
        del os.environ["OPENAI_API_KEY"]

@pytest.mark.asyncio
async def test_api_initialization_success_arg():
    """Test successful initialization using direct api_key argument."""
    with patch('market_research.api.openai_api.OpenAI') as mock_constructor:
        api = OpenAIAPI(api_key="direct_key_456")
        assert api.api_key == "direct_key_456"
        mock_constructor.assert_called_once_with(api_key="direct_key_456")

@pytest.mark.asyncio
async def test_api_initialization_success_file(tmp_path):
    """Test successful initialization using api_key file path."""
    key_file = tmp_path / "api_key.txt"
    key_file.write_text("file_key_789")
    with patch('market_research.api.openai_api.OpenAI') as mock_constructor:
        api = OpenAIAPI(api_key=str(key_file))
        assert api.api_key == "file_key_789"
        mock_constructor.assert_called_once_with(api_key="file_key_789")


@pytest.mark.asyncio
async def test_api_initialization_failure_no_key():
    """Test initialization failure when no API key is found."""
    # Ensure env var is not set
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    with pytest.raises(ValueError, match="No valid OpenAI API key found"):
        OpenAIAPI() # No key provided

# --- Tests for generate_text_with_tools ---

@pytest.mark.asyncio
async def test_generate_text_simple(openai_api_instance):
    """Test basic text generation without tools."""
    messages = [{"role": "user", "content": "Hello"}]
    expected_response = "Hi there!"
    mock_completion = create_mock_completion(content=expected_response)
    openai_api_instance.client.chat.completions.create.return_value = mock_completion

    response = await openai_api_instance.generate_text_with_tools(messages=messages)

    assert response == expected_response
    openai_api_instance.client.chat.completions.create.assert_awaited_once()
    call_args = openai_api_instance.client.chat.completions.create.call_args
    assert call_args.kwargs['messages'] == messages
    assert call_args.kwargs['model'] == API_MODEL # Default
    assert "web_search_preview" in [t['type'] for t in call_args.kwargs['tools']] # Check web search tool is present
    assert call_args.kwargs['tool_choice'] == "auto"


@pytest.mark.asyncio
async def test_generate_text_with_web_search_implicit(openai_api_instance):
    """Test generation where web search is implicitly used (no tool_call response)."""
    messages = [{"role": "user", "content": "What's the weather?"}]
    expected_response = "The weather is sunny (data from web search)."
    # Simulate a response that used web search internally, returning content directly
    # The current implementation checks for annotations, let's mock that
    mock_message = MagicMock()
    mock_message.role = "assistant"
    mock_message.content = expected_response
    # Add mock annotations to signal web search usage
    mock_message.annotations = [{"type": "web_search_result", "data": "..."}]
    mock_message.tool_calls = None # No explicit tool calls returned

    mock_choice = Choice(index=0, message=mock_message, finish_reason="stop", logprobs=None)
    mock_completion = ChatCompletion(
        id="chatcmpl-mock-web", choices=[mock_choice], created=1, model=API_MODEL, object="chat.completion"
    )

    openai_api_instance.client.chat.completions.create.return_value = mock_completion

    response = await openai_api_instance.generate_text_with_tools(messages=messages)

    assert response == expected_response
    openai_api_instance.client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_text_api_error(openai_api_instance):
    """Test handling of an API error during generation."""
    messages = [{"role": "user", "content": "Trigger error"}]
    error_message = "API connection failed"
    openai_api_instance.client.chat.completions.create.side_effect = APIConnectionError(message=error_message, request=None) # Use a specific error

    response = await openai_api_instance.generate_text_with_tools(messages=messages)

    assert "[Error: An unexpected error occurred: APIConnectionError]" in response
    openai_api_instance.client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_text_timeout(openai_api_instance):
    """Test handling of an asyncio timeout during the API call."""
    messages = [{"role": "user", "content": "Trigger timeout"}]

    # Make the mocked API call sleep longer than the timeout used in generate_text_with_tools
    async def long_call(*args, **kwargs):
        await asyncio.sleep(2) # Assume timeout in generate_text_with_tools is less than 2s
        return create_mock_completion(content="Should not return")

    # We need to patch asyncio.wait_for inside the function OR configure the mock correctly
    # It's easier to just make the underlying call raise TimeoutError
    openai_api_instance.client.chat.completions.create.side_effect = asyncio.TimeoutError

    # Set a shorter timeout for the test itself if needed, but the code has internal timeout
    response = await openai_api_instance.generate_text_with_tools(messages=messages)

    # The code catches the TimeoutError from asyncio.wait_for(completion_task, ...)
    assert response == "[Error: API call timed out]"
    openai_api_instance.client.chat.completions.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_text_max_iterations(openai_api_instance, mock_tool_factory):
    """Test reaching max tool iterations."""
    messages = [{"role": "user", "content": "Use a tool repeatedly"}]
    max_iterations = 2 # Set a low limit for testing
    tool_name = "dummy_tool"

    # Register a dummy tool
    def dummy_tool_func(param: str): return {"status": "ok", "param_received": param}
    mock_tool_factory.register_tool(dummy_tool_func, tool_name, "A dummy tool", {"type": "object", "properties": {"param": {"type": "string"}}})

    # --- Mock API Responses ---
    # Iteration 1: Request tool call
    tool_call_1 = {
        "id": "call_1",
        "type": "function",
        "function": {"name": tool_name, "arguments": '{"param": "value1"}'}
    }
    completion_1 = create_mock_completion(tool_calls=[tool_call_1])

    # Iteration 2: Request tool call again
    tool_call_2 = {
        "id": "call_2",
        "type": "function",
        "function": {"name": tool_name, "arguments": '{"param": "value2"}'}
    }
    completion_2 = create_mock_completion(tool_calls=[tool_call_2])

    # Final assistant message (after last tool result is sent) - this might not be reached if max_iterations logic stops before final call
    # Let's assume the loop breaks *after* processing the second tool call result but *before* getting a final content response.
    final_content_if_reached = "Okay, I used the tool twice."
    # completion_final = create_mock_completion(content=final_content_if_reached) # This won't be returned if max_iterations hits


    # Configure the mock client to return responses in sequence
    openai_api_instance.client.chat.completions.create.side_effect = [
        completion_1,
        completion_2,
        # If the loop continued, it would make a third call. Since max_iterations=2, it stops.
    ]

    # --- Mock Tool Factory Dispatch ---
    # Patch the dispatch method
    with patch.object(mock_tool_factory, 'dispatch_tool', side_effect=[
        '{"status": "ok", "param_received": "value1"}', # Result for call_1
        '{"status": "ok", "param_received": "value2"}', # Result for call_2
    ]) as mock_dispatch:

        response = await openai_api_instance.generate_text_with_tools(
            messages=messages,
            max_tool_iterations=max_iterations
        )

    # Assertions
    assert openai_api_instance.client.chat.completions.create.call_count == max_iterations
    assert mock_dispatch.call_count == max_iterations
    # Check the expected warning message about max iterations
    assert f"Max tool iterations ({max_iterations}) reached" in response
    # The response might include the last tool result or a generic error message
    assert "Error: Max tool iterations reached" in response # Check for the primary error text
    assert "value2" in response # Check if last tool result snippet is included as per the code


def test_convert_message_to_dict_simple_content(openai_api_instance):
    """Test _convert_message_to_dict with simple content."""
    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.role = "assistant"
    mock_message.content = "Simple text"
    mock_message.tool_calls = None
    mock_message.annotations = None

    result = openai_api_instance._convert_message_to_dict(mock_message)

    assert result == {"role": "assistant", "content": "Simple text"}


def test_convert_message_to_dict_with_tool_call(openai_api_instance):
    """Test _convert_message_to_dict with a function tool call."""
    tool_call_mock = MagicMock()
    tool_call_mock.id = "tc_123"
    tool_call_mock.type = "function"
    tool_call_mock.function = MagicMock(name="get_weather", arguments='{"location": "Paris"}')

    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.role = "assistant"
    mock_message.content = None
    mock_message.tool_calls = [tool_call_mock]
    mock_message.annotations = None


    result = openai_api_instance._convert_message_to_dict(mock_message)

    expected_tool_call = {
        "id": "tc_123",
        "type": "function",
        "function": {"name": "get_weather", "arguments": '{"location": "Paris"}'}
    }
    assert result == {"role": "assistant", "content": None, "tool_calls": [expected_tool_call]}


def test_convert_message_to_dict_with_annotations(openai_api_instance):
    """Test _convert_message_to_dict with annotations (simulating web search)."""
    # Mock annotations (structure might vary, use a simple example)
    mock_annotations = [{"type": "web_search_result", "source": "example.com"}]

    mock_message = MagicMock(spec=ChatCompletionMessage)
    mock_message.role = "assistant"
    mock_message.content = "Content with web results."
    mock_message.tool_calls = None
    # Assign annotations directly if the object supports it
    mock_message.annotations = mock_annotations

    result = openai_api_instance._convert_message_to_dict(mock_message)

    # The exact structure depends on how annotations are handled/serialized
    assert result["role"] == "assistant"
    assert result["content"] == "Content with web results."
    assert "annotations" in result
    assert result["annotations"] == mock_annotations # Assuming direct assignment works