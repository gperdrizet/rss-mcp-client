'''Functions to handle re-prompting and final reply generation
downstream of LLM tool calls.'''

import json
import logging
import queue
from anthropic.types import text_block
from client import prompts
from client.anthropic_bridge import AnthropicBridge

INTERMEDIATE_REPLY_HINTS = {
    'rss_mcp_server_context_search': 'Let me find some additional context before I generate a final answer.',
    'rss_mcp_server_find_article': 'I will find the title of that article.',
    'rss_mcp_server_get_summary': 'I will summarize that article',
    'rss_mcp_server_get_link': 'I will get the link to that article'
}

async def tool_loop(
        user_query: str,
        prior_reply: str,
        result: list,
        bridge: AnthropicBridge,
        output_queue: queue.Queue,
        dialog: logging.Logger
) -> None:

    '''Re-prompts the LLM in a loop until it generates a final reply based on tool output.

    Args:
        user_query: the original user input that provoked the tool call
        result: the complete model reply containing the tool call
        bridge: AnthropicBridge class instance
        output_queue: queue to send results back to Gradio UI
        dialog: logger instance to record intermediate responses and internal dialog
    '''

    tool_call = result['tool_call']
    tool_name = tool_call['name']

    if tool_name == 'rss_mcp_server_get_feed':
        reply = await get_feed_call(
            user_query,
            result,
            bridge,
            output_queue,
            dialog
        )

        output_queue.put(reply)

    else:
        tool_call = result['tool_call']
        tool_name = tool_call['name']
        tool_parameters = tool_call['parameters']
        response_content = result['llm_response'].content[0]

        if isinstance(response_content, text_block.TextBlock):
            intermediate_reply = response_content.text
        else:
            intermediate_reply = INTERMEDIATE_REPLY_HINTS[tool_name]

        dialog.info('LLM intermediate reply: %s', intermediate_reply)
        dialog.info('MCP: called %s', tool_name)

        tool_result = json.loads(result['tool_result'].content)['text']

        prompt = prompts.OTHER_TOOL_PROMPT.substitute(
            user_query=user_query,
            prior_reply=prior_reply,
            intermediate_reply=intermediate_reply,
            tool_name=tool_name,
            tool_parameters=tool_parameters,
            tool_result=tool_result
        )

        dialog.info('System: re-prompting LLM with return from %s call', tool_name)

        while True:

            reply = await other_call(
                prompt,
                bridge,
                dialog
            )

            if 'final reply' in reply:
                final_reply = reply['final reply']
                dialog.info('LLM final reply: %s ...', final_reply[:50])
                output_queue.put(final_reply)
                break

            else:
                prompt = reply['new_prompt']


async def get_feed_call(
        user_query: str,
        result: list,
        bridge: AnthropicBridge,
        output_queue: queue.Queue,
        dialog: logging.Logger
) -> str:

    '''Re-prompts LLM after a call to get_feed().
    
    Args:
        user_query: the original user input that provoked the tool call
        result: the complete model reply containing the tool call
        bridge: AnthropicBridge class instance
        output_queue: queue to send results back to Gradio UI
        dialog: logger instance to record intermediate responses and internal dialog
    '''

    tool_call = result['tool_call']
    tool_name = tool_call['name']
    tool_parameters = tool_call['parameters']
    website = tool_parameters['website']
    response_content = result['llm_response'].content[0]

    if isinstance(response_content, text_block.TextBlock):
        intermediate_reply = response_content.text
    else:
        intermediate_reply = f'I Will check the {website} RSS feed for you'

    dialog.info('LLM intermediate reply: %s', intermediate_reply)
    dialog.info('MCP: called %s on %s', tool_name, website)

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

    result = await bridge.process_query(
        prompts.REPROMPTING_SYSTEM_PROMPT,
        input_message
    )

    try:

        reply = result['llm_response'].content[0].text

    except (IndexError, AttributeError):
        reply = 'No final reply from model'

    dialog.info('LLM final reply: %s ...', reply[:50])

    output_queue.put(reply)


async def other_call(
        prompt: list[dict],
        bridge: AnthropicBridge,
        dialog: logging.Logger
) -> dict:

    '''Re-prompts LLM after a call to get_feed().
    
    Args:
        prompt: prompt to to send the LLM
        result: the complete model reply containing the tool call
        bridge: AnthropicBridge class instance
        output_queue: queue to send results back to Gradio UI
        dialog: logger instance to record intermediate responses and internal dialog
    '''

    input_message =[{
        'role': 'user',
        'content': prompt
    }]

    result = await bridge.process_query(
        prompts.REPROMPTING_SYSTEM_PROMPT,
        input_message
    )

    if result['tool_result']:

        tool_call = result['tool_call']
        tool_name = tool_call['name']
        tool_parameters = tool_call['parameters']
        response_content = result['llm_response'].content[0]

        if isinstance(response_content, text_block.TextBlock):
            intermediate_reply = response_content.text
        else:
            intermediate_reply = INTERMEDIATE_REPLY_HINTS[tool_name]

        dialog.info('LLM intermediate reply: %s', intermediate_reply)
        dialog.info('MCP: called %s', tool_name)

        tool_result = json.loads(result['tool_result'].content)['text']

        prompt += f'agent: {intermediate_reply}\n'
        prompt += f'function call: {tool_name}("{tool_parameters}")'
        prompt += f'function return: {tool_result}'

        dialog.info('System: re-prompting LLM with return from %s call', tool_name)

        return {'new_prompt': prompt}

    else:

        reply = result['llm_response'].content[0].text
        return {'final reply': reply}
