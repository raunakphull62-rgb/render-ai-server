"""
Smart Proxy Server for Render.com
==================================
Forwards requests to your Kaggle API.
When Kaggle is offline, shows a friendly message.

HOW TO UPDATE KAGGLE URL:
  Change KAGGLE_URL below to your new Ngrok URL
  then redeploy on Render (just push to GitHub).
"""

import os
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

# ============================================================
# UPDATE THIS every time you restart Kaggle!
# Paste your new Ngrok URL from Cell 5 output here.
# ============================================================
KAGGLE_URL = "https://clawless-superexplicitly-rayna.ngrok-free.dev"
# ============================================================

app = FastAPI(title="Qwen2.5-Coder-32B Proxy")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OFFLINE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AI Server Status</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      background: #0d1117;
      color: #e6edf3;
      font-family: sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }
    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 40px;
      max-width: 480px;
      text-align: center;
    }
    .emoji { font-size: 64px; margin-bottom: 16px; }
    h1 { color: #f78166; margin: 0 0 12px; }
    p  { color: #8b949e; line-height: 1.6; }
    .badge {
      display: inline-block;
      background: #21262d;
      border: 1px solid #30363d;
      border-radius: 20px;
      padding: 6px 16px;
      font-size: 13px;
      color: #8b949e;
      margin-top: 20px;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="emoji">😴</div>
    <h1>AI Server Sleeping</h1>
    <p>
      The Qwen2.5-Coder-32B AI server is currently offline.<br><br>
      The server runs on free GPU credits and sleeps when not in use.
      It will be back online shortly.
    </p>
    <div class="badge">⏱ Check back in 5-10 minutes</div>
    <br>
    <div class="badge">🤖 Qwen2.5-Coder-32B</div>
  </div>
</body>
</html>
"""

ONLINE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AI Server Status</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      background: #0d1117;
      color: #e6edf3;
      font-family: sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }
    .card {
      background: #161b22;
      border: 1px solid #30363d;
      border-radius: 12px;
      padding: 40px;
      max-width: 480px;
      text-align: center;
    }
    .emoji { font-size: 64px; margin-bottom: 16px; }
    h1 { color: #3fb950; margin: 0 0 12px; }
    p  { color: #8b949e; line-height: 1.6; }
    .badge {
      display: inline-block;
      background: #21262d;
      border: 1px solid #30363d;
      border-radius: 20px;
      padding: 6px 16px;
      font-size: 13px;
      color: #8b949e;
      margin-top: 12px;
    }
    .green { color: #3fb950; }
  </style>
</head>
<body>
  <div class="card">
    <div class="emoji">🚀</div>
    <h1>AI Server Online!</h1>
    <p>
      Qwen2.5-Coder-32B is running and ready.<br>
      Use the API endpoint below.
    </p>
    <div class="badge green">✅ Status: Online</div><br>
    <div class="badge">🤖 Qwen2.5-Coder-32B</div><br>
    <div class="badge">📡 /v1/chat/completions</div><br>
    <div class="badge">🔑 Use your API key</div>
  </div>
</body>
</html>
"""

async def is_kaggle_online() -> bool:
    """Check if Kaggle API is alive."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{KAGGLE_URL}/health")
            return r.status_code == 200
    except Exception:
        return False

@app.get("/", response_class=HTMLResponse)
async def root():
    """Status page — shows online/offline card."""
    if await is_kaggle_online():
        return HTMLResponse(content=ONLINE_HTML)
    return HTMLResponse(content=OFFLINE_HTML)

@app.get("/health")
async def health():
    """Proxy health check."""
    kaggle_online = await is_kaggle_online()
    return {
        "proxy_status": "online",
        "kaggle_status": "online" if kaggle_online else "offline",
        "kaggle_url": KAGGLE_URL,
        "model": "Qwen2.5-Coder-32B-Instruct",
    }

@app.get("/v1/models")
async def models(request: Request):
    """Forward models list to Kaggle."""
    if not await is_kaggle_online():
        return JSONResponse(
            status_code=503,
            content={"error": "AI server is offline. Please try again later."}
        )
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = dict(request.headers)
        r = await client.get(f"{KAGGLE_URL}/v1/models", headers=headers)
        return JSONResponse(content=r.json(), status_code=r.status_code)

@app.post("/v1/chat/completions")
async def chat(request: Request):
    """Forward chat requests to Kaggle API."""
    if not await is_kaggle_online():
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": "AI server is sleeping 😴 Please try again in 5-10 minutes.",
                    "type": "server_offline",
                    "code": 503
                }
            }
        )
    try:
        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(
                f"{KAGGLE_URL}/v1/chat/completions",
                content=body,
                headers=headers
            )
            return JSONResponse(content=r.json(), status_code=r.status_code)
    except httpx.TimeoutException:
        return JSONResponse(
            status_code=504,
            content={"error": "Request timed out. The model may be busy."}
        )
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"error": f"Proxy error: {str(e)}"}
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
