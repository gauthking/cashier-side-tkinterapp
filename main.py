import tkinter as tk
from tkinter import messagebox
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

video_codec = cv2.VideoWriter_fourcc(*"XVID")
filename = "recs/camera_feed_recording.mp4"

if not os.path.exists("recs"):
    os.mkdir("recs")

cap = None
out = None
recording = False
emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Fearful",
                3: "Happy", 4: "Neutral", 5: "Sad", 6: "Surprised"}
emotion_job = None
emotions_detected_list = [] 
employee_id = None
customer_id = None
customer_name = None
customer_gender = None
camera_var = None  # Define camera_var globally

def get_available_cameras():
    available_cameras = []
    for i in range(10):  
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            available_cameras.append(i)
            print(i)
            cap.release()
    return available_cameras

def validate_customer_id(customer_id):
    return customer_id.isdigit() and len(customer_id) == 10

def start_camera():
    global cap, emotion_job
    if cap is not None:
        cap.release()
    if not check_inputs():
        tk.messagebox.showerror("Error", "All fields must be filled in before starting the feed.")
        return
    camera_index = int(camera_var.get())
    if camera_index not in get_available_cameras():
        tk.messagebox.showerror("Error", "Selected camera is not available.")
        return

    cap = cv2.VideoCapture(camera_index)
    
    # Additional check to ensure the camera is functioning
    if not cap.isOpened():
        tk.messagebox.showerror("Error", "Failed to open the selected camera.")
        return
    
    ret, _ = cap.read()
    if not ret:
        tk.messagebox.showerror("Error", "Selected camera is not connected or not functioning properly.")
        cap.release()
        return

    emotion_job = window.after(5, perform_emotion_detection)

def perform_emotion_detection():
    global cap, emotion_job, emotions, emotions_detected_list
    if cap is not None:
        ret, frame = cap.read()
        if ret:
            face_detector = cv2.CascadeClassifier('./haarcascades/haarcascade_frontalface_default.xml')
            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            num_faces = face_detector.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)
            for (x, y, w, h) in num_faces:
                cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (0, 255, 0), 4)
                roi_gray_frame = gray_frame[y:y + h, x:x + w]
                cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray_frame, (48, 48)), -1), 0)
                
                emotion_prediction = emotion_model.predict(cropped_img)
                maxindex = int(np.argmax(emotion_prediction))
                cv2.putText(frame, emotion_dict[maxindex], (x+5, y-20),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                print(emotion_dict[maxindex])
                emotions_detected_list.append(emotion_dict[maxindex])

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            camera.imgtk = imgtk
            camera.config(image=imgtk)
            if recording and out is not None:
                out.write(frame)
            emotion_job = window.after(5, perform_emotion_detection)
        else:
            stop_camera()

def check_inputs():
    global employee_id, customer_id, customer_name, customer_gender
    employee_id = cashier_id_input.get()
    customer_id = customer_id_input.get()
    customer_name = customer_name_input.get()
    customer_gender = customer_gender_input.get()
    
    if not employee_id or not customer_id or not customer_name or not customer_gender:
        return False
    if not validate_customer_id(customer_id):
        tk.messagebox.showerror("Error", "Customer ID must be a valid 10-digit phone number.")
        return False
    return True

def get_input_values():
    global employee_id, customer_id, customer_name, customer_gender
    employee_id = cashier_id_input.get()
    customer_id = customer_id_input.get()
    customer_name = customer_name_input.get()
    customer_gender = customer_gender_input.get()

def stop_camera():
    global cap, out, emotion_job, emotions_detected_list
    if cap is not None:
        if out is not None:
            out.release()
            out = None
            print("Recording saved:", filename)
            print("Saving file...")
        if emotion_job is not None:
            window.after_cancel(emotion_job)
            emotion_job = None
        cap.release()
        cap = None
        camera.config(image='')
        print("Camera feed stopped")
        print(emotions_detected_list)
        get_input_values()
        print(f"Customer ID: {customer_id}")
        if len(emotions_detected_list)!=0:
            try:            
                date = get_date()
                doc_id = customer_id+"_emotionData"

                datewise_doc_ref = db.collection("customer-satisfaction-data").document(doc_id).collection("datewise").document(date)
                datewise_doc = datewise_doc_ref.get()

                if datewise_doc.exists:
                    existing_data = datewise_doc.to_dict()
                    updated_emotion_data = existing_data.get('emotion-data', []) + emotions_detected_list
                else:
                    updated_emotion_data = emotions_detected_list

                data1 = {"customer-id": customer_id, "Customer-name": customer_name}
                data2 = {'Cashier-id': employee_id, 'emotion-data': updated_emotion_data}

                db.collection("customer-satisfaction-data").document(doc_id).set(data1)
                datewise_doc_ref.set(data2)

                print("posted data successfully into firestore")
            except Exception as e:
                print("An error occurred while posting to firestore - ", e)
            

        emotions_detected_list=[]

def update_datetime():
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    datetime_label.config(text=date_str)
    datetime_label.after(1000, update_datetime)

def get_date():
    now = datetime.datetime.now()
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
    return datetime_str[0:10]

def main():
    global camera, cap, datetime_label, customer_name_input, window, customer_gender_input, customer_id_input, cashier_id_input, camera_var
    window = tk.Tk()
    window.geometry("1200x900")
    window.title("Cashier Side Application")
    window.configure(bg="black")

    heading_label = tk.Label(
        window, text="Cashier Desk Portal - Emotion Detection", font=("Helvetica", 28, "bold"))
    heading_label.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

    outer_container = tk.Frame(
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

    left_container = tk.Frame(outer_container, bg="black")
    left_container.grid(row=0, column=0, padx=10, pady=10)
    left_container.configure(highlightbackground="green", highlightthickness=3)

    cashier_id_label = tk.Label(
        left_container, text="Employee ID:", font=("Helvetica", 14))
    cashier_id_label.grid(row=0, column=0, sticky='w', padx=15, pady=10)
    cashier_id_input = tk.Entry(left_container, font=("Helvetica", 14))
    cashier_id_input.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    customer_id_label = tk.Label(
        left_container, text="Customer ID:", font=("Helvetica", 14))
    customer_id_label.grid(row=1, column=0, sticky='w', padx=15, pady=10)
    customer_id_input = tk.Entry(left_container, font=("Helvetica", 14))
    customer_id_input.grid(row=1, column=1, padx=10, pady=5, sticky="w")

    customer_name_label = tk.Label(
        left_container, text="Customer Name:", font=("Helvetica", 14))
    customer_name_label.grid(row=2, column=0, sticky='w', padx=15, pady=10)
    customer_name_input = tk.Entry(left_container, font=("Helvetica", 14))
    customer_name_input.grid(row=2, column=1, padx=10, pady=5, sticky="w")

    customer_gender_label = tk.Label(
        left_container, text="Customer Gender:", font=("Helvetica", 14))
    customer_gender_label.grid(row=3, column=0, sticky='w', padx=15, pady=10)
    customer_gender_input = tk.Entry(left_container, font=("Helvetica", 14))
    customer_gender_input.grid(row=3, column=1, padx=6, pady=5, sticky="w")

    right_container = tk.Frame(outer_container, padx=10, pady=10, bg="black")
    right_container.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
    right_container.configure(
        highlightbackground="green", highlightthickness=3)

    camera = tk.Label(right_container)
    camera.pack()

    start_button = tk.Button(left_container, text="Start Feed", font=(
        "Helvetica", 14), command=start_camera)
    start_button.grid(row=4, column=0, padx=10, pady=5, sticky='w')

    stop_button = tk.Button(left_container, text="Stop Feed", font=(
        "Helvetica", 14), command=stop_camera)
    stop_button.grid(row=4, column=1, padx=10, pady=5, sticky='w')

    datetime_label = tk.Label(outer_container, font=("Helvetica", 14))
    datetime_label.grid(row=0, column=1, padx=10, pady=10, sticky="ne")
    update_datetime()

    # Camera selection option
    available_cameras = get_available_cameras()
    camera_var_label = tk.Label(
        left_container, text="Camera Select:", font=("Helvetica", 14))
    camera_var_label.grid(row=5, column=0, sticky='w', padx=15, pady=10)
    camera_var = tk.StringVar(value=str(available_cameras[0]) if available_cameras else "No camera available")
    camera_option_menu = tk.OptionMenu(left_container, camera_var, *available_cameras)
    camera_option_menu.grid(row=5, column=1, columnspan=2, padx=10, pady=5, sticky='w')

    window.mainloop()

if __name__ == "__main__":
    main()
