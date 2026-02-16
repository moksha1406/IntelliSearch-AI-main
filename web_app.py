from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
from pathlib import Path
import shutil

app = FastAPI()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h1>Private Knowledge Q&A</h1>
    <h3>Step 1: Upload Document</h3>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <button type="submit">Upload</button>
    </form>

    <h3>Step 2: Ask Question</h3>
    <form action="/ask" method="post">
        <input type="text" name="question" placeholder="Ask something">
        <button type="submit">Ask</button>
    </form>

    <br>
    <a href="/documents">View Documents</a>
    <br>
    <a href="/status">System Status</a>
    """

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # TODO: call your indexing function here

    return {"message": f"{file.filename} uploaded successfully"}

@app.get("/documents")
def list_documents():
    return {"documents": [f.name for f in UPLOAD_DIR.iterdir()]}

@app.post("/ask")
def ask_question(question: str = Form(...)):
    # TODO: call your retrieval logic here
    return {
        "question": question,
        "answer": "Temporary answer placeholder",
        "source": "Temporary source"
    }

@app.get("/status")
def status():
    return {
        "backend": "OK",
        "database": "Not connected yet",
        "llm": "Disabled"
    }
