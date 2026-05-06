from django.urls import path
from . import views

urlpatterns = [

    # LOGIN
    path('', views.login_view, name='login'),

    # DASHBOARD
    path(
        'dashboard/',
        views.dashboard_view,
        name='dashboard'
    ),

    # CAMERA SETTINGS
    path(
        'camera-settings/',
        views.camera_settings_view,
        name='camera_settings'
    ),

    # VIDEO STREAM
    path(
        'video-feed/',
        views.video_feed,
        name='video_feed'
    ),

    # LOGS
    path(
        'logs/',
        views.logs_view,
        name='logs'
    ),

    path(
        'login-attempts/',
        views.login_attempts_view,
        name='login_attempts'
    ),

    path(
        'camera-logs/',
        views.camera_logs_view,
        name='camera_logs'
    ),

    # LOGOUT
    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),
]