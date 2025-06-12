'''Collection of HTML elements for Gradio interface.'''

TITLE = (
    '''
        <center> 
            <h1>RASS (retrieval augmented simple syndication) Agent</h1>
            <h2>Agentic RSS feed reader</h2>
        </center>
    '''
)

DESCRIPTION = (
    '''
        <p><b>Problem</b>: I love RSS feeds, but need help keeping up with all of the content from my subscriptions.
        
        <b>Solution</b>: Build a tool to allow LLMs to find and interact with RSS feeds on behalf of the user.</p>
        <h2>Introduction</h2>
        <p>This demonstration uses sister space
        <a href='https://huggingface.co/spaces/gperdrizet/rss-mcp-server'>
        RSS feed reader</a> via MCP to interact with RSS feeds. Click 'Connect to MCP 
        server' to get started. If it takes a minute or two to reply, don't worry the inference
        container was probably cold and spinning up. Check out the 
        <a href='https://github.com/gperdrizet/MCP-hackathon/tree/main'>
        main project repo on GitHub</a>. Both Spaces by
        <a href=https://www.linkedin.com/in/gperdrizet/'>George Perdrizet</a>.</p>

        I love RSS feeds - they remind me of a time when the internet was a weird and
        wonderful place, filled with interesting content hiding behind every link. The tools
        to produce and navigate that content have improved by leaps and bounds. However, 
        the improvement has not come without some losses. Content often feels homogeneous and
        it is too often painfully apparent that your favorite platform has a large degree of
        control over what content you see and what content you don't.

        This tool give the user back some of that control. It let's them decide what content
        and sources they are interested in. I built it because I want access to diverse,
        unfiltered publishing by many sources, paired modern AI to help me navigate it. 
        I want the model to help me ingest my feed, not create it for me!
    '''
)

FEATURES_TOOLS ='''
    ## Features

    1. Inference with Anthropic's efficient claude-3-haiku model.
    2. Custom MCP client with asynchronous server side events, retry and error handling based on the excellent repo by [Adel Zaalouk](https://github.com/zanetworker/mcp-playground/tree/main).
    3. Multi-turn re-prompting to allow LLM workflows with multiple tool calls.
    4. Queue and worker system to show user what's going on 'under the hood' while the model calls tools and generates replies. 
    
    ## Tools

    1. `get_feed()`: Given a website name or URL, find its RSS feed and
        return recent article titles, links and a generated summary of content if
        avalible. Caches results for fast retrieval by other tools. Embeds content
        to vector database for subsequent RAG.
    2. `context_search()`: Vector search on article content for RAG context.
    3. `find_article()`: Uses vector search on article content to find title of article
        that user is referring to.
    4. `get_summary()`: Gets article summary from Redis cache using article title.
    5. `get_link()`: Gets article link from Redis cache using article title.
'''
