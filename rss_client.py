'''RSS MCP server demonstration client app.'''

import os
import asyncio
import logging
import time
import queue
from typing import Tuple
from pathlib import Path
from logging.handlers import RotatingFileHandler
import gradio as gr
import assets.html as html
import client.gradio_functions as gradio_funcs
import client.interface as interface
from client.mcp_client import MCPClientWrapper
from client.anthropic_bridge import AnthropicBridge

# Set-up root logger so we send logs from the MCP client,
# Gradio and the rest of the project to the same file.
# Make sure log directory exists
Path('logs').mkdir(parents=True, exist_ok=True)

# Clear old logs if present
gradio_funcs.delete_old_logs('logs', 'rss_client')

# Configure
logging.basicConfig(
    handlers=[RotatingFileHandler(
        'logs/rss_client.log',
        maxBytes=100000,
        backupCount=10,
        mode='w'
    )],
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

# Get a logger
logger = logging.getLogger(__name__)

# Handle MCP server connection and interactions
RSS_CLIENT = MCPClientWrapper(
    #'https://agents-mcp-hackathon-rss-mcp-server.hf.space/gradio_api/mcp/sse',
    'http://127.0.0.1:7861/gradio_api/mcp/sse'
)
logger.info('Started MCP client')

# Handles Anthropic API I/O
BRIDGE = AnthropicBridge(
    RSS_CLIENT,
    api_key=os.environ['ANTHROPIC_API_KEY']
)

logger.info('Started Anthropic API bridge')

# Queue to return responses to user
OUTPUT_QUEUE = queue.Queue()
logger.info('Created response queue')

def user_message(message: str, history: list) -> Tuple[str, list]:
    '''Adds user message to conversation and returns for immediate posting.

    Args:
        message: the new message from the user as a string
        chat_history: list containing conversation history where each element is
            a dictionary with keys 'role' and 'content'

    Returns
        New chat history with user's message added.
    '''

    return '', history + [{'role': 'user', 'content': message}]


def send_message(chat_history: list):
    '''Submits chat history to agent, streams reply, one character at a time.
    
    Args:
        chat_history: list containing conversation history where each element is
            a dictionary with keys 'role' and 'content'

    Returns
        New chat history with model's response to user added.
    '''

    asyncio.run(interface.agent_input(BRIDGE, OUTPUT_QUEUE, chat_history))

    while True:
        response = OUTPUT_QUEUE.get()

        if response == 'bot-finished':
            break

        chat_history.append({'role': 'assistant', 'content': ''})

        for character in response:
            chat_history[-1]['content'] += character
            time.sleep(0.005)

            yield chat_history


with gr.Blocks(title='MCP RSS client') as demo:
    with gr.Row():
        gr.HTML(html.TITLE)

    gr.Markdown(html.DESCRIPTION)

    # MCP connection/tool dump
    connect_btn = gr.Button('Connect to MCP server')
    status = gr.Textbox(label='MCP server tool dump', interactive=False, lines=4)
    connect_btn.click(# pylint: disable=no-member
        RSS_CLIENT.list_tools,
        outputs=status
    )

    # Dialog log output
    dialog_output = gr.Textbox(label='Internal dialog', lines=10, max_lines=100)
    timer = gr.Timer(0.5, active=True)

    timer.tick( # pylint: disable=no-member
        lambda: gradio_funcs.update_dialog(), # pylint: disable=unnecessary-lambda
        outputs=dialog_output
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
        user_message, [msg, chatbot], [msg, chatbot], queue=False
    ).then(
        send_message, chatbot, chatbot
    )


if __name__ == '__main__':

    # current_directory = os.getcwd()

    # if 'pyrite' in current_directory:
    logger.info('Starting RASS on LAN')
    demo.launch(server_name='0.0.0.0', server_port=7860)

    # else:
    #     logger.info('Starting RASS')
    #     demo.launch()
