from fastapi import FastAPI
from api.leave import router as leave_router
from api.apply_leave import router as apply_leave_router

app = FastAPI(
    title="HR Agent Backend",
    description="APIs for Agentic HR Assistant",
    version="1.0.0"
)

app.include_router(leave_router)


app.include_router(apply_leave_router)

@app.get("/")
def health_check():
    return {"status": "HR backend running"}

