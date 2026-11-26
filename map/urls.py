from django.contrib import admin
from django.urls import path, include
from .views import (
    resources_map,
    home_page,
    questionnaire_page,
    actions_page,
    about_page,
    community_page,
    feature_detail_page,
    resource_count,
    ping,
)

from .intake_api import intake_page, mcp_search_page, triage_api, outcome_api
from .curation import review_resource
from .voice_api import transcribe_api

from .activity import record_activity

urlpatterns = [
    path("api/page-activity/", record_activity, name="page_activity"),
    path("api/transcribe/", transcribe_api, name="transcribe_api"),
    path("help/", intake_page, name="intake"),
    path("help/mcp/", mcp_search_page, name="mcp_search"),
    path("api/triage/", triage_api, name="triage_api"),
    path("api/recommendation-feedback/", outcome_api, name="outcome_api"),
    path("review/<str:token>/", review_resource, name="resource_review"),
    path("",home_page, name = "homepage"),
    path("actions/", actions_page, name="actions"),
    path("about/", about_page, name="about"),
    path("community/", community_page, name="community"),
    path("features/<slug:slug>/", feature_detail_page, name="feature_detail"),
    path("questionnaire/", questionnaire_page, name="questionnaire"),
    path("ping/", ping),
    path("map/", resources_map, name="resources_map"),
    path("resources/count/", resource_count, name="resource_count"),
    
]
