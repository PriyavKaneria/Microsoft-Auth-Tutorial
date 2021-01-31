from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

app = FastAPI()
templates = Jinja2Templates(directory="templates")

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("login.html",{"request":request})

@app.get("/homepage")
async def homepage(request: Request):
    return templates.TemplateResponse("homepage.html",{"request":request})