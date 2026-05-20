try:
    import cv2
except:
    cv2 = None
import time
import numpy as np
import os

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

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

    camera = None

    # =========================
    # CAMERA OPEN FUNCTION
    # =========================

    def open_camera():

        global CURRENT_CAMERA_MODE
        global CURRENT_CAMERA_INDEX
        global CURRENT_CAMERA_URL

        try:

            # =========================
            # LOCAL CAMERA
            # =========================

            if CURRENT_CAMERA_MODE == "local":

                print("OPENING LOCAL CAMERA")

                cam = cv2.VideoCapture(
                    CURRENT_CAMERA_INDEX,
                    cv2.CAP_DSHOW
                )

                cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                time.sleep(1)

                success = False
                frame = None

                start_time = time.time()

                while time.time() - start_time < 5:

                    success, frame = cam.read()

                    if success and frame is not None:
                        break

                    time.sleep(0.1)

                print("LOCAL CAMERA TEST:", success)

                if success:
                    return cam

                cam.release()

                return None

            # =========================
            # RTSP / IP CAMERA
            # =========================

            else:

                print("OPENING RTSP CAMERA")
                print("URL:", CURRENT_CAMERA_URL)

                os.environ[
                    "OPENCV_FFMPEG_CAPTURE_OPTIONS"
                ] = (
                    "rtsp_transport;tcp|"
                    "stimeout;5000000|"
                    "buffer_size;1024000|"
                    "max_delay;500000"
                )

                cam = cv2.VideoCapture(
                    CURRENT_CAMERA_URL,
                    cv2.CAP_FFMPEG
                )

                cam.set(
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,
                    5000
                )

                cam.set(
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC,
                    5000
                )

                cam.set(
                    cv2.CAP_PROP_BUFFERSIZE,
                    1
                )

                time.sleep(1)

                print(
                    "FFMPEG STATUS:",
                    cam.isOpened()
                )

                success = False
                frame = None

                start_time = time.time()

                # =========================
                # SAFE FRAME TEST
                # =========================

                while time.time() - start_time < 5:

                    success, frame = cam.read()

                    if success and frame is not None:
                        break

                    time.sleep(0.1)

                print("FIRST FRAME:", success)

                # =========================
                # FALLBACK NORMAL MODE
                # =========================

                if not success:

                    print("FFMPEG FAILED")
                    print("TRYING NORMAL MODE")

                    try:
                        cam.release()
                    except:
                        pass

                    time.sleep(1)

                    cam = cv2.VideoCapture(
                        CURRENT_CAMERA_URL
                    )

                    cam.set(
                        cv2.CAP_PROP_BUFFERSIZE,
                        1
                    )

                    success = False
                    frame = None

                    start_time = time.time()

                    while time.time() - start_time < 5:

                        success, frame = cam.read()

                        if success and frame is not None:
                            break

                        time.sleep(0.1)

                    print(
                        "NORMAL MODE STATUS:",
                        success
                    )

                if success:
                    return cam

                try:
                    cam.release()
                except:
                    pass

                return None

        except Exception as e:

            print("CAMERA OPEN ERROR:", e)

            return None

    # =========================
    # INITIAL CAMERA OPEN
    # =========================

    camera = open_camera()

    reconnect_attempts = 0

    # =========================
    # MAIN LOOP
    # =========================

    while True:

        # =========================
        # CAMERA NOT AVAILABLE
        # =========================

        if camera is None:

            CURRENT_STREAM_STATUS = "Offline"
            CURRENT_DETECTION_STATUS = "Disconnected"

            reconnect_attempts += 1

            print(
                f"RECONNECT ATTEMPT: "
                f"{reconnect_attempts}"
            )

            black_frame = np.zeros(
                (550, 900, 3),
                dtype=np.uint8
            )

            cv2.putText(
                black_frame,
                "CAMERA OFFLINE",
                (220, 220),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.4,
                (0, 0, 255),
                4
            )

            cv2.putText(
                black_frame,
                "ATTEMPTING RECONNECT...",
                (170, 300),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.9,
                (255, 255, 255),
                2
            )

            cv2.putText(
                black_frame,
                f"ATTEMPT #{reconnect_attempts}",
                (300, 360),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
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

            time.sleep(2)

            camera = open_camera()

            continue

        # =========================
        # READ FRAME
        # =========================

        try:

            read_start = time.time()

            success = False
            frame = None

            while time.time() - read_start < 5:

                success, frame = camera.read()

                if success and frame is not None:
                    break

                time.sleep(0.05)

        except Exception as e:

            print("READ ERROR:", e)

            success = False
            frame = None

        # =========================
        # FRAME FAILED
        # =========================

        if not success or frame is None:

            print("FRAME READ FAILED")

            CURRENT_STREAM_STATUS = "Offline"

            try:
                camera.release()
            except:
                pass

            cv2.destroyAllWindows()

            camera = None

            continue

        reconnect_attempts = 0

        # =========================
        # CAMERA ACTIVE
        # =========================

        CURRENT_STREAM_STATUS = "Excellent"

        # Resize

        frame = cv2.resize(
            frame,
            (900, 550)
        )

        # =========================
        # FPS
        # =========================

        CURRENT_FPS = int(
            camera.get(cv2.CAP_PROP_FPS)
        )

        if CURRENT_FPS <= 0:
            CURRENT_FPS = 30

        current_time = time.time()

        # =========================
        # FACE DETECTION
        # =========================

        gray = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2GRAY
        )

        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades +
            'haarcascade_frontalface_default.xml'
        )

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

        # =========================
        # DETECTION STATUS
        # =========================

        if face_detected:

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
        # ENCODE
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