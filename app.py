from fastapi import FastAPI, HTTPException, Request, Body, Path
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
import os
import httpx

# Initialize FastAPI app
app = FastAPI()

# Load environment variables
load_dotenv()

# Fetch OpenAI API key from environment variables
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
SESSION_ID = os.getenv("SESSION_ID")
CHAT_ID = os.getenv("CHAT_ID")
ID = os.getenv("ID")

if not ACCESS_TOKEN:
    raise HTTPException(status_code=500, detail="Missing ACCESS_TOKEN. Set it in your .env file.")

# Configure Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Serve static files from the 'assets' directory
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/", response_class=HTMLResponse)
async def read_blog(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/create-photo")
async def create_photo(prompt: str = Body(..., embed=True)):
    url = "https://chat.qwenlm.ai/api/chat/completions"
    headers = {
        "accept": "*/*",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "content-type": "application/json",
    }
    data = {
        "stream": False,
        "chat_type": "t2i",
        "model": "qwen-max-latest",
        "messages": [
            {
                "role": "user",
                "content": prompt,
                "extra": {}
            }
        ],
        "session_id": SESSION_ID,
        "chat_id": CHAT_ID,
        "id": ID,
        "size": "1024*1024"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            response_data = response.json()

             # Extract task_id from the response
            task_id = None
            for message in response_data.get("messages", []):
                if message.get("role") == "assistant" and "extra" in message:
                    task_id = message["extra"].get("wanx", {}).get("task_id")
                    break

            if not task_id:
                raise HTTPException(status_code=500, detail="Task ID not found in response")

            return {"task_id": task_id}
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/check-status/{task_id}")
async def check_status(task_id: str = Path(..., description="The ID of the task to check")):
    url = f"https://chat.qwenlm.ai/api/v1/tasks/status/{task_id}"
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer {ACCESS_TOKEN}",
        "content-type": "application/json"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))