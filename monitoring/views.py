import cv2
import time

from django.http import StreamingHttpResponse
from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

from .models import AccessLog, LoginLog, CameraLog


# GLOBAL CAMERA INDEX
CURRENT_CAMERA_INDEX = 0


# LOGIN
def login_view(request):

    error_message = None

    if request.method == 'POST':

        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(
            request,
            username=username,
            password=password
        )

        ip = request.META.get('REMOTE_ADDR')

        # SUCCESS
        if user is not None:

            LoginLog.objects.create(
                username=username,
                ip_address=ip,
                status='SUCCESS'
            )

            login(request, user)

            return redirect('/dashboard/')

        # FAILED
        else:

            LoginLog.objects.create(
                username=username,
                ip_address=ip,
                status='FAILED'
            )

            error_message = "Invalid username or password"

    return render(
        request,
        'monitoring/login.html',
        {
            'error_message': error_message
        }
    )


# LOGOUT
@login_required
def logout_view(request):

    logout(request)

    return redirect('/')


# DASHBOARD
@login_required
def dashboard_view(request):

    ip = request.META.get('REMOTE_ADDR')

    AccessLog.objects.create(
        user=request.user,
        ip_address=ip
    )

    accessLogs = AccessLog.objects.order_by('-timestamp')[:5]
    loginLogs = LoginLog.objects.order_by('-timestamp')[:5]
    cameraLogs = CameraLog.objects.order_by('-timestamp')[:5]

    context = {
        'accessLogs': accessLogs,
        'loginLogs': loginLogs,
        'cameraLogs': cameraLogs,
    }

    return render(
        request,
        'monitoring/camera.html',
        context
    )


# CAMERA SETTINGS
@login_required
def camera_settings_view(request):

    global CURRENT_CAMERA_INDEX

    if request.method == 'POST':

        try:

            CURRENT_CAMERA_INDEX = int(
                request.POST.get('camera_index')
            )

        except:

            CURRENT_CAMERA_INDEX = 0

    return render(
        request,
        'monitoring/camera_settings.html',
        {
            'current_camera': CURRENT_CAMERA_INDEX
        }
    )


# CAMERA SYSTEM
def generate_frames():

    global CURRENT_CAMERA_INDEX

    camera = cv2.VideoCapture(
        CURRENT_CAMERA_INDEX,
        cv2.CAP_DSHOW
    )

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        'haarcascade_frontalface_default.xml'
    )

    previous_frame = None

    last_log_time = 0
    last_motion_update = 0

    while True:

        success, frame = camera.read()

        if not success:
            break

        current_time = time.time()

        # RESIZE
        frame = cv2.resize(frame, (900, 550))

        # GRAYSCALE
        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        # FACE DETECTION
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(70, 70)
        )

        face_detected = False

        for (x, y, w, h) in faces:

            face_detected = True

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (255, 0, 0),
                3
            )

            cv2.putText(
                frame,
                "FACE DETECTED",
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 0, 0),
                2
            )

        # MOTION DETECTION
        gray_blur = cv2.GaussianBlur(
            gray,
            (21, 21),
            0
        )

        if previous_frame is None:

            previous_frame = gray_blur

            continue

        delta_frame = cv2.absdiff(
            previous_frame,
            gray_blur
        )

        if current_time - last_motion_update > 0.5:

            previous_frame = gray_blur

            last_motion_update = current_time

        thresh_frame = cv2.threshold(
            delta_frame,
            35,
            255,
            cv2.THRESH_BINARY
        )[1]

        thresh_frame = cv2.dilate(
            thresh_frame,
            None,
            iterations=2
        )

        contours, _ = cv2.findContours(
            thresh_frame,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        motion_detected = False

        for contour in contours:

            area = cv2.contourArea(contour)

            if area < 3500:
                continue

            (x, y, w, h) = cv2.boundingRect(contour)

            if w < 40 or h < 40:
                continue

            motion_detected = True

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                3
            )

        # HUMAN ACTIVITY
        if motion_detected and face_detected:

            cv2.putText(
                frame,
                "HUMAN ACTIVITY DETECTED",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                3
            )

            if current_time - last_log_time > 10:

                CameraLog.objects.create(
                    event="Human activity detected"
                )

                last_log_time = current_time

        elif motion_detected:

            cv2.putText(
                frame,
                "MOTION DETECTED",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                3
            )

        # ENCODE FRAME
        ret, buffer = cv2.imencode(
            '.jpg',
            frame
        )

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'
        )

    camera.release()


# VIDEO FEED
def video_feed(request):

    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


# WEBSITE LOGS
@login_required
def logs_view(request):

    accessLogs = AccessLog.objects.order_by('-timestamp')

    return render(
        request,
        'monitoring/logs.html',
        {
            'accessLogs': accessLogs
        }
    )


# LOGIN LOGS
@login_required
def login_attempts_view(request):

    loginLogs = LoginLog.objects.order_by('-timestamp')

    return render(
        request,
        'monitoring/login_attempts.html',
        {
            'loginLogs': loginLogs
        }
    )


# CAMERA LOGS
@login_required
def camera_logs_view(request):

    cameraLogs = CameraLog.objects.order_by('-timestamp')

    return render(
        request,
        'monitoring/camera_logs.html',
        {
            'cameraLogs': cameraLogs
        }
    )