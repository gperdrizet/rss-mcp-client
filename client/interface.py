'''Functions for controlling chat flow between Gradio and Anthropic/MCP'''

import json
import logging
from anthropic.types import text_block
from gradio.components.chatbot import ChatMessage

from client import prompts
from client.anthropic_bridge import AnthropicBridge

async def agent_input(
        bridge: AnthropicBridge,
        chat_history: list
) -> list:

    '''Handles model interactions.'''

    function_logger = logging.getLogger(__name__ + '.agent_input')

    input_messages = format_chat_history(chat_history)
    result = await bridge.process_query(prompts.DEFAULT_SYSTEM_PROMPT, input_messages)

    if result['tool_result']:
        tool_call = result['tool_call']
        tool_name = tool_call['name']

        if tool_name == 'rss_mcp_server_get_feed':

            tool_parameters = tool_call['parameters']
            website = tool_parameters['website']
            user_query = input_messages[-1]['content']
            response_content = result['llm_response'].content[0]

            if isinstance(response_content, text_block.TextBlock):
                intermediate_reply = response_content.text
            else:
                intermediate_reply = f'I Will check the {website} RSS feed for you'

            function_logger.info('User query: %s', user_query)
            function_logger.info('Model intermediate reply: %s', intermediate_reply)
            function_logger.info('LLM called %s on %s', tool_name, website)

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

            function_logger.info('Re-prompting input %s', input_message)
            result = await bridge.process_query(prompts.GET_FEED_SYSTEM_PROMPT, input_message)

            try:

                final_reply = result['llm_response'].content[0].text

            except (IndexError, AttributeError):
                final_reply = 'No final reply from model'

            function_logger.info('LLM final reply: %s', final_reply)

            chat_history.append({
                "role": "assistant",
                "content": intermediate_reply
            })

            chat_history.append({
                "role": "assistant",
                "content": final_reply
            })

    else:
        try:
            reply = result['llm_response'].content[0].text

        except AttributeError:
            reply = 'Bad reply - could not parse'

        function_logger.info('Direct, no-tool reply: %s', reply)

        chat_history.append({
            "role": "assistant",
            "content": reply
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
