'''Functions for controlling chat flow between Gradio and Anthropic/MCP'''

import json
import logging
import queue
from anthropic.types import text_block
from gradio.components.chatbot import ChatMessage

from client import prompts
from client.anthropic_bridge import AnthropicBridge
import client.gradio_functions as gradio_funcs

# Create dialog logger
dialog = gradio_funcs.get_dialog_logger(clear = True)


async def agent_input(
        bridge: AnthropicBridge,
        output_queue: queue.Queue,
        chat_history: list
) -> list:

    '''Handles model interactions.'''

    logger = logging.getLogger(__name__ + '.agent_input')

    user_query = chat_history[-1]['content']
    dialog.info('User: %s', user_query)

    input_messages = format_chat_history(chat_history)
    result = await bridge.process_query(
        prompts.DEFAULT_SYSTEM_PROMPT,
        input_messages
    )

    if result['tool_result']:
        tool_call = result['tool_call']
        tool_name = tool_call['name']

        if tool_name == 'rss_mcp_server_get_feed':

            tool_parameters = tool_call['parameters']
            website = tool_parameters['website']
            response_content = result['llm_response'].content[0]

            if isinstance(response_content, text_block.TextBlock):
                intermediate_reply = response_content.text
            else:
                intermediate_reply = f'I Will check the {website} RSS feed for you'

            output_queue.put(intermediate_reply)
            dialog.info('LLM: %s', intermediate_reply)
            dialog.info('LLM: called %s on %s', tool_name, website)

            articles = json.loads(result['tool_result'].content)['text']

            prompt = prompts.GET_FEED_PROMPT.substitute(
                website=website,
                user_query=user_query,
                intermediate_reply=intermediate_reply,
                articles=articles
            )

            input_message =[{
                'role': 'user',
                'content': prompt
            }]

            dialog.info('System: re-prompting LLM with return from %s call', tool_name)
            dialog.info('New prompt: %s ...', prompt[:75])

            logger.info('Re-prompting input %s', input_message)
            result = await bridge.process_query(
                prompts.GET_FEED_SYSTEM_PROMPT,
                input_message
            )

            try:

                reply = result['llm_response'].content[0].text

            except (IndexError, AttributeError):
                reply = 'No final reply from model'

            logger.info('LLM final reply: %s', reply)

    else:
        try:
            reply = result['llm_response'].content[0].text

        except AttributeError:
            reply = 'Bad reply - could not parse'

        logger.info('Direct, no-tool reply: %s', reply)

    dialog.info('LLM: %s ...', reply[:175])
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
