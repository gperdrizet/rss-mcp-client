'''RSS MCP server demonstration client app.'''

import os
import json
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

import gradio as gr
from gradio.components.chatbot import ChatMessage
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

    chat_history.append({"role": "user", "content": message})
    input_messages = format_chat_history(chat_history)
    function_logger.info(input_messages)

    result = await bridge.process_query(input_messages)
    function_logger.info(result)
    function_logger.info(result.keys())

    try:
        chat_history.append({
            "role": "assistant",
            "content": result['llm_response'].content[0].text
        })

    except AttributeError:
        function_logger.info('Model called the tool, but did not talk about it')

    if result['tool_result']:
        articles = json.loads(result['tool_result'].content)['text']
        function_logger.info(articles)
        tmp_chat_history = chat_history.copy()
        tmp_chat_history.append({
            "role": "assistant",
            "content": ('Here are the three most recent entries from the RSS ' +
                f'feed in JSON format. Tell the user what you have found: {json.dumps(articles)}')
        })

        tmp_input_messages = format_chat_history(tmp_chat_history)
        function_logger.info(tmp_input_messages)
        result = await bridge.process_query(tmp_input_messages)

        chat_history.append({
            "role": "assistant",
            "content": result['llm_response'].content[0].text
        })


    return '', chat_history


def format_chat_history(history) -> list[dict]:
    '''Formats gradio chat history for submission to anthropic.'''

    messages = []

    for chat_message in history:
        if isinstance(msg, ChatMessage):
            role, content = chat_message.role, chat_message.content
        else:
            role, content = chat_message.get("role"), chat_message.get("content")

        if role in ["user", "assistant", "system"]:
            messages.append({"role": role, "content": content})

    return messages


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
