from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import sources, articles, posts

app = FastAPI(title="Klark API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sources.router)
app.include_router(articles.router)
app.include_router(posts.router)

@app.get("/health")
def health():
    return {"status": "ok", "service": "klark-api"}