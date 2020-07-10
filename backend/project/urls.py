"""project URL Configuration.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
import os
from django.contrib import admin
from django.urls import path, re_path
from django.conf import settings
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

from server import views

urlpatterns = [  # pylint: disable=C0103
    path("admin/", admin.site.urls),
    re_path(
        "^graphql",
        csrf_exempt(GraphQLView.as_view(graphiql=(os.getenv("GRAPHIQL") or False))),
    ),
    path("predictions", csrf_exempt(views.predictions), name="predictions"),
    path("fixtures", csrf_exempt(views.fixtures), name="fixtures"),
    path("matches", csrf_exempt(views.matches), name="matches"),
]

if settings.ENVIRONMENT == "production":
    urlpatterns.append(re_path("", TemplateView.as_view(template_name="index.html")))
