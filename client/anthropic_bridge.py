'''Classes to connect to Anthropic inference endpoint'''

import abc
from typing import Dict, List, Any, Optional
import anthropic
from client.mcp_client import MCPClientWrapper, ToolDef, ToolParameter, ToolInvocationResult

DEFAULT_ANTHROPIC_MODEL = 'claude-3-haiku-20240307'

# Type mapping from Python/MCP types to JSON Schema types
TYPE_MAPPING = {
    'int': 'integer',
    'bool': 'boolean',
    'str': 'string',
    'float': 'number',
    'list': 'array',
    'dict': 'object',
    'boolean': 'boolean',
    'string': 'string',
    'integer': 'integer',
    'number': 'number',
    'array': 'array',
    'object': 'object'
}


class LLMBridge(abc.ABC):
    '''Abstract base class for LLM bridge implementations.'''

    def __init__(self, mcp_client: MCPClientWrapper):
        '''Initialize the LLM bridge with an MCPClient instance.

        Args:
            mcp_client: An initialized MCPClient instance
        '''
        self.mcp_client = mcp_client
        self.tools = None


    async def fetch_tools(self) -> List[ToolDef]:
        '''Fetch available tools from the MCP endpoint.

        
        Returns:
            List of ToolDef objects
        '''
        self.tools = await self.mcp_client.list_tools()
        return self.tools


    @abc.abstractmethod
    async def format_tools(self, tools: List[ToolDef]) -> Any:
        '''Format tools for the specific LLM provider.

        Args:
            tools: List of ToolDef objects
            
        Returns:
            Formatted tools in the LLM-specific format
        '''
        pass


    @abc.abstractmethod
    async def submit_query(self, system_prompt: str, query: List[Dict], formatted_tools: Any) -> Dict[str, Any]:
        '''Submit a query to the LLM with the formatted tools.

        Args:
            query: User query string            # messages=[
            #     {'role': 'user', 'content': query}
            # ],
            formatted_tools: Tools in the LLM-specific format
            
        Returns:
            LLM response
        '''
        pass


    @abc.abstractmethod
    async def parse_tool_call(self, llm_response: Any) -> Optional[Dict[str, Any]]:
        '''Parse the LLM response to extract tool calls.

        Args:
            llm_response: Response from the LLM
            
        Returns:
            Dictionary with tool name and parameters, or None if no tool call
        '''
        pass


    async def execute_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolInvocationResult:
        '''Execute a tool with the given parameters.

        Args:
            tool_name: Name of the tool to invoke
            kwargs: Dictionary of parameters to pass to the tool
            
        Returns:
            ToolInvocationResult containing the tool's response
        '''
        return await self.mcp_client.invoke_tool(tool_name, kwargs)


    async def process_query(self, system_prompt: str, query: List[Dict]) -> Dict[str, Any]:
        '''Process a user query through the LLM and execute any tool calls.

        This method handles the full flow:
        1. Fetch tools if not already fetched
        2. Format tools for the LLM
        3. Submit query to LLM
        4. Parse tool calls from LLM response
        5. Execute tool if needed
        
        Args:
            query: User query string
            
        Returns:
            Dictionary containing the LLM response, tool call, and tool result
        '''
        # 1. Fetch tools if not already fetched
        if self.tools is None:
            await self.fetch_tools()

        # 2. Format tools for the LLM
        formatted_tools = await self.format_tools(self.tools)

        # 3. Submit query to LLM
        llm_response = await self.submit_query(system_prompt, query, formatted_tools)

        # 4. Parse tool calls from LLM response
        tool_call = await self.parse_tool_call(llm_response)

        result = {
            'llm_response': llm_response,
            'tool_call': tool_call,
            'tool_result': None
        }

        # 5. Execute tool if needed
        if tool_call:
            tool_name = tool_call.get('name')
            kwargs = tool_call.get('parameters', {})
            tool_result = await self.execute_tool(tool_name, kwargs)
            result['tool_result'] = tool_result

        return result


class AnthropicBridge(LLMBridge):
    '''Anthropic-specific implementation of the LLM Bridge.'''

    def __init__(self, mcp_client, api_key, model=DEFAULT_ANTHROPIC_MODEL): # Use imported default
        '''Initialize Anthropic bridge with API key and model.
        
        Args:
            mcp_client: An initialized MCPClient instance
            api_key: Anthropic API key
            model: Anthropic model to use (default: from models.py)
        '''
        super().__init__(mcp_client)
        self.llm_client = anthropic.Anthropic(api_key=api_key)
        self.model = model


    async def format_tools(self, tools: List[ToolDef]) -> List[Dict[str, Any]]:
        '''Format tools for Anthropic.
        
        Args:
            tools: List of ToolDef objects
            
        Returns:
            List of tools in Anthropic format
        '''
        return to_anthropic_format(tools)


    async def submit_query(
            self,
            system_prompt: str,
            query: List[Dict],
            formatted_tools: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        '''Submit a query to Anthropic with the formatted tools.
        
        Args:
            query: User query string
            formatted_tools: Tools in Anthropic format
            
        Returns:
            Anthropic API response
        '''
        response = self.llm_client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=query,
            tools=formatted_tools
        )

        return response


    async def parse_tool_call(self, llm_response: Any) -> Optional[Dict[str, Any]]:
        '''Parse the Anthropic response to extract tool calls.
        
        Args:
            llm_response: Response from Anthropic
            
        Returns:
            Dictionary with tool name and parameters, or None if no tool call
        '''
        for content in llm_response.content:
            if content.type == 'tool_use':
                return {
                    'name': content.name,
                    'parameters': content.input
                }

        return None



def to_anthropic_format(tools: List[ToolDef]) -> List[Dict[str, Any]]:
    '''Convert ToolDef objects to Anthropic tool format.
    
    Args:
        tools: List of ToolDef objects to convert
        
    Returns:
        List of dictionaries in Anthropic tool format
    '''

    anthropic_tools = []
    for tool in tools:
        anthropic_tool = {
            'name': tool.name,
            'description': tool.description,
            'input_schema': {
                'type': 'object',
                'properties': {},
                'required': []
            }
        }

        # Add properties
        for param in tool.parameters:
            # Map the type or use the original if no mapping exists
            schema_type = TYPE_MAPPING.get(param.parameter_type, param.parameter_type)

            param_schema = {
                'type': schema_type,  # Use mapped type
                'description': param.description
            }

            # For arrays, we need to specify the items type
            if schema_type == 'array':
                item_type = _infer_array_item_type(param)
                param_schema['items'] = {'type': item_type}

            anthropic_tool['input_schema']['properties'][param.name] = param_schema

            # Add default value if provided
            if param.default is not None:
                anthropic_tool['input_schema']['properties'][param.name]['default'] = param.default

            # Add to required list if required
            if param.required:
                anthropic_tool['input_schema']['required'].append(param.name)

        anthropic_tools.append(anthropic_tool)
    return anthropic_tools


def _infer_array_item_type(param: ToolParameter) -> str:
    '''Infer the item type for an array parameter based on its name and description.
    
    Args:
        param: The ToolParameter object
        
    Returns:
        The inferred JSON Schema type for array items
    '''
    # Default to string items
    item_type = 'string'

    # Check if parameter name contains hints about item type
    param_name_lower = param.name.lower()
    if any(hint in param_name_lower for hint in ['language', 'code', 'tag', 'name', 'id']):
        item_type = 'string'
    elif any(hint in param_name_lower for hint in ['number', 'count', 'amount', 'index']):
        item_type = 'integer'

    # Also check the description for hints
    if param.description:
        desc_lower = param.description.lower()
        if 'string' in desc_lower or 'text' in desc_lower or 'language' in desc_lower:
            item_type = 'string'
        elif 'number' in desc_lower or 'integer' in desc_lower or 'int' in desc_lower:
            item_type = 'integer'

    return item_type
