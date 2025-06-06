'''RSS MCP server demonstration client app.'''

import os
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

import gradio as gr
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

client = MCPClientWrapper('https://agents-mcp-hackathon-rss-mcp-server.hf.space/gradio_api/mcp/sse')
bridge = AnthropicBridge(
    client,
    api_key=os.environ['ANTHROPIC_API_KEY']
)

async def submit_input(message: str, chat_history: list) -> str:
    '''Submits user message to agent'''

    function_logger = logging.getLogger(__name__ + '.submit_input')

    result = await bridge.process_query(message)
    function_logger.info(result)
    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": result['llm_response'].content[0].text})

    return '', chat_history


with gr.Blocks(title='MCP RSS client') as demo:
    gr.Markdown('# MCP RSS reader')
    gr.Markdown(
        'Connect to the MCP RSS server: ' +
        'https://huggingface.co/spaces/Agents-MCP-Hackathon/rss-mcp-server'
    )

    connect_btn = gr.Button('Connect')
    status = gr.Textbox(label='Connection Status', interactive=False, lines=10)

    chatbot = gr.Chatbot(
        value=[],
        height=500,
        type='messages',
        show_copy_button=True,
        avatar_images=('👤', '🤖')
    )

    msg = gr.Textbox(
        label='Your Question',
        placeholder='Ask about an RSS feed',
        scale=4
    )

    connect_btn.click(client.list_tools, outputs=status) # pylint: disable=no-member
    msg.submit(submit_input, [msg, chatbot], [msg, chatbot]) # pylint: disable=no-member

if __name__ == '__main__':

    demo.launch(debug=True)
