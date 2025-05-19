import openai
from openai import OpenAI
import time
from functools import cache

class OpenAILLM:
    def __init__(self, llm_model_name, embedding_model_name):
        self.client = OpenAI(api_key="api-key")
        self.llm_model_name = llm_model_name
        self.embedding_model_name = embedding_model_name

    def get_llm_response(self, prompt, max_tokens=1024, timeout=600):
        n_retries = 10
        for i in range(n_retries):
            chat_completion = self.client.chat.completions.create(model=self.llm_model_name, messages=[{"role": "user", "content": prompt}], max_tokens=max_tokens, timeout=timeout)
            return chat_completion.choices[0].message.content

    @cache
    def get_embeddings(self, query):
        response = self.client.embeddings.create( 
            input=query,
            model=self.embedding_model_name
        )
        embeddings = response.data[0].embedding
        return embeddings