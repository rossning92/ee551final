"""
In this implementation, we use https://github.com/ageitgey/face_recognition as
our shuttle controller. face_recognition is built on top of dlib's state-of-
the-art face recognition. The deep learning model has an accuracy of 99.38% on
the Labeled Faces in the Wild benchmark.
"""

import face_recognition
import cv2


cameraFrameArray = None
facePos = (0.5, 0.5)


def run():

    video_capture = cv2.VideoCapture(0)

    while True:
        # Grab a single frame of video
        ret, frame = video_capture.read()
        frame = cv2.flip(frame, 1)

        # Resize frame of video to 1/4 size for faster face recognition processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

        # Only process every other frame of video to save time

        # Find all the faces and face encodings in the current frame of video
        face_locations = face_recognition.face_locations(small_frame, model='hog')
        # face_encodings = face_recognition.face_encodings(small_frame, face_locations)
        #
        face_names = ['FACE'] * len(face_locations)

        # Display the results
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            # Scale back up face locations since the frame we detected in was scaled to 1/4 size
            top *= 4
            right *= 4
            bottom *= 4
            left *= 4

            # Draw a box around the face
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            # Draw a label with a name below the face
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), (0, 0, 255), cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 1.0, (255, 255, 255), 1)

            x = (left + right) * 0.5 / frame.shape[1]
            y = (top + bottom) * 0.5 / frame.shape[0]
            global facePos
            facePos = (x, y)

        # Display the resulting image
        cv2.imshow('Video', frame)
        global cameraFrameArray
        cameraFrameArray = frame

        # Hit 'q' on the keyboard to quit!
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release handle to the webcam
    video_capture.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    run()
