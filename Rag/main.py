from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from rag import ask_hr

app=FastAPI()

class ChatRequest(BaseModel):
    question:str

class ChatResponse(BaseModel):
    answer:str
    sources: List[str] = []
@app.get("/")
def root():
    return{"status":"API is running"}

@app.post("/chat",response_model=ChatResponse)
def chat(req:ChatRequest):
    question=req.question.strip()

    if not question:
        return ChatResponse(answer="Please ask valid question.", sources=[])
    result = ask_hr(question)   # 👈 dict

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"]
    )