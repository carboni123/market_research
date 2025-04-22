# src/market_research/api/openai_api.py
import asyncio
from openai import OpenAI
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
        model: Optional[str] = None,
        max_tool_iterations: int = 5,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Generates text using the OpenAI API, potentially using custom tools
        from the factory and the built-in web search tool.

        Args:
            messages: List of message dictionaries for the conversation history.
            model: Override the default model for this call.
            max_tokens: Max tokens for the completion.
            temperature: Sampling temperature.
            max_tool_iterations: Maximum number of tool call/response cycles.
            user_location: Optional dictionary for web search localization.
                           Example: {"type": "approximate", "country": "US", "region": "CA", "city": "San Francisco"}
            search_context_size: Optional context size for web search ("low", "medium", "high").
            **kwargs: Additional arguments passed to the OpenAI client.

        Returns:
            The final text content from the assistant, or None on error/timeout.
        """
        if not model:
            model = self.model
        logging.info(f"Using model: {model}")

        current_messages = list(messages)
        last_list_products_result_content: Optional[str] = None # Keep your custom logic state
        iteration_count = 0

        try:
            while iteration_count < max_tool_iterations:
                module_logger.debug(f"--- Iteration {iteration_count + 1} ---")
                current_iteration_list_products_result = last_list_products_result_content
                last_list_products_result_content = None

                try:
                     logging.debug(f"Messages being sent to API (Iteration {iteration_count+1}): {json.dumps(current_messages, indent=2, default=str)}") # Added default=str for non-serializable
                except TypeError as e:
                    logging.error(f"Serialization error before API call (Iteration {iteration_count+1}): {e}")
                    logging.debug(f"Messages (raw list): {current_messages}")

                # --- API Call ---
                # Use asyncio.to_thread for the blocking OpenAI client call
                completion_task = asyncio.to_thread(
                    self.client.chat.completions.create,
                    model=model,
                    messages=current_messages,
                    **kwargs,
                )
                # Add a timeout to the API call itself
                completion = await asyncio.wait_for(completion_task, timeout=120.0) # 2 min timeout for API call
                # ---------------

                response_message_obj = completion.choices[0].message
                message_dict = self._convert_message_to_dict(response_message_obj)

                current_messages.append(message_dict)
                module_logger.debug(f"API Response (converted to dict and added): {json.dumps(message_dict, indent=2, default=str)}")

                tool_calls_in_response = message_dict.get("tool_calls")

                # --- Handle Response ---
                if not tool_calls_in_response:
                    # Check if the response contains web search results (annotations)
                    # Note: Annotations might be structured differently depending on API version.
                    # This checks common patterns. Adjust based on actual observed responses.
                    web_results_found = False
                    if message_dict.get("content"):
                         # Example check: look for annotations in the content or message structure
                         # This part is speculative and needs verification with actual API responses
                         # when web_search_preview is used.
                         # Annotations might be part of the message object directly or within content.
                         if hasattr(response_message_obj, 'annotations') and response_message_obj.annotations:
                             web_results_found = True
                         elif isinstance(message_dict.get("content"), list): # Check for block-based content
                             for block in message_dict["content"]:
                                 if block.get("type") == "text" and block.get("text", {}).get("annotations"):
                                     web_results_found = True
                                     break
                         # Add more checks based on actual response structure if needed

                    if web_results_found:
                         module_logger.info("Model used web search (indicated by annotations) and provided final response.")
                    else:
                         module_logger.info("No tool calls requested by the model. Returning final response.")

                    return message_dict.get("content") # Return content whether search was used or not

                # --- Process Tool Calls (Your existing logic) ---
                # This part remains largely the same, handling *custom* tools if any were called.
                # The web_search_preview tool is handled internally by OpenAI; you won't see a "call" for it here.
                # You only need to handle calls for functions defined in your ApiToolFactory.

                if not self.tool_factory:
                    # This case should ideally not happen if tool_calls were received unless they are malformed
                    # or somehow related to internal OpenAI states not exposed as standard tool calls.
                    module_logger.error("Tool calls received from API, but no *custom* ApiToolFactory is configured to handle them.")
                    # It's unlikely a call for a *custom* tool would appear if none were defined.
                    # Log the unexpected tool calls.
                    module_logger.warning(f"Unexpected tool calls received: {tool_calls_in_response}")
                    # Append a message indicating confusion, or decide how to proceed.
                    # Maybe just continue the loop, hoping the next response is final content.
                    current_messages.append({"role": "user", "content": "System note: Received unexpected tool calls that cannot be processed."})
                    iteration_count += 1
                    continue # Go to the next iteration

                module_logger.info(f"Custom tool calls requested: {len(tool_calls_in_response)}")
                tool_outputs = []

                # --- Process Custom Tool Calls with Intervention Logic ---
                for tool_call in tool_calls_in_response:
                    # Check if it's a function call (expected type for custom tools)
                    if tool_call.get("type") != "function":
                         module_logger.warning(f"Received non-function tool call, skipping: {tool_call}")
                         continue # Skip non-function calls (like internal search results if they appear here)

                    function_info = tool_call.get("function", {})
                    function_name = function_info.get("name")
                    function_args_str = function_info.get("arguments")
                    tool_call_id = tool_call.get("id")

                    if not tool_call_id or not function_name or function_args_str is None:
                        module_logger.error(f"Malformed tool call structure received: {tool_call}")
                        tool_outputs.append({
                            "role": "tool", "tool_call_id": tool_call_id or "unknown_id",
                            "name": function_name or "unknown_function",
                            "content": json.dumps({"error": "Malformed tool call structure received from API."})})
                        continue

                    # --- *** Intervention Logic (Your existing code for list_products) *** ---
                    should_skip = False
                    if function_name == "list_products" and current_iteration_list_products_result is not None:
                        try:
                            prev_result_data = json.loads(current_iteration_list_products_result)
                            if isinstance(prev_result_data, dict) and prev_result_data.get("products") == []:
                                module_logger.warning(f"INTERVENTION: Skipping redundant 'list_products' call (ID: {tool_call_id}) because previous call returned empty list.")
                                should_skip = True
                                tool_outputs.append({
                                    "role": "tool", "tool_call_id": tool_call_id, "name": function_name,
                                    "content": json.dumps({
                                        "error": "Redundant Call Blocked",
                                        "message": "Cannot call 'list_products' again. The previous call indicated the end of the product catalog."
                                    })})
                        except json.JSONDecodeError:
                             module_logger.warning(f"Could not parse previous list_products result for intervention check: {current_iteration_list_products_result}")
                        except Exception as e:
                             module_logger.warning(f"Error during intervention check for {function_name}: {e}")

                    if should_skip:
                        continue

                    # --- Execute Custom Tool via Factory ---
                    try:
                        module_logger.info(f"Dispatching custom tool via factory: {function_name} with args string: {function_args_str}")
                        # Dispatch only handles custom tools defined in the factory
                        tool_result_str = self.tool_factory.dispatch_tool(function_name, function_args_str)
                        module_logger.info(f"Custom tool {function_name} result string: {tool_result_str[:200]}...")

                        if function_name == "list_products":
                             last_list_products_result_content = tool_result_str

                        tool_outputs.append({
                            "role": "tool", "tool_call_id": tool_call_id, "name": function_name,
                            "content": tool_result_str })

                    except Exception as e:
                         module_logger.error(f"Error dispatching/executing custom tool {function_name} via factory: {e}\n{traceback.format_exc()}")
                         tool_outputs.append({
                             "role": "tool", "tool_call_id": tool_call_id, "name": function_name,
                             "content": json.dumps({"error": f"Failed to execute custom tool {function_name}", "details": str(e)})
                         })
                         if function_name == "list_products":
                             last_list_products_result_content = None # Reset on error


                current_messages.extend(tool_outputs)
                iteration_count += 1
                # Reset check state (already done at start of loop)

            # --- Max Iterations Reached ---
            if iteration_count >= max_tool_iterations:
                 module_logger.warning(f"Max tool iterations ({max_tool_iterations}) reached.")
                 # Try to find the last assistant message with content
                 last_assistant_message = next((msg for msg in reversed(current_messages) if msg.get("role") == 'assistant' and msg.get("content")), None)
                 if last_assistant_message:
                      # Check if the last message indicates web search was used (via annotations)
                      final_content = last_assistant_message["content"]
                      # Add annotation check here if needed, similar to the check after API call
                      return final_content + f"\n[Warning: Max tool iterations ({max_tool_iterations}) reached]"
                 else:
                     # Fallback if no final assistant content found
                     last_tool_message = next((msg for msg in reversed(current_messages) if msg.get("role") == 'tool'), None)
                     if last_tool_message:
                         return f"[Error: Max tool iterations reached. Last tool result: {str(last_tool_message.get('content'))[:200]}...]"
                     else:
                         return "[Error: Max tool iterations reached without final assistant content or tool results.]"

        except asyncio.TimeoutError:
            # This catches timeouts set around the completion_task
            module_logger.error(f"The OpenAI API request timed out after 120 seconds.")
            return "[Error: API call timed out]"
        except Exception as e:
            module_logger.error(f"An unexpected error occurred during text generation: {e}\n{traceback.format_exc()}")
            # Attempt to get the last assistant message even on error
            last_assistant_content = self._find_last_assistant_content(current_messages)
            error_suffix = f"\n[Error: An unexpected error occurred: {type(e).__name__}]"
            return (last_assistant_content + error_suffix) if last_assistant_content else f"[Error: An unexpected error occurred: {type(e).__name__}]"

        # Should not be reached if logic is correct
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