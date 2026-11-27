import redis, tiktoken
from gateway.llm import ModelGateway

def pack(history, docs, tools):
    enc = tiktoken.get_encoding("cl100k_base")
    return truncate(history, enc, max_tokens=8000)

def do(task_id, tenant_id, gw):
    gw.ainvoke(tenant_id, pack([], [], []))
