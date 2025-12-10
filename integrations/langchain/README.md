# Sentinel LangChain Hub Integration

Publish Sentinel alignment seeds to [LangChain Hub](https://smith.langchain.com/hub) for easy discovery and use.

## Setup

1. Create a LangSmith account at https://smith.langchain.com
2. Generate an API key in Settings
3. Set the environment variable:

```bash
export LANGSMITH_API_KEY="your-api-key"
```

## Publishing

```bash
cd sentinel/integrations/langchain
pip install langchain langsmith sentinelseed
python sentinel_prompt.py
```

## Usage (after publishing)

Once published, anyone can use the Sentinel prompt:

```python
from langchain import hub
from langchain_openai import ChatOpenAI

# Pull the Sentinel alignment seed
prompt = hub.pull("sentinelseed/alignment-seed")

# Use with any LLM
llm = ChatOpenAI(model="gpt-4o")
chain = prompt | llm

response = chain.invoke({
    "system_context": "",  # Optional additional context
    "input": "How can I improve my home security?"
})
```

## Available Prompts

| Prompt | Tokens | Description |
|--------|--------|-------------|
| `sentinelseed/alignment-seed` | ~1,400 | Standard THSP protocol |
| `sentinelseed/alignment-seed-minimal` | ~450 | Compact version |

## Links

- [LangChain Hub](https://smith.langchain.com/hub)
- [Sentinel Docs](https://sentinelseed.dev/docs)
- [sentinelseed on PyPI](https://pypi.org/project/sentinelseed/)
