'''RSS MCP server demonstration client app.'''

import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

import gradio as gr
from classes.client import MCPClientWrapper

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

client = MCPClientWrapper('https://agents-mcp-hackathon-rss-mcp-server.hf.space/gradio_api/mcp/sse')

# def gradio_interface():
with gr.Blocks(title='MCP RSS client') as demo:
    gr.Markdown('# MCP RSS reader')
    gr.Markdown('Connect to the MCP RSS server: https://huggingface.co/spaces/Agents-MCP-Hackathon/rss-mcp-server')

    connect_btn = gr.Button('Connect')
    status = gr.Textbox(label='Connection Status', interactive=False, lines=50)
    connect_btn.click(client.list_tools, outputs=status) # pylint: disable=no-member


if __name__ == '__main__':

    demo.launch(debug=True)
