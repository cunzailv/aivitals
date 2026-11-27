from fastapi import FastAPI
from gateway.llm import ModelGateway
app = FastAPI()

@app.post("/run")
async def run(job):
    task_id = enqueue(job)
    return {"task_id": task_id}
