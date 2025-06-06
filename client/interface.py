'''Functions for controlling chat flow between Gradio and Anthropic/MCP'''

import json
import logging
from gradio.components.chatbot import ChatMessage
from client.anthropic_bridge import AnthropicBridge

async def agent_input(bridge: AnthropicBridge, chat_history: list) -> list:
    '''Handles model interactions.'''

    function_logger = logging.getLogger(__name__ + '.agent_input')

    input_messages = format_chat_history(chat_history)
    result = await bridge.process_query(input_messages)
    function_logger.info(result)

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

    return chat_history


def format_chat_history(history) -> list[dict]:
    '''Formats gradio chat history for submission to anthropic.'''

    messages = []

    for chat_message in history:
        if isinstance(chat_message, ChatMessage):
            role, content = chat_message.role, chat_message.content
        else:
            role, content = chat_message.get("role"), chat_message.get("content")

        if role in ["user", "assistant", "system"]:
            messages.append({"role": role, "content": content})

    return messages
