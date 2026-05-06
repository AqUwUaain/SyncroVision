import cv2
from django.http import StreamingHttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from .models import AccessLog, LoginLog, CameraLog
import time


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

        if user is not None:

            LoginLog.objects.create(
                username=username,
                ip_address=ip,
                status='SUCCESS'
            )

            login(request, user)

            return redirect('/camera/')

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

@login_required
def camera_view(request):
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

    return render(request, 'monitoring/camera.html', context)

def generate_frames():

    camera = cv2.VideoCapture(0)

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

        # CURRENT TIME
        current_time = time.time()

        # Resize frame
        frame = cv2.resize(frame, (800, 500))

        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Blur image
        gray_blur = cv2.GaussianBlur(gray, (21, 21), 0)

        # INITIAL FRAME
        if previous_frame is None:
            previous_frame = gray_blur
            continue

        # FRAME DIFFERENCE
        delta_frame = cv2.absdiff(
            previous_frame,
            gray_blur
        )

        # UPDATE BACKGROUND FRAME EVERY 1 SECOND
        if current_time - last_motion_update > 1:

            previous_frame = gray_blur

            last_motion_update = current_time

        # THRESHOLD
        thresh_frame = cv2.threshold(
            delta_frame,
            30,
            255,
            cv2.THRESH_BINARY
        )[1]

        thresh_frame = cv2.dilate(
            thresh_frame,
            None,
            iterations=2
        )

        # FIND CONTOURS
        contours, _ = cv2.findContours(
            thresh_frame,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )

        motion_detected = False

        for contour in contours:

            # IGNORE SMALL MOVEMENTS
            if cv2.contourArea(contour) < 3500:
                continue

            motion_detected = True

            (x, y, w, h) = cv2.boundingRect(contour)

            # GREEN MOTION BOX
            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                3
            )

        # FACE DETECTION
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.2,
            minNeighbors=7,
            minSize=(90, 90)
        )

        face_detected = False

        for (x, y, w, h) in faces:

            face_detected = True

            # BLUE FACE BOX
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

            # SAVE LOG EVERY 10 SECONDS
            if current_time - last_log_time > 10:

                CameraLog.objects.create(
                    event="Human activity detected"
                )

                last_log_time = current_time

        # ONLY MOTION
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

        # CONVERT FRAME
        ret, buffer = cv2.imencode('.jpg', frame)

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame +
            b'\r\n'
        )


def video_feed(request):
    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )

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
@login_required
def logout_view(request):

    logout(request)

    return redirect('/')