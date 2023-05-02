from supertokens_python import init, InputAppInfo
from supertokens_python.recipe import emailpassword
from supertokens_python.recipe.emailpassword.interfaces import APIInterface, APIOptions, SignUpPostOkResult
from supertokens_python.recipe.emailpassword.types import FormField
from typing import Dict, Any, List

from supertokens_python.recipe.usermetadata.asyncio import update_user_metadata
import datetime

from db_conn import db


def override_email_password_apis(original_implementation: APIInterface):
    original_sign_up_post = original_implementation.sign_up_post

    async def sign_up_post(form_fields: List[FormField], api_options: APIOptions, user_context: Dict[str, Any]):
        # First we call the original implementation of signInPOST.
        response = await original_sign_up_post(form_fields, api_options, user_context)

        # Post sign up response, we check if it was successful
        if isinstance(response, SignUpPostOkResult):
            _ = response.user.user_id
            __ = response.user.email

            # add username to database
            db.Users.insert_one({
                "user_id": response.user.user_id,
                "email": response.user.email,
                'first_name': form_fields[2].value,
                'last_name': form_fields[3].value,
                "favorites": [],
            })
            await update_user_metadata(response.user.user_id, {
                "first_name": form_fields[2].value,
                "last_name": form_fields[3].value,
            })

        return response

    original_implementation.sign_up_post = sign_up_post
    return original_implementation


def get_relative_time_description(then):
    now = datetime.datetime.now()
    diff = now - then
    if diff.days > 365:
        return f"{diff.days // 365} years ago"
    elif diff.days > 30:
        return f"{diff.days // 30} months ago"
    elif diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        return f"{diff.seconds // 3600} hours ago"
    elif diff.seconds > 60:
        return f"{diff.seconds // 60} minutes ago"
    else:
        return f"{diff.seconds} seconds ago"

