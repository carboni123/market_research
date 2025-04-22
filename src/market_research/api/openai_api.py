# src/market_research/api/openai_api.py
import asyncio
from openai import OpenAI, BadRequestError
from pydantic import BaseModel
from .api import API # Assuming api.py is in the same directory
from .api_tool_factory import ApiToolFactory # Assuming api_tool_factory.py is in the same directory
from typing import List, Dict, Any, Optional
import logging
import json
import traceback

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
module_logger = logging.getLogger(__name__)


class OpenAIAPI(API):
    """
    Concrete class for interactions with the OpenAI API, enhanced for tool use
    via an ApiToolFactory and including built-in web search.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini-search-preview", # Default model supports web search
        tool_factory: Optional[ApiToolFactory] = None
    ):
        """
        Initializes the OpenAI API object.

        Args:
            api_key: OpenAI API key string or path to file containing the key.
                     Defaults to environment variable OPENAI_API_KEY.
            model: The default OpenAI model to use (must support web_search_preview, e.g., gpt-4o, gpt-4o-mini).
            tool_factory: An instance of ApiToolFactory for dynamic *custom* tool handling.
        """
        super().__init__(api_key, api_env="OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "No valid OpenAI API key found. Provide it via api_key argument, "
                "file path, or set OPENAI_API_KEY environment variable."
            )
        self.client = OpenAI(api_key=self.api_key)

        self.model = model
        self.tool_factory = tool_factory

        if self.tool_factory:
             module_logger.info(f"OpenAI API initialized with model: {self.model}, ApiToolFactory, and built-in web_search_preview.")
        else:
             module_logger.info(f"OpenAI API initialized with model: {self.model} and built-in web_search_preview. No ApiToolFactory provided.")

    async def generate_text_with_tools(
        self,
        messages: List[Dict[str, Any]],
        expect_json: BaseModel,
        model: Optional[str] = None,
        max_tool_iterations: int = 5,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Generates text using the OpenAI API, potentially using custom tools
        from the factory and the built-in web search tool. Can request JSON output.

        Args:
            messages: List of message dictionaries for the conversation history.
            model: Override the default model for this call.
            max_tool_iterations: Maximum number of tool call/response cycles.
            expect_json: If True, requests JSON output format from the API.
            **kwargs: Additional arguments passed to the OpenAI client.

        Returns:
            The final text content from the assistant, or None on error/timeout.
        """
        target_model = model or self.model
        module_logger.info(f"Starting generation with model: {target_model}. Expect JSON: {expect_json}")

        current_messages = list(messages)
        last_list_products_result_content: Optional[str] = None # Custom logic state
        iteration_count = 0

        # Prepare API call arguments
        api_call_args = {
            "model": target_model,
            "messages": current_messages,
            **kwargs,
        }
        
        if expect_json:
            api_call_args["response_format"] = expect_json
        
        if self.tool_factory:
            custom_tools = self.tool_factory.get_tool_definitions()
            if custom_tools:
                api_call_args["tools"] = custom_tools
                api_call_args["tool_choice"] = "auto"

        try:
            while iteration_count < max_tool_iterations:
                module_logger.debug(f"--- Tool Iteration {iteration_count + 1} ---")
                api_call_args["messages"] = list(current_messages) # Use fresh list copy

                # API Call
                try:
                     completion_task = asyncio.to_thread(
                         self.client.beta.chat.completions.parse,
                         **api_call_args
                     )
                     completion = await asyncio.wait_for(completion_task, timeout=180.0)
                except TypeError as e:
                    # Catch serialization errors specifically before the API call
                    module_logger.error(f"Serialization error preparing API call (Iteration {iteration_count+1}): {e}")
                    module_logger.debug(f"Problematic Messages (structure/types): {current_messages}")
                    return f"[Error: Internal serialization error before API call]" # Return specific error


                response_message_obj = completion.choices[0].message
                message_dict = self._convert_message_to_dict(response_message_obj)
                current_messages.append(message_dict)

                tool_calls_in_response = message_dict.get("tool_calls")

                # Handle Response: No Tool Calls -> Final Response
                if not tool_calls_in_response:
                    module_logger.info("No tool calls requested by model. Returning final response.")
                    final_content = message_dict.get("content")

                    # Warn if JSON was expected but not received
                    if expect_json:
                        is_valid_json_string = False
                        if isinstance(final_content, str):
                            try: json.loads(final_content); is_valid_json_string = True
                            except json.JSONDecodeError: pass
                        if not is_valid_json_string:
                             module_logger.warning(f"Expected JSON output but received non-JSON content (type: {type(final_content)}). Returning raw content.")
                             module_logger.debug(f"Non-JSON content snippet: {str(final_content)[:200]}...")
                    return final_content

                # Handle Response: Process Tool Calls
                if not self.tool_factory:
                     module_logger.error("Tool calls received, but no ApiToolFactory configured.")
                     error_message = "[System Error: Received tool calls but cannot process them.]"
                     current_messages.append({"role": "user", "content": error_message})
                     iteration_count += 1
                     continue

                module_logger.info(f"Processing {len(tool_calls_in_response)} tool call(s) requested by model.")
                tool_outputs = []
                current_iteration_list_products_result = last_list_products_result_content
                last_list_products_result_content = None

                for tool_call in tool_calls_in_response:
                    if tool_call.get("type") != "function":
                         module_logger.warning(f"Received non-function tool call type, skipping: {tool_call.get('type')}")
                         continue

                    function_info = tool_call.get("function", {})
                    function_name = function_info.get("name")
                    function_args_str = function_info.get("arguments")
                    tool_call_id = tool_call.get("id")

                    if not tool_call_id or not function_name or function_args_str is None:
                        module_logger.error(f"Malformed tool call structure received: ID={tool_call_id}, Name={function_name}, Args Provided={function_args_str is not None}")
                        tool_outputs.append({
                            "role": "tool", "tool_call_id": tool_call_id or "unknown_id",
                            "name": function_name or "unknown_function",
                            "content": json.dumps({"error": "Malformed tool call structure received from API."})})
                        continue

                    # --- Intervention Logic (Specific to 'list_products') ---
                    should_skip = False
                    if function_name == "list_products" and current_iteration_list_products_result is not None:
                        try:
                            prev_result_data = json.loads(current_iteration_list_products_result)
                            if isinstance(prev_result_data, dict) and prev_result_data.get("products") == []:
                                module_logger.warning(f"INTERVENTION: Skipping redundant 'list_products' call (ID: {tool_call_id})")
                                should_skip = True
                                tool_outputs.append({ "role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": "Redundant Call Blocked"})})
                        except Exception as e:
                             module_logger.warning(f"Error during intervention check for {function_name} (ID: {tool_call_id}): {e}", exc_info=False) # Less verbose traceback

                    if should_skip: continue

                    # --- Execute Custom Tool via Factory ---
                    try:
                        module_logger.info(f"Dispatching tool '{function_name}' (ID: {tool_call_id})")
                        tool_result_str = self.tool_factory.dispatch_tool(function_name, function_args_str)
                        # module_logger.debug(f"Tool '{function_name}' result snippet: {tool_result_str[:100]}...")

                        if function_name == "list_products":
                             last_list_products_result_content = tool_result_str

                        tool_outputs.append({ "role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": tool_result_str })
                    except Exception as e:
                         module_logger.error(f"Error dispatching/executing tool '{function_name}' (ID: {tool_call_id}): {e}", exc_info=True) # Show traceback for tool errors
                         tool_outputs.append({ "role": "tool", "tool_call_id": tool_call_id, "name": function_name, "content": json.dumps({"error": f"Failed to execute tool {function_name}", "details": str(e)})})
                         if function_name == "list_products": last_list_products_result_content = None

                current_messages.extend(tool_outputs)
                iteration_count += 1

            # Max Iterations Reached
            if iteration_count >= max_tool_iterations:
                 module_logger.warning(f"Max tool iterations ({max_tool_iterations}) reached.")
                 last_assistant_message = next((msg for msg in reversed(current_messages) if msg.get("role") == 'assistant' and msg.get("content")), None)
                 if last_assistant_message:
                      final_content = last_assistant_message["content"]
                      if expect_json:
                          is_valid_json_string = False
                          if isinstance(final_content, str):
                              try: json.loads(final_content); is_valid_json_string = True
                              except json.JSONDecodeError: pass
                          if not is_valid_json_string:
                               module_logger.warning(f"Max iterations reached. Expected JSON, but last assistant content was not valid JSON.")
                               module_logger.debug(f"Non-JSON content snippet: {str(final_content)[:200]}...")
                      return final_content + f"\n[Warning: Max tool iterations ({max_tool_iterations}) reached]"
                 else:
                     return f"[Error: Max tool iterations ({max_tool_iterations}) reached without final assistant content.]"

        except asyncio.TimeoutError:
            module_logger.error(f"The OpenAI API request timed out after 180 seconds.")
            return "[Error: API call timed out]"
        except BadRequestError as e: # Catch specific OpenAI errors
             error_details = e.body.get('message', str(e)) if hasattr(e, 'body') and isinstance(e.body, dict) else str(e)
             if "context_length_exceeded" in error_details:
                 module_logger.error(f"BadRequestError: Context length exceeded. Details: {error_details}", exc_info=False)
                 return "[Error: Context length exceeded]"
             elif "response_format" in error_details and expect_json:
                  module_logger.error(f"BadRequestError related to JSON response format: {error_details}. Model may have failed to produce valid JSON.", exc_info=False)
                  return "[Error: Model failed to generate valid JSON]"
             else:
                 module_logger.error(f"BadRequestError during generation: {error_details}", exc_info=True)
                 return f"[Error: OpenAI API Error - {type(e).__name__}]"
        except Exception as e:
            module_logger.error(f"An unexpected error occurred during text generation: {e}", exc_info=True)
            last_assistant_content = self._find_last_assistant_content(current_messages)
            error_suffix = f"\n[Error: Unexpected error during generation: {type(e).__name__}]"
            return (last_assistant_content + error_suffix) if last_assistant_content else error_suffix[1:] # Remove leading newline if no content

        module_logger.error("Generation process ended unexpectedly without returning content.")
        return "[Error: Generation process ended unexpectedly]"

    # Helper method to convert OpenAI message object to dictionary (Keep as is)
    def _convert_message_to_dict(self, message_obj) -> Dict[str, Any]:
        message_dict = {"role": message_obj.role}
        if message_obj.content is not None:
            # Content might be complex (e.g., list of blocks) or simple string
            message_dict["content"] = message_obj.content
        if message_obj.tool_calls:
            message_dict["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    # Only include 'function' if the type is 'function'
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments} if tc.type == 'function' else None
                }
                for tc in message_obj.tool_calls if tc.id and tc.type # Basic validation
            ]
            # Filter out entries where function is None if type wasn't function
            message_dict["tool_calls"] = [tc for tc in message_dict["tool_calls"] if tc.get("type") == "function" or tc.get("function") is not None]

        # Include annotations if present (for web search results)
        if hasattr(message_obj, 'annotations') and message_obj.annotations:
             # Convert annotations to a serializable format if necessary
             try:
                 # Assuming annotations are already serializable or have a standard structure
                 message_dict["annotations"] = json.loads(json.dumps(message_obj.annotations, default=str)) # Attempt serialization
             except Exception as e:
                 module_logger.warning(f"Could not serialize message annotations: {e}")
                 message_dict["annotations"] = "[Serialization Error]"

        return message_dict

    # Helper to find last assistant content, useful for error reporting
    def _find_last_assistant_content(self, messages: List[Dict[str, Any]]) -> Optional[str]:
         for msg in reversed(messages):
              if msg.get("role") == 'assistant' and msg.get("content"):
                   # Handle complex content (e.g., list of blocks)
                   content = msg["content"]
                   if isinstance(content, str):
                       return content
                   elif isinstance(content, list) and content:
                       # Try to extract text from the first text block
                       for block in content:
                           if block.get("type") == "text" and block.get("text"):
                               return str(block["text"])[:500] + "..." # Return truncated text
                       return "[Assistant message with non-text content]"
                   else:
                        return "[Assistant message with unknown content format]"
         return None