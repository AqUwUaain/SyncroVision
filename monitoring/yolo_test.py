from ultralytics import YOLO
import cv2
import time

# =========================
# LOAD YOLO MODEL
# =========================

model = YOLO("yolov8n.pt")

# =========================
# CAMERA SOURCE SELECTOR
# =========================

print("\n=== SYNCROVISION AI ===\n")

print("1 = Webcam")
print("2 = RTSP / CCTV")
print("3 = HTTP / HLS Stream\n")

mode = input("Select source: ")

# =========================
# SOURCE LOGIC
# =========================

if mode == "1":

    camera_source = 0

elif mode == "2":

    camera_source = input(
        "\nEnter RTSP URL:\n"
    )

elif mode == "3":

    camera_source = input(
        "\nEnter HTTP/HLS URL:\n"
    )

else:

    print("INVALID OPTION")

    exit()

# =========================
# OPEN CAMERA
# =========================

print("\nOPENING SOURCE...\n")

# RTSP uses FFMPEG
if isinstance(camera_source, str):

    camera = cv2.VideoCapture(
        camera_source,
        cv2.CAP_FFMPEG
    )

else:

    camera = cv2.VideoCapture(
        camera_source
    )

# =========================
# CAMERA SETTINGS
# =========================

camera.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    1280
)

camera.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    720
)

# =========================
# CHECK CAMERA
# =========================

if not camera.isOpened():

    print("FAILED TO OPEN CAMERA")

    exit()

print("CAMERA CONNECTED\n")

# =========================
# FPS
# =========================

previous_time = 0

# =========================
# DETECTION TIMER
# =========================

last_detection_time = 0

# =========================
# SCAN LINE
# =========================

scan_y = 0

# =========================
# COLORS
# =========================

GREEN = (0, 255, 0)

RED = (0, 0, 255)

CYAN = (255, 255, 0)

WHITE = (255, 255, 255)

BLACK = (0, 0, 0)

# =========================
# ALLOWED CLASSES
# =========================

allowed_classes = {

    0: "PERSON",
    15: "CAT",
    16: "DOG",
    41: "CUP",
    56: "CHAIR",
    62: "TV",
    63: "LAPTOP",
    67: "PHONE"

}

# =========================
# MAIN LOOP
# =========================

while True:

    success, frame = camera.read()

    if not success:

        print("FRAME FAILED")

        break

    # =========================
    # BRIGHTNESS BOOST
    # =========================

    frame = cv2.convertScaleAbs(
        frame,
        alpha=1.15,
        beta=20
    )

    # =========================
    # YOLO AI
    # =========================

    results = model(
        frame,
        verbose=False
    )

    boxes = results[0].boxes

    detection_count = 0

    # =========================
    # PROCESS DETECTIONS
    # =========================

    if boxes is not None:

        for box in boxes:

            confidence = float(
                box.conf[0]
            )

            if confidence < 0.40:

                continue

            class_id = int(
                box.cls[0]
            )

            if class_id not in allowed_classes:

                continue

            detection_count += 1

            object_name = (
                allowed_classes[class_id]
            )

            x1, y1, x2, y2 = map(
                int,
                box.xyxy[0]
            )

            # PERSON = RED
            if object_name == "PERSON":

                box_color = RED

                last_detection_time = (
                    time.time()
                )

            else:

                box_color = GREEN

            # =========================
            # DRAW BOX
            # =========================

            cv2.rectangle(
                frame,
                (x1, y1),
                (x2, y2),
                box_color,
                3
            )

            # =========================
            # LABEL
            # =========================

            label = (
                f"{object_name} "
                f"{confidence:.2f}"
            )

            cv2.putText(
                frame,
                label,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                box_color,
                2
            )

    # =========================
    # FPS
    # =========================

    current_time = time.time()

    fps = 1 / (
        current_time - previous_time
    )

    previous_time = current_time

    # =========================
    # HUMAN DETECTION
    # =========================

    human_detected = (
        time.time() - last_detection_time
    ) < 2

    # =========================
    # UI OVERLAY
    # =========================

    overlay = frame.copy()

    cv2.rectangle(
        overlay,
        (0, 0),
        (470, 190),
        BLACK,
        -1
    )

    cv2.addWeighted(
        overlay,
        0.5,
        frame,
        0.5,
        0,
        frame
    )

    # =========================
    # LIVE ICON
    # =========================

    cv2.circle(
        frame,
        (420, 30),
        10,
        RED,
        -1
    )

    cv2.putText(
        frame,
        "LIVE",
        (440, 37),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        RED,
        2
    )

    # =========================
    # TITLE
    # =========================

    cv2.putText(
        frame,
        "SYNCROVISION AI",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        CYAN,
        2
    )

    # =========================
    # FPS
    # =========================

    cv2.putText(
        frame,
        f"FPS: {int(fps)}",
        (20, 75),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        GREEN,
        2
    )

    # =========================
    # OBJECT COUNT
    # =========================

    cv2.putText(
        frame,
        f"OBJECTS: {detection_count}",
        (20, 110),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        GREEN,
        2
    )

    # =========================
    # STATUS
    # =========================

    if human_detected:

        status_text = (
            "HUMAN ACTIVITY DETECTED"
        )

        status_color = RED

        cv2.rectangle(
            frame,
            (0, 0),
            (
                frame.shape[1],
                frame.shape[0]
            ),
            RED,
            6
        )

    else:

        status_text = "AREA CLEAR"

        status_color = GREEN

    cv2.putText(
        frame,
        status_text,
        (20, 145),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        status_color,
        2
    )

    # =========================
    # SOURCE DISPLAY
    # =========================

    cv2.putText(
        frame,
        f"SOURCE: {camera_source}",
        (20, 180),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        WHITE,
        2
    )

    # =========================
    # SCANNING LINE
    # =========================

    scan_y += 4

    if scan_y > frame.shape[0]:

        scan_y = 0

    cv2.line(
        frame,
        (0, scan_y),
        (frame.shape[1], scan_y),
        CYAN,
        2
    )

    # =========================
    # SHOW VIDEO
    # =========================

    cv2.imshow(
        "SYNCROVISION AI SURVEILLANCE",
        frame
    )

    # =========================
    # EXIT
    # =========================

    if cv2.waitKey(1) == 27:

        break

# =========================
# CLEANUP
# =========================

camera.release()

cv2.destroyAllWindows()