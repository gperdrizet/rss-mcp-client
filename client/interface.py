'''Functions for controlling chat flow between Gradio and Anthropic/MCP'''

import logging
import queue
from gradio.components.chatbot import ChatMessage

from client import prompts
from client.anthropic_bridge import AnthropicBridge
import client.gradio_functions as gradio_funcs
import client.tool_workflows as tool_funcs

# Create dialog logger
dialog = gradio_funcs.get_dialog_logger(clear = True)


async def agent_input(
        bridge: AnthropicBridge,
        output_queue: queue.Queue,
        chat_history: list
) -> list:

    '''Handles model interactions.'''

    logger = logging.getLogger(__name__ + '.agent_input')
    reply = 'No reply from LLM'

    user_query = chat_history[-1]['content']

    if len(chat_history) > 1:
        prior_reply = chat_history[-2]['content']

    else:
        prior_reply = ''

    dialog.info('User: %s', user_query)

    input_messages = format_chat_history(chat_history)
    result = await bridge.process_query(
        prompts.DEFAULT_SYSTEM_PROMPT,
        input_messages
    )

    if result['tool_result']:
        logger.info('LLM called tool, entering tool loop.')
        await tool_funcs.tool_loop(
            user_query,
            prior_reply,
            result,
            bridge,
            output_queue,
            dialog
        )

    else:
        logger.info('LLM replied directly.')

        try:
            reply = result['llm_response'].content[0].text

        except AttributeError:
            reply = 'Bad reply - could not parse'

        logger.info('Reply: %s', reply)
        output_queue.put(reply)

    output_queue.put('bot-finished')


def format_chat_history(history) -> list[dict]:
    '''Formats gradio chat history for submission to anthropic.'''

    messages = []

    for chat_message in history:
        if isinstance(chat_message, ChatMessage):
            role, content = chat_message.role, chat_message.content
        else:
            role, content = chat_message.get('role'), chat_message.get('content')

        if role in ['user', 'assistant', 'system']:
            messages.append({'role': role, 'content': content})

    return messages
