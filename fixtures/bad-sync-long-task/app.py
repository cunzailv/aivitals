import os
from fastapi import FastAPI, Request
from langchain_openai import ChatOpenAI
from langchain.chains import LLMChain

app = FastAPI()

_sessions = {}
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
llm = ChatOpenAI(api_key=OPENAI_API_KEY)
chain = LLMChain(llm=llm)

@app.post("/run")
async def run(req: Request):
    payload = await req.json()
    result = await chain.ainvoke({"input": payload["q"]})
    _sessions[payload["sid"]] = result
    return {"result": result}

@app.post("/exec")
async def run_code(req: Request):
    payload = await req.json()
    return {"out": exec(payload["code"])}
