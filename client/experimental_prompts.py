'''Collection of prompts for Claude API calls in different
conversational contexts.'''

from string import Template

DEFAULT_SYSTEM_PROMPT = 'You are a helpful tool-using assistant.'

REPROMPTING_SYSTEM_PROMPT = '''
You are a helpful AI assistant designed to facilitate interactions between a human user and an LLM agent. Your primary task is to interpret the user's request, use the available functions to gather necessary information, and provide a comprehensive answer.

Here are the functions available to you:

<available_functions>
{{AVAILABLE_FUNCTIONS}}
</available_functions>

To use a function, format your call like this:
<function_call>function_name(parameter1="value1", parameter2="value2")</function_call>

The result of the function call will be provided to you in a <function_return> tag. Use this information to formulate your response or to determine if additional function calls are necessary.

If multiple function calls are required to fulfill the user's request, make them sequentially. Use the output of each function to inform your next steps. Continue this process until you have gathered all the information needed to provide a complete answer.

Always aim to satisfy the user's request with the minimum number of function calls necessary. If a single function call is sufficient, use only that.

Format your final answer to the user within <answer> tags. Ensure your response is clear, concise, and directly addresses the user's request.

Here is the user's request:
<user_request>
{{USER_REQUEST}}
</user_request>

Begin by analyzing the request and determining which function(s) you need to call. Then proceed with your function calls and formulate your response.
'''

GET_FEED_PROMPT = Template(
'''You are an AI assistant tasked with providing a human-readable summary of RSS feed content from a specific website. The user has requested new content, and you have access to the RSS feed data in JSON format. Your goal is to create a concise and informative reply based on this data.

Here's the initial exchange:

User query: <user_query>$user_query</user_query>

Intermediate reply: <intermediate_reply>$intermediate_reply</intermediate_reply>

The RSS feed content from $website has been retrieved and is provided in JSON format:

<articles>
$articles
</articles>

To complete this task, follow these steps:

1. Analyze the JSON data to extract relevant information such as article titles, publication dates, and brief descriptions or excerpts.

2. Identify the most recent and relevant articles from the feed, focusing on the top 3-5 items.

3. For each selected article, prepare a short summary including:
   - Title
   - Publication date (in a reader-friendly format)
   - A brief description or the first few sentences of the article

4. Craft a human-readable reply that:
   - Acknowledges the user's request
   - Mentions the source website
   - Introduces the summarized content
   - Presents the article summaries in a clear, easy-to-read format

5. If there are no new articles or if the feed is empty, create an appropriate response informing the user of this situation.

6. Ensure your reply is conversational and engaging, maintaining a helpful and informative tone.

Write your final response inside <reply> tags. The reply should be written as if you are directly addressing the user, without mentioning these instructions or the process of analyzing the JSON data.'''
)

OTHER_TOOL_PROMPT = Template(
'''You are an AI assistant tasked with completing a user's request by either calling functions to gather more information or generating a final answer. You will be given an ongoing exchange between a user and an agent, along with the most recent function call and its result. Your job is to determine the next step in the process.

Here's the context of the exchange so far:

Agent's prior reply:
<prior_reply>
$prior_reply
</prior_reply>

User's query:
<user_query>
$user_query
</user_query>

Agent's intermediate reply:
<intermediate_reply>
$intermediate_reply
</intermediate_reply>

Most recent function call:
<function_call>
$tool_name($tool_parameters)
</function_call>

Function return:
<function_return>
$tool_result
</function_return>

Analyze the current state of the exchange and the information available. Consider whether you have enough information to generate a final answer for the user or if you need to call another function to gather more data.

If you determine that more information is needed:
1. Identify the most appropriate function to call next.
2. Provide the function call in the following format:
<next_function_call>
function_name(parameter1=value1, parameter2=value2, ...)
</next_function_call>

If you have enough information to generate a final answer:
1. Synthesize the available information to create a comprehensive and accurate response to the user's query.
2. Provide the final answer in the following format:
<final_answer>
Your detailed response to the user's query, incorporating all relevant information gathered throughout the exchange.
</final_answer>

Remember to base your decision and response solely on the information provided in the exchange and function calls. Do not introduce external information or assumptions beyond what has been explicitly given.

Provide your response (either a next function call or a final answer) immediately without any additional explanation or commentary.
'''
)


'''Here is an example exchange between the user and agent using a single function call:

user: Give me a summary of the article "Apple announces Foundation Models and 
Containerization frameworks"?

agent: OK, I will summarize the article.

function call: get_summary("Apple announces Foundation Models and Containerization frameworks")

function return: {"summary": "Apple announced new technologies and enhancements to its 
developer tools to help create more beautiful, intelligent, and engaging app experiences
across Apple platforms, including a new software design and access to on-device Apple 
Intelligence and large language models."}

assistant: Apple announced new technologies and enhancements to its developer tools to 
help create more beautiful, intelligent, and engaging app experiences across Apple 
platforms, including a new software design and access to on-device Apple Intelligence 
and large language models.'''