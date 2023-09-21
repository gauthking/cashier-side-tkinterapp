import tkinter as tkn
import cv2
from keras.models import model_from_json
from PIL import Image, ImageTk
import datetime
import os
import numpy as np

import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials

cred = credentials.Certificate('./sensorsprok-firebase-adminsdk-8lypo-862938d9d5.json')
app = firebase_admin.initialize_app(cred)
db = firestore.client()

json_file = open('./model/emotion_model.json', 'r')
loaded_model_json = json_file.read()
json_file.close()
emotion_model = model_from_json(loaded_model_json)

emotion_model.load_weights("./model/emotion_model.h5")
print("Loaded model from disk")

# video codec and recording filename
video_codec = cv2.VideoWriter_fourcc(*"XVID")
filename = "recs/camera_feed_recording.mp4"

# create the "recs" folder if it doesn't exist
if not os.path.exists("recs"):
    os.mkdir("recs")

# initialize the capture variable as None
cap = None
out = None
recording = False

emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful",
                3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}

# initialize the emotion_job variable to keep track of the emotion detection update
emotion_job = None
emotions_detected_list = [] 

employee_id = None
customer_id = None
customer_name = None
customer_gender = None


def start_camera():
    global cap, emotion_job
    # release any existing capture
    if cap is not None:
        cap.release()
    # initialize the capture, turning on the camera
    cap = cv2.VideoCapture(0)
    # start the emotion detection process
    emotion_job = window.after(5, perform_emotion_detection)


def perform_emotion_detection():
    global cap, emotion_job, emotions,emotions_detected_list
    if cap is not None:
        ret, frame = cap.read()
        if ret:
            # perform emotion detection on the frame here
            face_detector = cv2.CascadeClassifier('./haarcascades/haarcascade_frontalface_default.xml')
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            num_faces = face_detector.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)
            for (x, y, w, h) in num_faces:
                cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (0, 255, 0), 4)
                roi_gray_frame = gray_frame[y:y + h, x:x + w]
                cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray_frame, (48, 48)), -1), 0)
                
                # predict the emotions
                emotion_prediction = emotion_model.predict(cropped_img)
                maxindex = int(np.argmax(emotion_prediction))
                cv2.putText(frame, emotion_dict[maxindex], (x+5, y-20),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                print(emotion_dict[maxindex])
                emotions_detected_list.append(emotion_dict[maxindex])


            # update the camera feed with the processed frame
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            camera.imgtk = imgtk
            camera.config(image=imgtk)
            if recording and out is not None:
                # write frame to the video file
                out.write(frame)
            # schedule the next emotion detection update
            emotion_job = window.after(5, perform_emotion_detection)
        else:
            # If capturing is finished, stop the emotion detection
            stop_camera()

def get_input_values():
    global employee_id, customer_id, customer_name, customer_gender
    employee_id = cashier_id_input.get()
    customer_id = customer_id_input.get()
    customer_name = customer_name_input.get()
    customer_gender = customer_gender_input.get()



def stop_camera():
    global cap, out, emotion_job,emotions_detected_list
    if cap is not None:
        # Stop recording before stopping the camera
        if out is not None:
            out.release()
            out = None
            print("Recording saved:", filename)
            print("Saving file...")
        # Stop the emotion detection update loop
        if emotion_job is not None:
            window.after_cancel(emotion_job)
            emotion_job = None
        # Release the camera
        cap.release()
        cap = None
        # Clear the camera feed
        camera.config(image='')
        print("Camera feed stopped")
        print(emotions_detected_list)
        get_input_values()
        print(f"Customer Name: {customer_name}")

        data = {"Cashier-id":employee_id ,"Customer-name":customer_name, "emotion-data":emotions_detected_list }
        doc_id = customer_name+"_emotionData"
        db.collection("customer-satisfaction-data").document(doc_id).set(data)
        emotions_detected_list=[]
def update_datetime():
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    datetime_label.config(text=date_str)
    datetime_label.after(1000, update_datetime)


def main():
    global camera, cap, datetime_label, customer_name_input, window, customer_gender_input,customer_id_input,cashier_id_input
    window = tkn.Tk()
    window.geometry("1200x900")
    window.title("Cashier Side Application")
    window.configure(bg="black")

    heading_label = tkn.Label(
        window, text="Cashier Desk Portal - Emotion Detection", font=("Helvetica", 28, "bold"))
    heading_label.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

    # create a container frame to hold the left and right containers
    outer_container = tkn.Frame(
        window, padx=10, pady=10, bg="#2D2B2B",
    )
    outer_container.grid(row=2, column=0, padx=(
        20, 20), pady=(20, 20), sticky="nsew")
    window.grid_rowconfigure(2, weight=1)
    window.grid_columnconfigure(0, weight=1)

    outer_container.grid_columnconfigure(0, weight=1, minsize=500)
    outer_container.grid_columnconfigure(1, weight=1, minsize=600)
    outer_container.configure(
        highlightbackground="white", highlightthickness=1
    )

    # Left frame container for taking inputs
    left_container = tkn.Frame(outer_container, bg="black")
    left_container.grid(row=0, column=0, padx=10, pady=10)
    left_container.configure(highlightbackground="green", highlightthickness=3)

    # Left frame attributes
    # Cashier ID
    cashier_id_label = tkn.Label(
        left_container, text="Employee ID:", font=("Helvetica", 14))
    cashier_id_label.grid(row=0, column=0, sticky='w', padx=15, pady=10)
    cashier_id_input = tkn.Entry(left_container, font=("Helvetica", 14))
    cashier_id_input.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    # Customer ID
    customer_id_label = tkn.Label(
        left_container, text="Customer ID:", font=("Helvetica", 14))
    customer_id_label.grid(row=1, column=0, sticky='w', padx=15, pady=10)
    customer_id_input = tkn.Entry(left_container, font=("Helvetica", 14))
    customer_id_input.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    # Customer Name
    customer_name_label = tkn.Label(
        left_container, text="Customer Name:", font=("Helvetica", 14))
    customer_name_label.grid(row=2, column=0, sticky='w', padx=15, pady=10)
    customer_name_input = tkn.Entry(left_container, font=("Helvetica", 14))
    customer_name_input.grid(row=2, column=1, padx=10, pady=5, sticky="w")

    # Customer Gender
    customer_gender_label = tkn.Label(
        left_container, text="Customer Gender:", font=("Helvetica", 14))
    customer_gender_label.grid(row=3, column=0, sticky='w', padx=15, pady=10)
    customer_gender_input = tkn.Entry(left_container, font=("Helvetica", 14))
    customer_gender_input.grid(row=3, column=1, padx=6, pady=5, sticky="w")

    # RIGHT container for the camera feed view
    right_container = tkn.Frame(outer_container, padx=10, pady=10, bg="black")
    right_container.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    right_container.configure(
        highlightbackground="green", highlightthickness=3)

    # Label for the camera window
    camera = tkn.Label(right_container)
    camera.pack()

    # Buttons to start and stop camera feed
    start_button = tkn.Button(left_container, text="Start Feed", font=(
        "Helvetica", 14), command=start_camera)
    start_button.grid(row=4, column=0, padx=10, pady=5, sticky='w')

    stop_button = tkn.Button(left_container, text="Stop Feed", font=(
        "Helvetica", 14), command=stop_camera)
    stop_button.grid(row=4, column=1, padx=10, pady=5, sticky='w')

    datetime_label = tkn.Label(outer_container, font=("Helvetica", 14))
    datetime_label.grid(row=0, column=1, padx=10, pady=10, sticky="ne")
    update_datetime()

    # start the GUI app
    window.mainloop()


if __name__ == "__main__":
    main()
