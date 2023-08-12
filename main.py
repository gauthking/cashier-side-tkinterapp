import tkinter as tkn
import cv2
from PIL import Image, ImageTk
import datetime
import os

# Video codec and recording filename
video_codec = cv2.VideoWriter_fourcc(*"XVID")
filename = "recs/camera_feed_recording.mp4"

# Create the "recs" folder if it doesn't exist
if not os.path.exists("recs"):
    os.mkdir("recs")

# Initialize the capture variable as None
cap = None
out = None
recording = False


def set_filename(name):
    global filename
    filename = "recs/camera_feed_"+name+".mp4"


def update_cam_view():
    global cap, out, recording
    if cap is not None:
        ret, frame = cap.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            camera.imgtk = imgtk
            camera.config(image=imgtk)
            if recording and out is not None:
                # Write frame to the video file
                out.write(frame)
        # Continue updating the camera feed even if not recording
        camera.after(10, update_cam_view)
    else:
        camera.after(10, update_cam_view)


def start_camera():
    global cap
    # Release any existing capture
    if cap is not None:
        cap.release()
    # Initialize the capture
    cap = cv2.VideoCapture(0)
    update_cam_view()


def start_recording():
    global cap, out, recording
    if cap is not None:
        recording = True
        width = int(cap.get(3))
        height = int(cap.get(4))
        set_filename(customer_name_input.get())
        out = cv2.VideoWriter(filename, video_codec, 20, (width, height))
        print("Recording started:", filename)


def stop_camera():
    global cap, out, recording
    if cap is not None:
        # Stop recording before stopping the camera
        if out is not None:
            out.release()
            out = None
            print("Recording saved:", filename)
            print("Saving file...")
            # Add a delay to allow the camera to release
            camera.after(100, save_cam_feed)


def save_cam_feed():
    global cap
    if cap is not None:
        # Release the camera
        # cap.release()
        # cap = None
        # Clear the camera feed
        camera.config(image='')
        print("Camera feed stopped")


def update_datetime():
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d %H:%M:%S")
    datetime_label.config(text=date_str)
    datetime_label.after(1000, update_datetime)


def main():
    global camera, cap, datetime_label, customer_name_input
    window = tkn.Tk()
    window.geometry("1200x900")
    window.title("Cashier Side Application")
    window.configure(bg="black")

    heading_label = tkn.Label(
        window, text="Cashier Desk Portal - Emotion Detection", font=("Helvetica", 28, "bold"))
    heading_label.grid(row=0, column=0, padx=10, pady=10, columnspan=2)

    # Create a container frame to hold the left and right containers
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
        "Helvetica", 14), command=start_recording)
    start_button.grid(row=4, column=0, padx=10, pady=5, sticky='w')

    stop_button = tkn.Button(left_container, text="Stop Feed", font=(
        "Helvetica", 14), command=stop_camera)
    stop_button.grid(row=4, column=1, padx=10, pady=5, sticky='w')

    datetime_label = tkn.Label(outer_container, font=("Helvetica", 14))
    datetime_label.grid(row=0, column=1, padx=10, pady=10, sticky="ne")
    update_datetime()

    # Start the GUI app
    start_camera()

    window.mainloop()


if __name__ == "__main__":
    main()
