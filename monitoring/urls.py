from django.urls import path
from . import views

urlpatterns = [

    path('', views.login_view, name='login'),

    path('camera/', views.camera_view, name='camera'),

    path('video_feed/', views.video_feed, name='video_feed'),

    path('logs/', views.logs_view, name='logs'),

    path('login-attempts/',
         views.login_attempts_view,
         name='login_attempts'),

    path('camera-logs/',
         views.camera_logs_view,
         name='camera_logs'),

    path('logout/',
         views.logout_view,
         name='logout'),
]