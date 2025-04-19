# app/api/api_tool_factory.py
import json
import logging
from typing import List, Dict, Any, Callable

module_logger = logging.getLogger(__name__)

class ApiToolFactory:
    """
    Manages the definition and dispatching of custom tools for the API.
    For now, it's minimal as we rely on built-in web search.
    """
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_definitions: List[Dict[str, Any]] = []
        module_logger.info("ApiToolFactory initialized.")
        # Example: If you had a custom tool later
        # self.register_tool(self.example_tool_function, "example_tool", "An example tool description.")

    def register_tool(self, function: Callable, name: str, description: str, parameters: Dict[str, Any] = None):
        """Registers a custom tool function and its definition."""
        if name in self.tools:
            module_logger.warning(f"Tool '{name}' is already registered. Overwriting.")

        self.tools[name] = function
        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
            }
        }
        if parameters:
            tool_def["function"]["parameters"] = parameters
        self.tool_definitions.append(tool_def)
        module_logger.info(f"Registered custom tool: {name}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns the list of OpenAI-compatible tool definitions."""
        # Return definitions of *custom* tools. Web search is handled by OpenAI.
        return self.tool_definitions

    def dispatch_tool(self, function_name: str, function_args_str: str) -> str:
        """
        Executes the appropriate tool function based on the name and arguments.

        Args:
            function_name: The name of the function to execute.
            function_args_str: A JSON string containing the arguments for the function.

        Returns:
            A JSON string representation of the tool's execution result or error.
        """
        if function_name not in self.tools:
            module_logger.error(f"Attempted to dispatch unknown tool: {function_name}")
            return json.dumps({"error": f"Tool '{function_name}' not found."})

        try:
            # Parse arguments safely
            try:
                arguments = json.loads(function_args_str)
            except json.JSONDecodeError as e:
                module_logger.error(f"Failed to parse arguments for {function_name}: {e}")
                return json.dumps({"error": f"Invalid JSON arguments for tool {function_name}", "details": str(e)})

            tool_function = self.tools[function_name]

            # Execute the tool function (assuming it's synchronous for now)
            # If your tools are async, you'll need to adjust the execution pattern
            module_logger.info(f"Executing tool '{function_name}' with args: {arguments}")
            result = tool_function(**arguments) # Pass parsed args as kwargs

            # Ensure result is JSON serializable (or convert it)
            try:
                result_str = json.dumps(result)
                module_logger.info(f"Tool '{function_name}' executed successfully.")
                return result_str
            except TypeError as e:
                 module_logger.error(f"Result from tool '{function_name}' is not JSON serializable: {e}")
                 return json.dumps({"error": f"Tool {function_name} result not serializable", "details": str(e)})

        except Exception as e:
            module_logger.exception(f"Error executing tool {function_name}: {e}")
            # Return error details in a JSON structure
            return json.dumps({"error": f"Failed to execute tool {function_name}", "details": str(e)})

    # --- Example Tool (if needed later) ---
    # def example_tool_function(self, param1: str, param2: int) -> Dict[str, Any]:
    #     """An example function that could be registered as a tool."""
    #     module_logger.info(f"Executing example_tool_function with param1='{param1}', param2={param2}")
    #     # Replace with actual tool logic
    #     return {"status": "success", "input_params": {"param1": param1, "param2": param2}}