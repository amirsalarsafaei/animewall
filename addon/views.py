from io import BytesIO
import logging

import httpx
from PIL import Image
from kenar.widgets.image_carousel_row import ImageCarouselRow
import pydantic
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from kenar.app import CreatePostAddonRequest, Scope
from kenar.oauth import OauthResourceType
from rest_framework.decorators import api_view

from addon.models import Post
from boilerplate import settings
from boilerplate.clients import get_divar_kenar_client
from oauth.models import OAuth
from oauth.schemas import OAuthSession, OAuthSessionType

logger = logging.getLogger(__name__)


@api_view(["GET"])
def addon_oauth(request):
    post_token = request.query_params.get("post_token")
    callback_url = request.query_params.get("return_url")

    post, _ = Post.objects.get_or_create(token=post_token)

    oauth_session = OAuthSession(
        callback_url=callback_url,
        type=OAuthSessionType.POST,
        post_token=post.token,
    )
    request.session[settings.OAUTH_SESSION_KEY] = oauth_session.model_dump(exclude_none=True)

    kenar_client = get_divar_kenar_client()

    oauth_scopes = [
        Scope(resource_type=OauthResourceType.USER_PHONE),
        Scope(resource_type=OauthResourceType.POST_ADDON_CREATE, resource_id=post_token),
    ]

    oauth_url = kenar_client.oauth.get_oauth_redirect(
        scopes=oauth_scopes,
        state=oauth_session.state,
    )

    return redirect(oauth_url)


@api_view(["GET"])
def addon_app(request):
    resp = httpx.get("https://api.nekosapi.com/v3/images/random", params={"rating":"safe", "limit": 20})
    resp.raise_for_status()
    logger.info(resp.json())
    res = []
    for item in resp.json()["items"]:
        is_nsfw = False
        for tag in item["tags"]:
            if tag.get("is_nsfw", False):
                is_nsfw = True
                break
        if is_nsfw:
            continue
        res.append({
            "sample": item["sample_url"],
            "url": item["image_url"],
            "alt": item.get("source", "source not found")
            })

    return render(request, "addon/selectwall.html", {
            "anime_images": res,
        })

@api_view(["POST"])
def submit_images(request):
    logger.error("hello")

    try:
        oauth_session = OAuthSession(**request.session.get(settings.OAUTH_SESSION_KEY))
    except pydantic.ValidationError as e:
        logger.error(e)
        return HttpResponseForbidden("permission denied")

    try:
        oauth = OAuth.objects.get(session_id=request.session.session_key)
        post = oauth.post
    except OAuth.DoesNotExist:
        return HttpResponseForbidden("permission denied")

    selected_image_ids = request.POST.getlist('selected_images')
    logger.error(selected_image_ids)
    kenar_client = get_divar_kenar_client()

    image_ids = []

    for image in selected_image_ids:
        print(image)
        resp = httpx.get(image)
        resp.raise_for_status()
        webpImageIO = BytesIO(resp.content)
        image = Image.open(webpImageIO)
        jpegImageIO = BytesIO()
        image.convert("RGB").save(jpegImageIO, 'JPEG')

        resp = kenar_client.addon._client.put(
                url="https://divar.ir/v2/image-service/open-platform/image.jpg",
                content=jpegImageIO.getvalue(),
                headers={"Content-Type": "image/jpeg"},
        )

        resp.raise_for_status()
        image_ids.append(ImageCarouselRow.ImageCarouselRowItem(image_url=resp.json()['image_name'], description=""))

    kenar_client.addon.create_post_addon(access_token=oauth.access_token, data=CreatePostAddonRequest(token=post.token, widgets=[
        ImageCarouselRow(items=image_ids),

        ]))
    callback_url = oauth_session.get_callback_url()
    return redirect(callback_url)

# @api_view(["GET"])
# def addon_app_2(request):
#     try:
#         oauth_session = OAuthSession(**request.session.get(settings.OAUTH_SESSION_KEY))
#     except pydantic.ValidationError as e:
#         logger.error(e)
#         return HttpResponseForbidden("permission denied")
#
#     req_state = request.query_params.get("state")
#     if not req_state or req_state != oauth_session.get_state():
#         return HttpResponseForbidden("permission denied")
#
#     try:
#         oauth = OAuth.objects.get(session_id=request.session.session_key)
#         post = oauth.post
#     except OAuth.DoesNotExist:
#         return HttpResponseForbidden("permission denied")
#
#     # TODO: Implement logic for after opening your application in post
    # Example: create post addon

    # After processing the post logic, redirect to the callback URL
  
