try:
    import cv2
except:
    cv2 = None
import time
import numpy as np

try:
    from pygrabber.dshow_graph import FilterGraph
except:
    FilterGraph = None
from django.http import StreamingHttpResponse
from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

from .models import AccessLog, LoginLog, CameraLog


# =========================
# CAMERA CONFIG
# =========================

CURRENT_CAMERA_MODE = "local"

CURRENT_CAMERA_INDEX = 0

CURRENT_CAMERA_URL = ""
# DETECT AVAILABLE CAMERAS
def get_available_cameras():

    try:

        graph = FilterGraph()

        devices = graph.get_input_devices()

        return devices

    except:

        return []

# LIVE MONITOR VARIABLES
CURRENT_FPS = 0

CURRENT_DETECTION_STATUS = "IDLE"

CURRENT_STREAM_STATUS = "Offline"


# =========================
# LOGIN
# =========================

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


# =========================
# LOGOUT
# =========================

@login_required
def logout_view(request):

    logout(request)

    return redirect('/')


# =========================
# DASHBOARD
# =========================

@login_required
def dashboard_view(request):

    global CURRENT_FPS
    global CURRENT_DETECTION_STATUS
    global CURRENT_STREAM_STATUS

    ip = request.META.get('REMOTE_ADDR')

    AccessLog.objects.create(
        user=request.user,
        ip_address=ip
    )

    accessLogs = AccessLog.objects.order_by('-timestamp')[:5]
    loginLogs = LoginLog.objects.order_by('-timestamp')[:5]
    cameraLogs = CameraLog.objects.order_by('-timestamp')[:5]

    # CAMERA SOURCE DISPLAY
    if CURRENT_CAMERA_MODE == "local":

        available_cameras = get_available_cameras()

        try:

            current_source = available_cameras[
                CURRENT_CAMERA_INDEX
             ]

        except:

            current_source = (
                f"Local Camera "
                f"({CURRENT_CAMERA_INDEX})"
            )

    else:

        current_source = CURRENT_CAMERA_URL

    context = {

        'accessLogs': accessLogs,
        'loginLogs': loginLogs,
        'cameraLogs': cameraLogs,

        'camera_mode': CURRENT_CAMERA_MODE,
        'camera_source': current_source,

        'current_fps': CURRENT_FPS,
        'detection_status': CURRENT_DETECTION_STATUS,
        'stream_status': CURRENT_STREAM_STATUS,

    }

    return render(
        request,
        'monitoring/camera.html',
        context
    )


# =========================
# CAMERA SETTINGS
# =========================

@login_required
def camera_settings_view(request):

    global CURRENT_CAMERA_MODE
    global CURRENT_CAMERA_INDEX
    global CURRENT_CAMERA_URL

    if request.method == 'POST':

        camera_mode = request.POST.get(
            'camera_mode'
        )

        CURRENT_CAMERA_MODE = camera_mode

        # LOCAL CAMERA
        if camera_mode == "local":

            try:

                CURRENT_CAMERA_INDEX = int(
                    request.POST.get(
                        'camera_index'
                    )
                )

            except:

                CURRENT_CAMERA_INDEX = 0

        # IP CAMERA
        elif camera_mode == "ip":

            CURRENT_CAMERA_URL = request.POST.get(
                'camera_url'
            )

    available_cameras = get_available_cameras()

    return render(
        request,
            'monitoring/camera_settings.html',
            {
                'current_camera': CURRENT_CAMERA_INDEX,
                'current_mode': CURRENT_CAMERA_MODE,
                'current_url': CURRENT_CAMERA_URL,
                'available_cameras': available_cameras
            }
)


# =========================
# CAMERA SYSTEM
# =========================

# =========================
# CAMERA SYSTEM
# =========================

def generate_frames():

    global CURRENT_CAMERA_MODE
    global CURRENT_CAMERA_INDEX
    global CURRENT_CAMERA_URL

    global CURRENT_FPS
    global CURRENT_DETECTION_STATUS
    global CURRENT_STREAM_STATUS

    if cv2 is None:

        CURRENT_STREAM_STATUS = "Offline"
        CURRENT_DETECTION_STATUS = "Disabled"

        while True:

            time.sleep(1)

    # =========================
    # OPEN CAMERA
    # =========================

    if CURRENT_CAMERA_MODE == "local":

        print("OPENING LOCAL CAMERA")

        camera = cv2.VideoCapture(
            CURRENT_CAMERA_INDEX
        )

    else:

        print("OPENING RTSP CAMERA")
        print("URL:", CURRENT_CAMERA_URL)

        # FFMPEG MODE
        camera = cv2.VideoCapture(
            CURRENT_CAMERA_URL,
            cv2.CAP_FFMPEG
        )

        print("FFMPEG STATUS:", camera.isOpened())

        # FALLBACK
        if not camera.isOpened():

            print("FFMPEG FAILED")
            print("TRYING NORMAL MODE")

            camera = cv2.VideoCapture(
                CURRENT_CAMERA_URL
            )

        print("FINAL STATUS:", camera.isOpened())

        # TOTAL FAILURE
        if not camera.isOpened():

            CURRENT_STREAM_STATUS = "Offline"
            CURRENT_DETECTION_STATUS = "Disconnected"

            while True:

                black_frame = (
                    np.zeros(
                        (550, 900, 3),
                        dtype=np.uint8
                    )
                )

                cv2.putText(
                    black_frame,
                    "RTSP CONNECTION FAILED",
                    (180, 250),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 0, 255),
                    3
                )

                cv2.putText(
                    black_frame,
                    CURRENT_CAMERA_URL,
                    (20, 320),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1
                )

                ret, buffer = cv2.imencode(
                    '.jpg',
                    black_frame
                )

                frame = buffer.tobytes()

                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' +
                    frame +
                    b'\r\n'
                )

                time.sleep(1)

    # =========================
    # CAMERA SETTINGS
    # =========================

    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # =========================
    # FACE DETECTION
    # =========================

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades +
        'haarcascade_frontalface_default.xml'
    )

    previous_frame = None

    last_log_time = 0
    last_motion_update = 0

    prev_frame_time = time.time()

    # =========================
    # MAIN LOOP
    # =========================

    while True:

        success, frame = camera.read()

        # CAMERA FAILED
        if not success:

            print("FRAME READ FAILED")

            CURRENT_STREAM_STATUS = "Offline"

            black_frame = (
                np.zeros(
                    (550, 900, 3),
                    dtype=np.uint8
                )
            )

            cv2.putText(
                black_frame,
                "NO VIDEO FRAME",
                (250, 250),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3
            )

            ret, buffer = cv2.imencode(
                '.jpg',
                black_frame
            )

            frame = buffer.tobytes()

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' +
                frame +
                b'\r\n'
            )

            continue

        CURRENT_STREAM_STATUS = "Excellent"

        # =========================
        # FPS
        # =========================

        new_frame_time = time.time()

        fps = 1 / (
            new_frame_time -
            prev_frame_time
        )

        prev_frame_time = new_frame_time

        CURRENT_FPS = int(fps)

        current_time = time.time()

        # =========================
        # RESIZE
        # =========================

        frame = cv2.resize(
            frame,
            (900, 550)
        )

        # =========================
        # GRAYSCALE
        # =========================

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        # =========================
        # FACE DETECTION
        # =========================

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

        # =========================
        # MOTION DETECTION
        # =========================

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

            (x, y, w, h) = cv2.boundingRect(
                contour
            )

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

        # =========================
        # DETECTION STATUS
        # =========================

        if motion_detected and face_detected:

            CURRENT_DETECTION_STATUS = "ACTIVE"

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

            CURRENT_DETECTION_STATUS = "MOTION"

            cv2.putText(
                frame,
                "MOTION DETECTED",
                (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 255),
                3
            )

        else:

            CURRENT_DETECTION_STATUS = "IDLE"

        # =========================
        # CAMERA LABEL
        # =========================

        cv2.putText(
            frame,
            f"MODE: {CURRENT_CAMERA_MODE.upper()}",
            (20, 520),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        # =========================
        # ENCODE FRAME
        # =========================

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


# =========================
# VIDEO FEED
# =========================

def video_feed(request):

    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


# =========================
# WEBSITE LOGS
# =========================

@login_required
def logs_view(request):

    accessLogs = AccessLog.objects.order_by(
        '-timestamp'
    )

    return render(
        request,
        'monitoring/logs.html',
        {
            'accessLogs': accessLogs
        }
    )


# =========================
# LOGIN LOGS
# =========================

@login_required
def login_attempts_view(request):

    loginLogs = LoginLog.objects.order_by(
        '-timestamp'
    )

    return render(
        request,
        'monitoring/login_attempts.html',
        {
            'loginLogs': loginLogs
        }
    )


# =========================
# CAMERA LOGS
# =========================

@login_required
def camera_logs_view(request):

    cameraLogs = CameraLog.objects.order_by(
        '-timestamp'
    )

    return render(
        request,
        'monitoring/camera_logs.html',
        {
            'cameraLogs': cameraLogs
        }
    )