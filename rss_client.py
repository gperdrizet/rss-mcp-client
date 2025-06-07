'''RSS MCP server demonstration client app.'''

import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

import gradio as gr
import client.interface as interface
from client.mcp_client import MCPClientWrapper
from client.anthropic_bridge import AnthropicBridge

# Make sure log directory exists
Path('logs').mkdir(parents=True, exist_ok=True)

# Set-up logger
logger = logging.getLogger()

logging.basicConfig(
    handlers=[RotatingFileHandler(
        'logs/rss_client.log',
        maxBytes=100000,
        backupCount=10,
        mode='w'
    )],
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Handle MCP server connection and interactions
RSS_CLIENT = MCPClientWrapper(
    'https://agents-mcp-hackathon-rss-mcp-server.hf.space/gradio_api/mcp/sse'
)

# Handles Anthropic API I/O
BRIDGE = AnthropicBridge(
    RSS_CLIENT,
    api_key=os.environ['ANTHROPIC_API_KEY']
)

async def send_message(message: str, chat_history: list) -> str:
    '''Submits user message to agent.
    
    Args:
        message: the new message from the user as a string
        chat_history: list containing conversation history where each element is
            a dictionary with keys 'role' and 'content'

    Returns
        New chat history with model's response to user added.
    '''

    function_logger = logging.getLogger(__name__ + '.submit_input')
    function_logger.info('Submitting user message: %s', message)

    chat_history.append({"role": "user", "content": message})
    chat_history = await interface.agent_input(BRIDGE, chat_history)

    return '', chat_history


with gr.Blocks(title='MCP RSS client') as demo:
    gr.Markdown('# Agentic RSS reader')
    gr.Markdown("""
        Uses sister Space 
        [RSS feed reader](https://huggingface.co/spaces/Agents-MCP-Hackathon/rss-mcp-server) 
        via MCP. Click 'Connect to MCP server' to get started. Check out the
        [main project repo on GitHub](https://github.com/gperdrizet/MCP-hackathon/tree/main).
        Both Spaces by [George Perdrizet](https://www.linkedin.com/in/gperdrizet/).
    """)

    connect_btn = gr.Button('Connect to MCP server')
    status = gr.Textbox(label='MCP server tool dump', interactive=False, lines=4)

    chatbot = gr.Chatbot(
        value=[],
        height=200,
        type='messages',
        show_copy_button=True
    )

    msg = gr.Textbox(
        'Are there any new posts on Hacker News?',
        label='Ask about content or articles on a site or platform',
        placeholder='Is there anything new on Hacker News?',
        scale=4
    )

    connect_btn.click(RSS_CLIENT.list_tools, outputs=status) # pylint: disable=no-member

    msg.submit( # pylint: disable=no-member
        send_message,
        [msg, chatbot],
        [msg, chatbot]
    )

if __name__ == '__main__':

    demo.launch(server_name="0.0.0.0", server_port=7860)
