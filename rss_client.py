'''RSS MCP server demonstration client app.'''

import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

import gradio as gr
import assets.html as html
import client.gradio_functions as gradio_funcs
import client.interface as interface
from client.mcp_client import MCPClientWrapper
from client.anthropic_bridge import AnthropicBridge

# Make sure log directory exists
Path('logs').mkdir(parents=True, exist_ok=True)

# Clear old logs if present
gradio_funcs.delete_old_logs('logs', 'rss_client')

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
    with gr.Row():
        gr.HTML(html.TITLE)

    gr.Markdown(html.DESCRIPTION)

    # MCP connection/tool dump
    connect_btn = gr.Button('Connect to MCP server')
    status = gr.Textbox(label='MCP server tool dump', interactive=False, lines=4)
    connect_btn.click(RSS_CLIENT.list_tools, outputs=status) # pylint: disable=no-member

    # Log output
    logs = gr.Textbox(label='Client logs', lines=10, max_lines=10)
    timer = gr.Timer(1, active=True)

    timer.tick( # pylint: disable=no-member
        lambda: gradio_funcs.update_log(), # pylint: disable=unnecessary-lambda
        outputs=logs
    )

    # Chat interface
    chatbot = gr.Chatbot(
        value=[],
        height=500,
        type='messages',
        show_copy_button=True
    )

    msg = gr.Textbox(
        'Are there any new posts on Hacker News?',
        label='Ask about content or articles on a site or platform',
        placeholder='Is there anything new on Hacker News?',
        scale=4
    )

    msg.submit( # pylint: disable=no-member
        send_message,
        [msg, chatbot],
        [msg, chatbot]
    )

if __name__ == '__main__':

    current_directory = os.getcwd()

    if 'pyrite' in current_directory:
        demo.launch(server_name='0.0.0.0', server_port=7860)

    else:
        demo.launch()
