'''Classes for handling MCP server connection and operations.'''

import asyncio
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

from mcp import ClientSession
from mcp.client.sse import sse_client


@dataclass
class ToolParameter:
    '''Represents a parameter for a tool.
    
    Attributes:
        name: Parameter name
        parameter_type: Parameter type (e.g., 'string', 'number')
        description: Parameter description
        required: Whether the parameter is required
        default: Default value for the parameter
    '''
    name: str
    parameter_type: str
    description: str
    required: bool = False
    default: Any = None


@dataclass
class ToolDef:
    '''Represents a tool definition.
    
    Attributes:
        name: Tool name
        description: Tool description
        parameters: List of ToolParameter objects
        metadata: Optional dictionary of additional metadata
        identifier: Tool identifier (defaults to name)
    '''
    name: str
    description: str
    parameters: List[ToolParameter]
    metadata: Optional[Dict[str, Any]] = None
    identifier: str = ''


@dataclass
class ToolInvocationResult:
    '''Represents the result of a tool invocation.
    
    Attributes:
        content: Result content as a string
        error_code: Error code (0 for success, 1 for error)
    '''
    content: str
    error_code: int


class MCPConnectionError(Exception):
    '''Exception raised when MCP connection fails'''
    pass


class MCPTimeoutError(Exception):
    '''Exception raised when MCP operation times out'''
    pass


class MCPClientWrapper:
    '''Main client wrapper class for interacting with Model Context Protocol (MCP) endpoints'''

    def __init__(self, endpoint: str, timeout: float = 30.0, max_retries: int = 3):
        '''Initialize MCP client with endpoint URL
        
        Args:
            endpoint: The MCP endpoint URL (must be http or https)
            timeout: Connection timeout in seconds
            max_retries: Maximum number of retry attempts
        '''

        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        # self.tools = None
        # self.anthropic = Anthropic()


    async def _execute_with_retry(self, operation_name: str, operation_func):
        '''Execute an operation with retry logic and proper error handling
        
        Args:
            operation_name: Name of the operation for logging
            operation_func: Async function to execute
            
        Returns:
            Result of the operation
            
        Raises:
            MCPConnectionError: If connection fails after all retries
            MCPTimeoutError: If operation times out
        '''

        logger = logging.getLogger(__name__ + '_execute_with_retry')

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    'Attempting %s (attempt %s/%s)',
                    operation_name,
                    attempt + 1,
                    self.max_retries
                )

                # Execute with timeout
                result = await asyncio.wait_for(operation_func(), timeout=self.timeout)
                logger.debug('%s completed successfully', operation_name)
                return result

            except asyncio.TimeoutError as e:
                last_exception = MCPTimeoutError(
                    f'{operation_name} timed out after {self.timeout} seconds'
                )
                logger.warning('%s timed out on attempt %s: %s', operation_name, attempt + 1, e)

            except Exception as e: # pylint: disable=broad-exception-caught
                last_exception = e
                logger.warning('%s failed on attempt %s: %s', operation_name, attempt + 1, str(e))

                # Don't retry on certain types of errors
                if isinstance(e, (ValueError, TypeError)):
                    break

            # Wait before retry (exponential backoff)
            if attempt < self.max_retries - 1:
                wait_time = 2 ** attempt
                logger.debug('Waiting %s seconds before retry', wait_time)
                await asyncio.sleep(wait_time)

        # All retries failed
        if isinstance(last_exception, MCPTimeoutError):
            raise last_exception
        else:
            raise MCPConnectionError(
                f'{operation_name} failed after {self.max_retries} attempts: {str(last_exception)}'
            )


    async def _safe_sse_operation(self, operation_func):
        '''Safely execute an SSE operation with proper task cleanup
        
        Args:
            operation_func: Function that takes (streams, session) as arguments
            
        Returns:
            Result of the operation
        '''

        logger = logging.getLogger(__name__ + '_safe_sse_operation')

        streams = None
        session = None

        try:
            # Create SSE client with proper error handling
            streams = sse_client(self.endpoint)

            async with streams as stream_context:

                # Create session with proper cleanup
                session = ClientSession(*stream_context)

                async with session as session_context:
                    await session_context.initialize()
                    return await operation_func(session_context)

        except Exception as e:
            logger.error('SSE operation failed: %s', str(e))

            # Ensure proper cleanup of any remaining tasks
            if session:
                try:
                    # Cancel any pending tasks in the session
                    tasks = [task for task in asyncio.all_tasks() if not task.done()]
                    if tasks:
                        logger.debug('Cancelling %s pending tasks', len(tasks))
                        for task in tasks:
                            task.cancel()

                        # Wait for tasks to be cancelled
                        await asyncio.gather(*tasks, return_exceptions=True)

                except Exception as cleanup_error: # pylint: disable=broad-exception-caught
                    logger.warning('Error during task cleanup: %s', cleanup_error)
            raise


    async def list_tools(self) -> List[ToolDef]:
        '''List available tools from the MCP endpoint
        
        Returns:
            List of ToolDef objects describing available tools
            
        Raises:
            MCPConnectionError: If connection fails
            MCPTimeoutError: If operation times out
        '''

        async def _list_tools_operation():
            async def _operation(session):

                tools_result = await session.list_tools()
                tools = []

                for tool in tools_result.tools:
                    parameters = []
                    required_params = tool.inputSchema.get('required', [])

                    for param_name, param_schema in tool.inputSchema.get('properties', {}).items():
                        parameters.append(
                            ToolParameter(
                                name=param_name,
                                parameter_type=param_schema.get('type', 'string'),
                                description=param_schema.get('description', ''),
                                required=param_name in required_params,
                                default=param_schema.get('default'),
                            )
                        )

                    tools.append(
                        ToolDef(
                            name=tool.name,
                            description=tool.description,
                            parameters=parameters,
                            metadata={'endpoint': self.endpoint},
                            identifier=tool.name  # Using name as identifier
                        )
                    )

                self.tools = tools

                return tools

            return await self._safe_sse_operation(_operation)

        return await self._execute_with_retry('list_tools', _list_tools_operation)


    async def invoke_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> ToolInvocationResult:
        '''Invoke a specific tool with parameters
        
        Args:
            tool_name: Name of the tool to invoke
            kwargs: Dictionary of parameters to pass to the tool
            
        Returns:
            ToolInvocationResult containing the tool's response
            
        Raises:
            MCPConnectionError: If connection fails
            MCPTimeoutError: If operation times out
        '''

        async def _invoke_tool_operation():
            async def _operation(session):
                result = await session.call_tool(tool_name, kwargs)
                return ToolInvocationResult(
                    content='\n'.join([result.model_dump_json() for result in result.content]),
                    error_code=1 if result.isError else 0,
                )

            return await self._safe_sse_operation(_operation)

        return await self._execute_with_retry(f'invoke_tool({tool_name})', _invoke_tool_operation)


    async def check_connection(self) -> bool:
        '''Check if the MCP endpoint is reachable
        
        Returns:
            True if connection is successful, False otherwise
        '''

        logger = logging.getLogger(__name__ + '_check_connection')

        try:
            await self.list_tools()
            return True
        except Exception as e: # pylint: disable=broad-exception-caught
            logger.debug('Connection check failed: %s', str(e))
            return False


    def get_endpoint_info(self) -> Dict[str, Any]:
        '''Get information about the configured endpoint
        
        Returns:
            Dictionary with endpoint information
        '''
        parsed = urlparse(self.endpoint)
        return {
            'endpoint': self.endpoint,
            'scheme': parsed.scheme,
            'hostname': parsed.hostname,
            'port': parsed.port,
            'path': parsed.path,
            'timeout': self.timeout,
            'max_retries': self.max_retries
        }
