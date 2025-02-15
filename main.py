import os
import sys
import tkinter as tk
from tkinter import messagebox
import cv2
from keras.models import model_from_json
from PIL import Image, ImageTk
import datetime
import numpy as np
import firebase_admin
from firebase_admin import firestore
from firebase_admin import credentials
import logging

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

cred = credentials.Certificate(resource_path('sensorsprok-firebase-adminsdk-8lypo-862938d9d5.json'))
app = firebase_admin.initialize_app(cred)
db = firestore.client()

json_file = open(resource_path('models/emotion_model.json'), 'r')
loaded_model_json = json_file.read()
json_file.close()
emotion_model = model_from_json(loaded_model_json)
emotion_model.load_weights(resource_path("models/emotion_model.h5"))
print("Loaded model from disk")

print("Loaded model from disk")

video_codec = cv2.VideoWriter_fourcc(*"XVID")

cap = None
out = None
recording = False
emotion_dict = {0: "Angry", 1: "Disgusted", 2: "Concerned",
                3: "Happy", 4: "Neutral", 5: "Unsatisfied", 6: "Surprised"}
emotion_job = None
emotions_detected_list = []
employee_id = None
customer_id = None
customer_name = None
customer_gender = None
camera_var = None  
store_id = None

DETECTION_INTERVAL_MS = 100  

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
    
    if not cap.isOpened():
        tk.messagebox.showerror("Error", "Failed to open the selected camera.")
        return
    
    ret, _ = cap.read()
    if not ret:
        tk.messagebox.showerror("Error", "Selected camera is not connected or not functioning properly.")
        cap.release()
        return

    emotion_job = window.after(5, perform_emotion_detection)

def process_emotions_for_server(emotions_list):
    # """
    # Process the emotions list to reduce neutral entries before sending to server.
    # Uses surrounding emotions to replace some neutral entries intelligently.
    # """
    if not emotions_list:
        return emotions_list
        
    processed_emotions = emotions_list.copy()
    
    # Find indices of all neutral emotions
    neutral_indices = [i for i, emotion in enumerate(processed_emotions) if emotion == "Neutral"]
    
    for idx in neutral_indices:
        # Get emotions before and after the neutral emotion
        prev_emotion = processed_emotions[idx - 1] if idx > 0 else None
        next_emotion = processed_emotions[idx + 1] if idx < len(processed_emotions) - 1 else None
        
        # If we have both previous and next emotions and they're the same
        if prev_emotion and next_emotion and prev_emotion == next_emotion and prev_emotion != "Neutral":
            processed_emotions[idx] = prev_emotion
            continue
            
        # If we have three consecutive neutrals, keep only the middle one
        if (idx > 0 and idx < len(processed_emotions) - 1 and
            processed_emotions[idx - 1] == "Neutral" and 
            processed_emotions[idx + 1] == "Neutral"):
            # Replace first and last neutral with nearby non-neutral emotions if available
            for search_idx in range(idx - 2, -1, -1):
                if processed_emotions[search_idx] != "Neutral":
                    processed_emotions[idx - 1] = processed_emotions[search_idx]
                    break
            for search_idx in range(idx + 2, len(processed_emotions)):
                if processed_emotions[search_idx] != "Neutral":
                    processed_emotions[idx + 1] = processed_emotions[search_idx]
                    break
                    
        # If this is an isolated neutral between two different emotions
        elif prev_emotion and next_emotion and prev_emotion != "Neutral" and next_emotion != "Neutral":
            # Use the emotion that appears more frequently in the nearby context
            context_before = processed_emotions[max(0, idx-3):idx]
            context_after = processed_emotions[idx+1:min(len(processed_emotions), idx+4)]
            
            context_emotions = context_before + context_after
            emotion_counts = {e: context_emotions.count(e) for e in set(context_emotions) if e != "Neutral"}
            
            if emotion_counts:
                most_common = max(emotion_counts.items(), key=lambda x: x[1])[0]
                processed_emotions[idx] = most_common
    
    return processed_emotions

def perform_emotion_detection():
    global cap, emotion_job, emotions_detected_list
    if cap is not None:
        ret, frame = cap.read()
        if ret:
            try:
                face_cascade_path = resource_path('haarcascades/haarcascade_frontalface_default.xml')
                face_detector = cv2.CascadeClassifier(face_cascade_path)
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_detector.detectMultiScale(gray_frame, scaleFactor=1.3, minNeighbors=5)

                if len(faces) > 0:
                    largest_face = max(faces, key=lambda f: f[2] * f[3])
                    (x, y, w, h) = largest_face
                    cv2.rectangle(frame, (x, y-50), (x+w, y+h+10), (0, 255, 0), 4)
                    
                    roi_gray_frame = gray_frame[y:y + h, x:x + w]
                    cropped_img = np.expand_dims(np.expand_dims(cv2.resize(roi_gray_frame, (48, 48)), -1), 0)

                    emotion_prediction = emotion_model.predict(cropped_img)
                    maxindex = int(np.argmax(emotion_prediction))
                    
                    cv2.putText(frame, emotion_dict[maxindex], (x+5, y-20),
                                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)
                    logging.info(f"Detected emotion: {emotion_dict[maxindex]}")
                    emotions_detected_list.append(emotion_dict[maxindex])

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                camera.imgtk = imgtk
                camera.config(image=imgtk)
                
                if recording and out is not None:
                    out.write(frame)

                emotion_job = window.after(DETECTION_INTERVAL_MS, perform_emotion_detection)
            except Exception as e:
                logging.error("Error during emotion detection: %s", e)
                stop_camera()
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
        if emotion_job is not None:
            window.after_cancel(emotion_job)
            emotion_job = None
        cap.release()
        cap = None
        camera.config(image='')
        print("Camera feed stopped")
        print(f"Original emotions: {emotions_detected_list}")
        get_input_values()
        print(f"Customer ID: {customer_id}")
        if len(emotions_detected_list) != 0:
            try:
                # Process emotions before sending to server
                processed_emotions = process_emotions_for_server(emotions_detected_list)
                print(f"Processed emotions: {processed_emotions}")

                date = get_date()
                doc_id = customer_id + "_emotionData"

                doc_ref = db.collection("customer-satisfaction-data").document(store_id)

                dummy_data = {"initialized": True}
                doc_ref.set(dummy_data)

                datewise_doc_ref = doc_ref.collection("emotion_db").document(doc_id).collection("datewise").document(date)
                datewise_doc = datewise_doc_ref.get()

                updated_emotion_data = []
                cashier_data_array = []

                if datewise_doc.exists:
                    existing_data = datewise_doc.to_dict()
                    updated_emotion_data = existing_data.get('emotion-data', [])

                    # Get existing cashier data or initialize as empty
                    cashier_data_array = existing_data.get('cashier-id', [])
                    if not isinstance(cashier_data_array, list):
                        cashier_data_array = []

                # Append the new cashier ID and timestamp
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cashier_data_array.append({"cashier_id": employee_id, "timestamp": timestamp})

                # Merge new emotion data
                updated_emotion_data.extend(processed_emotions)

                data1 = {"customer-id": customer_id, "customer-name": customer_name, "customer-gender": customer_gender}
                data2 = {'cashier-id': cashier_data_array, 'emotion-data': updated_emotion_data}

                db.collection("customer-satisfaction-data").document(store_id).collection("emotion_db").document(doc_id).set(data1, merge=True)
                db.collection("customer-satisfaction-data").document(store_id).collection("emotion_db").document(doc_id).collection("datewise").document(date).set(data2)

                print("Posted data successfully into Firestore")
                tk.messagebox.showinfo("Success", "Saved Data into Db successfully!")
            except Exception as e:
                tk.messagebox.showerror("Error", "An error occurred while posting data to Firestore, please make sure the system is connected to Internet Connection")
                print("An error occurred while posting to Firestore - ", e)

    emotions_detected_list = []


def update_datetime():
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    datetime_label.config(text=date_str)
    datetime_label.after(1000, update_datetime)

def get_date(): 
    now = datetime.datetime.now()
    datetime_str = now.strftime("%Y-%m-%d %H:%M:%S")
    return datetime_str[0:10]

def show_main_window():
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

    available_cameras = get_available_cameras()
    camera_var_label = tk.Label(
        left_container, text="Camera Select:", font=("Helvetica", 14))
    camera_var_label.grid(row=5, column=0, sticky='w', padx=15, pady=10)
    camera_var = tk.StringVar(value=str(available_cameras[0]) if available_cameras else "No camera available")
    camera_option_menu = tk.OptionMenu(left_container, camera_var, *available_cameras)
    camera_option_menu.grid(row=5, column=1, columnspan=2, padx=10, pady=5, sticky='w')

    window.mainloop()

def prompt_access_key():
    login_window = tk.Tk()
    login_window.title("Access Key Required")
    login_window.geometry("500x350")
    def check_access_key():
        global store_id
        access_key = access_key_entry.get()
        store_id = store_id_entry.get()
        if access_key == "cs351":  
            login_window.destroy()
            show_main_window()
        else:
            messagebox.showerror("Invalid Access Key", "The access key you entered is invalid. Please try again.")
            access_key_entry.delete(0, tk.END)

    tk.Label(login_window, text="Enter Store ID:", font=("Helvetica", 14)).pack(pady=10)
    store_id_entry = tk.Entry(login_window, font=("Helvetica", 14))
    store_id_entry.pack(pady=5)
    tk.Label(login_window, text="Enter Access Key:", font=("Helvetica", 14)).pack(pady=10)
    access_key_entry = tk.Entry(login_window, show="*", font=("Helvetica", 14))
    access_key_entry.pack(pady=5)
    tk.Button(login_window, text="Submit", font=("Helvetica", 14), command=check_access_key).pack(pady=10)

    login_window.mainloop()

if __name__ == "__main__":
    prompt_access_key()
