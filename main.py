import cv2
import datetime
from send_mail_custom_lib import EmailSender
import time
import os
import threading
from ultralytics import YOLO
import RPi.GPIO as GPIO


buzzer_pin = 23

GPIO.setmode(GPIO.BCM)
GPIO.setup(buzzer_pin, GPIO.OUT)
GPIO.output(buzzer_pin, GPIO.LOW)


loc = "/home/pi/Desktop/Code/"

# Load YOLO model for weapon detection
yolo_model = YOLO(loc+"weapon.pt")


def beep(duration):
    GPIO.output(buzzer_pin, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(buzzer_pin, GPIO.LOW)
    time.sleep(duration)
    
    
def process_video(input_video_path):
    recording_time = 30
    gun_exist = False
    gun_count = 0
    gun_video_count = 1

    recording = False
    last_recording_time = 0

    cap = cv2.VideoCapture(input_video_path)

    if not cap.isOpened():
        print("Could not open video cam")
        return

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) + 0.5)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) + 0.5)
    fps = 7

    out = None

    frame_count = 0
    display_interval = 5  # Display every 5 frames
    process_interval = 5  # Process every 5 frames

    while True:
        ret, frame = cap.read()

        if not ret:
            print("Could not read frame")
            break

        frame_count += 1

        # Process frame every process_interval frames
        if frame_count % process_interval != 0:
            continue

        # Weapon detection using YOLO
        gun_result = yolo_model(frame)
        for result in gun_result:
            conf = result.boxes.conf
            detections = result.boxes.xyxy

            gun_exist = any(conf[i] >= 0.65 for i in range(len(detections)))

        if gun_exist:
            gun_count += 1
        else:
            GPIO.output(buzzer_pin, GPIO.LOW)
            gun_count = 0
        
        if gun_count > 3:
            GPIO.output(buzzer_pin, GPIO.HIGH)
        
        # Start recording if weapon detected consistently
        current_time = time.time()

        if (
            not recording
            and gun_count > 5
            and (current_time - last_recording_time) >= 10
        ):
            os.makedirs("Output Video", exist_ok=True)
            output_filename = loc + f"Output Video/weapon{gun_video_count}.avi"
            out = cv2.VideoWriter(
                output_filename,
                cv2.VideoWriter_fourcc(*"XVID"),
                fps,
                (width, height),
            )
            print(f"Recording started: {output_filename}")
            gun_count = 0
            recording = True
            recording_start_time = current_time

        if recording:
            out.write(frame)
            if (current_time - recording_start_time) >= recording_time:
                recording = False
                gun_video_count += 1
                last_recording_time = current_time
                out.release()
                print(f"Recording stopped: {output_filename}")
                print("Sending video via email...")
                threading.Thread(
                    target=send_mail, args=("Weapon Detected", output_filename)
                ).start()

        # Display frame every display_interval frames
        if frame_count % display_interval == 0:
            # Display timestamp and weapon detection status
            cv2.putText(
                frame,
                datetime.datetime.now().strftime("%m-%d-%Y %H:%M%p"),
                (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.35,
                (0, 0, 255),
                1,
            )

            status_text = "Weapon Detected" if gun_exist else "Normal"
            color = (0, 0, 255) if gun_exist else (0, 255, 0)
            cv2.putText(
                frame, status_text, (0, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2
            )

            cv2.imshow("Recording...", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                GPIO.cleanup()
                break

    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()


def send_mail(body, attachment_filename):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    email_from = "svinayak580@gmail.com"
    email_pass = "lgap tuos eowo pyjl"
    email_to = ["choudhurysaptarshi03@gmail.com"]
    subject = "New email from Weapon Detection Module"

    email_sender = EmailSender(smtp_server, smtp_port, email_from, email_pass)
    start = time.time()
    email_sender.send_email(email_to, subject, body, attachment_filename)
    end = time.time()
    print(f"Email sent in {end - start:.2f} seconds")


    # Run the process on a video or camera (use 0 for default camera
#process_video(loc+"Video Tests/weapon_test.mp4")
process_video(0)


  