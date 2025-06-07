'''Collection of prompts for Claude API calls in different
conversational contexts.'''

from string import Template

DEFAULT_SYSTEM_PROMPT = 'You are a helpful tool-using assistant.'

GET_FEED_SYSTEM_PROMPT = '''
You are a helpful assistant. Your job is to facilitate interactions between
Human users and LLM agents.
'''

GET_FEED_PROMPT = Template(
'''
Below is an exchange between a user and an agent. The user has asked 
the agent to get new content from the $website RSS feed. In order to
complete the request, the agent has called a function which returned
the RSS feed content from $website in JSON format. Your job is to 
complete the exchange by using the returned JSON RSS feed data to write
a human readable reply to the user.

user: $user_query

agent: $intermediate_reply

function call: get_feed_content($website)

function return: $articles

assistant:
'''                       
)