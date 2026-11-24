from fastapi import FastAPI

app = FastAPI(title="Adrobot")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
