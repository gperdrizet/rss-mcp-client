'''Collection of prompts for Claude API calls in different
conversational contexts.'''

from string import Template

DEFAULT_SYSTEM_PROMPT = 'You are a helpful tool-using assistant.'

REPROMPTING_SYSTEM_PROMPT = '''
You are a helpful assistant. Your job is to facilitate interactions between a Human 
user and LLM agent. To complete the user's request or answer their question, you may
need to call multiple functions sequentially and use each output to formulate the next
function call until you arrive at the final answer. But if you can satisfy the request
with a single function call, you should do so.

Here is an example exchange between the user and agent using multiple functions calls:

user: Can you give me a link to the article about the FAA modernizing air traffic control technology?

agent: OK, let me find the article you are referring to.

function call: find_article("FAA modernizing air traffic control technology")

function return: {"title": "FAA To Eliminate Floppy Disks Used In Air Traffic Control Systems"}

function call: get_link("FAA To Eliminate Floppy Disks Used In Air Traffic Control Systems")

function return: {"link": "https://www.tomshardware.com/the-faa-seeks-to-eliminate-floppy-disk-usage-in-air-traffic-control-systems"}

assistant: Here is the link to the article: [FAA To Eliminate Floppy Disks Used In Air Traffic Control Systems](https://www.tomshardware.com/the-faa-seeks-to-eliminate-floppy-disk-usage-in-air-traffic-control-systems)
'''

GET_FEED_PROMPT = Template(
'''Below is an exchange between a user and an agent. The user has asked the agent 
to get new content from the $website RSS feed. In order to complete the request, 
the agent has called a function which returned the RSS feed content from $website 
in JSON format. Your job is to complete the exchange by using the returned JSON 
RSS feed data to write a human readable reply to the user.

user: $user_query

agent: $intermediate_reply

function call: get_feed_content("$website")

function return: $articles

assistant:'''
)

OTHER_TOOL_PROMPT = Template(
'''Below is an exchange between a user and an agent. The user has asked the agent 
"$user_query". The agent is completing the users request by calling a function or 
functions. Complete the exchange by either:

1. Calling the next function needed to get the information necessary to generate a 
final answer for the user.
2. Generating the final answer if you have enough information to do so already.

If no more information is needed to generate the final answer, do so without calling
additional tools.

agent: $prior_reply

user: $user_query

agent: $intermediate_reply

function call: $tool_name($tool_parameters)

function return: $tool_result
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