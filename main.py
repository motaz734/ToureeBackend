from supertokens_python import init, InputAppInfo, SupertokensConfig, get_all_cors_headers
from supertokens_python.framework.fastapi import get_middleware
from supertokens_python.recipe import emailpassword, session, dashboard, usermetadata
from starlette.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from api import router as api_router
import pymongo

from utils import override_email_password_apis

init(
    app_info=InputAppInfo(
        app_name="Touree",
        api_domain="http://192.168.1.4:8000",
        website_domain="http://192.168.1.4:8000",
        api_base_path="/auth",
        website_base_path="/api"
    ),
    supertokens_config=SupertokensConfig(
        connection_uri="https://dev-3559c4e1d2e611ed90afe7f9c7039798-eu-west-1.aws.supertokens.io:3567",
        api_key="7uf6hhujIvbc8kRbodg=If4pGfP9Ci"
    ),
    framework='fastapi',
    recipe_list=[
        session.init(),  # initializes session features
        usermetadata.init(),
        emailpassword.init(
            sign_up_feature=emailpassword.InputSignUpFeature(
                form_fields=[
                    emailpassword.InputFormField(
                        id="first_name",
                        optional=False,
                    ),
                    emailpassword.InputFormField(
                        id="last_name",
                        optional=False,
                    ),
                ]
            ),
            override=emailpassword.InputOverrideConfig(
                apis=override_email_password_apis
            )
        ),
        dashboard.init()
    ],
    mode='asgi'
)

app = FastAPI()

app.add_middleware(get_middleware())


app.include_router(
    api_router,
    prefix="/api",
    tags=["api"],
    responses={404: {"description": "Not found"}},
)

# TODO: Add APIs


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],
    allow_credentials=True,
    allow_methods=["GET", "PUT", "POST", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type"] + get_all_cors_headers(),
)
