from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import msal
import requests as rq

app = FastAPI()
templates = Jinja2Templates(directory="templates")

###############################################################################
############################# Azure App Credentials ###########################
###############################################################################

CLIENT_ID = "2b8c32a1-2d6d-4e5c-a15c-74867a5d6067"
CLIENT_SECRET = "X9qe_XM.8w~66jve4k1-ra0lL8YR~oKZS."
AUTHORITY = "https://login.microsoftonline.com/common"
API_LOCATION = "http://localhost:8000"
TOKEN_ENDPOINT = "/get_auth_token"
SCOPE = ["User.ReadBasic.All"]

###############################################################################
############################## MSAL Functions #################################
###############################################################################

def _load_cache():
    cache = msal.SerializableTokenCache()
    # if session.get("token_cache"):
    #     cache.deserialize(session["token_cache"])
    return cache

def _build_msal_app(cache=None, authority=None):
    return msal.ConfidentialClientApplication(
        CLIENT_ID, authority=authority or AUTHORITY,
        client_credential=CLIENT_SECRET, token_cache=cache)

def _build_auth_url(authority=None, scopes=None, state=None):
    return _build_msal_app(authority=authority).get_authorization_request_url(
        scopes or [],
        state=state,
        redirect_uri=API_LOCATION+TOKEN_ENDPOINT)

def _get_token_from_cache(scope=None):
    cache = _load_cache()  # This web app maintains one cache per session
    cca = _build_msal_app(cache=cache)
    accounts = cca.get_accounts()
    if accounts:  # So all account(s) belong to the current signed-in user
        result = cca.acquire_token_silent(scope, account=accounts[0])
        return result


@app.get("/")
async def root(request: Request):
    auth_url = _build_auth_url(scopes=SCOPE,state="/homepage")
    return templates.TemplateResponse("login.html",{"request":request, "auth_url":auth_url})

@app.get("/get_auth_token")
async def get_auth_token(request: Request, code: str, state: str):
    if code!="":
        cache = _load_cache()
        cca = _build_msal_app(cache=cache)
        result = cca.acquire_token_by_authorization_code(
            code,
            scopes=SCOPE,  # Misspelled scope would cause an HTTP 400 error here
            redirect_uri=API_LOCATION + TOKEN_ENDPOINT)
        print(result)
        print("Scopes : ",SCOPE)
        if "error" in result:
            print(result)
            raise HTTPException(status_code=400, detail="Unable to validate social login")
        token_to_encode = result.get("id_token_claims")
        accounts = cca.get_accounts()
        token = cca.acquire_token_silent(SCOPE,account=accounts[0])
        real_token = token["access_token"]
    else:
        print("NO CODE GIVEN BY MICROSOFT")
        raise HTTPException(status_code=400, detail="NO CODE GIVEN BY MICROSOFT")
    try :
        email = token_to_encode["preferred_username"]
        username = token_to_encode["name"]
    except:
        raise HTTPException(status_code=400, detail="Unsupported Email ID")
    return templates.TemplateResponse("microsoft_proxy.html", {"request":request, "redirect_url":state, "token":real_token, "username":username, "email":email})

@app.post("/add-microsoft-cookie")
async def get_token(request: Request):
    formdata = await request.form()
    token = formdata["sub"]
    response = JSONResponse({"access_token": token, "token_type": "bearer"})

    response.set_cookie(
        key="Authorization",
        value=f"Bearer {token}",
        domain="localhost",
        httponly=True,
        max_age=3600,          # 1 hours
        expires=3600,          # 1 hours
    )
    return response

@app.get("/homepage")
async def homepage(request: Request):
    access_token = request.cookies.get("Authorization")
    headers = {
        'Authorization' : '{0}'.format(access_token),
        'Content-Type': 'application/json'
    }    
    response = rq.get("https://graph.microsoft.com/v1.0/me", headers = headers).json()
    print(response)
    return templates.TemplateResponse("homepage.html",{"request":request, "data":response})

@app.get("/logout")
async def logout(request: Request):
    response = RedirectResponse(url="http://localhost:8000/", status_code=303)
    response.delete_cookie(key="Authorization", domain="localhost")
    return response