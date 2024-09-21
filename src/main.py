import cv2
import mediapipe as mp

mp_pose = mp.solutions.pose
pose = mp_pose.Pose(min_detection_confidence=0.2, min_tracking_confidence=0.2)
mp_drawing = mp.solutions.drawing_utils

file_name = input("File Name: ")
cap = cv2.VideoCapture(f'data/{file_name}.mp4')

if not cap.isOpened():
    print("Error: Could not open video.")
    exit()

def round(frame):
    return

while cap.isOpened():
    ret, frame = cap.read()
    
    # If the frame was read successfully
    if not ret:
        break

    # Detect text in the bottom half of the frame
    detected_text = detect_text(frame)
    detected_text = detected_text.strip()  # Clean up the text output
    

    if round():
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb_frame)
        if results.pose_landmarks:
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
    
    # Display the output frame
    cv2.imshow('Pose Detection', frame)
    
    # Press 'q' to exit
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

# Release video capture object and close OpenCV windows
cap.release()
cv2.destroyAllWindows()
