from django.contrib import admin
from .models import AccessLog, LoginLog, CameraLog

admin.site.register(AccessLog)
admin.site.register(LoginLog)
admin.site.register(CameraLog)