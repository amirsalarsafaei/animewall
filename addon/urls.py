from django.urls import path

from . import views

urlpatterns = [
    path("addon_oauth/", views.addon_oauth, name="start_app"),
    path("", views.addon_app, name="addon_app"),
    path("submit-image", views.submit_images, name="submit_selected_images")
]
