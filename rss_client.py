'''RSS MCP server demonstration client app.'''

import asyncio
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from dataclasses import dataclass

import gradio as gr
from mcp import ClientSession
from mcp.client.sse import sse_client


# Make sure log directory exists
Path('logs').mkdir(parents=True, exist_ok=True)

# Set-up logger
logger = logging.getLogger()

logging.basicConfig(
    handlers=[RotatingFileHandler(
        'logs/rss_server.log',
        maxBytes=100000,
        backupCount=10,
        mode='w'
    )],
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


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


class MCPConnectionError(Exception):
    '''Exception raised when MCP connection fails'''
    pass


class MCPTimeoutError(Exception):
    '''Exception raised when MCP operation times out'''
    pass


class MCPClientWrapper:
    '''Client for interacting with Model Context Protocol (MCP) endpoints'''

    def __init__(self, endpoint: str, timeout: float = 30.0, max_retries: int = 3):
        '''Initialize MCP client with endpoint URL
        
        Args:
            endpoint: The MCP endpoint URL (must be http or https)
            timeout: Connection timeout in seconds
            max_retries: Maximum number of retry attempts
        '''
        if urlparse(endpoint).scheme not in ('http', 'https'):
            raise ValueError(f'Endpoint {endpoint} is not a valid HTTP(S) URL')
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries


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
                return tools

            return await self._safe_sse_operation(_operation)

        return await self._execute_with_retry('list_tools', _list_tools_operation)

client = MCPClientWrapper('https://agents-mcp-hackathon-rss-mcp-server.hf.space/gradio_api/mcp/sse')

# def gradio_interface():
with gr.Blocks(title='MCP RSS client') as demo:
    gr.Markdown('# MCP RSS reader')
    gr.Markdown('Connect to the MCP RSS server')

    connect_btn = gr.Button('Connect')
    status = gr.Textbox(label='Connection Status', interactive=False, lines=50)
    connect_btn.click(client.list_tools, outputs=status) # pylint: disable=no-member


if __name__ == '__main__':

    demo.launch(debug=True)
