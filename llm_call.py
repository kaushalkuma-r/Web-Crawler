import requests
import json
import os
from dotenv import load_dotenv
from time import time
import importlib

# Add these imports for local Llama
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
except ImportError:
    torch = None

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = "deepseek/deepseek-chat-v3-0324:free" #

_API = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM = (
    "You are an intent classifier for a trading chatbot. "
    "Return exactly one label from this set:\n"
    "VIEW_WITH_STRATEGY   - user shares a market/sector view AND explicitly wants trade ideas / strategies\n"
    "VIEW_NO_STRATEGY     - user shares a market/sector view but does NOT ask for strategies (might just discuss)\n"
    "OTHER                - any other chit-chat, greeting, question, etc.\n\n"
    "Output ONLY the label."
)

# Add these variables for local Llama
LLAMA_MODEL_NAME = "meta-llama/Meta-Llama-3-8B"
_llama_pipeline = None

def is_cuda_available():
    return torch and torch.cuda.is_available()

def get_llama_pipeline():
    global _llama_pipeline
    if _llama_pipeline is None:
        tokenizer = AutoTokenizer.from_pretrained(LLAMA_MODEL_NAME)
        model = AutoModelForCausalLM.from_pretrained(
            LLAMA_MODEL_NAME,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
        _llama_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            device=0 if torch.cuda.is_available() else -1,
        )
    return _llama_pipeline

def call_llama(prompt):
    pipe = get_llama_pipeline()
    result = pipe(prompt, max_new_tokens=512, do_sample=True, temperature=0.7)
    return result[0]['generated_text']

def call_llm(prompt):
    """
    Use local Llama-3-8B if CUDA is available, else use OpenRouter API.
    """
    if is_cuda_available():
        return call_llama(prompt)
    else:
        return call_openrouter(prompt)

def call_openrouter(prompt):
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://your-site.com",
            "X-Title": "Mistral"
        },
        data=json.dumps({
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        })
    )
    # time.sleep(2)
    response.raise_for_status()
    llm_response = response.json()
    return llm_response["choices"][0]["message"]["content"] 
