from time import sleep
# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
import pyaudio
import wave
from threading import Thread
import time
from datetime import datetime
import cv2

# pip install opencv-python pyTelegramBotAPI
# https://stackoverflow.com/questions/14140495/how-to-capture-a-video-and-audio-in-python-from-a-camera-or-webcam


class recordAudio:

    def __init__(self) -> None:
        self.running = False

        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 2
        self.fs = 44100  # Record at 44100 samples per second

        self.p = pyaudio.PyAudio()  # Create an interface to PortAudio

        # Store data in chunks for 3 seconds
        # for i in range(0, int(self.fs / self.chunk * self.seconds)):
        self.chunkInEachSec = int(self.fs / self.chunk)

        self.stream = self.p.open(format=self.sample_format,
                                  channels=self.channels,
                                  rate=self.fs,
                                  frames_per_buffer=self.chunk,
                                  input=True)

    def startAudio(self):

        self.frames = []  # Initialize array to store frames
        self.running = True
        self.stream.start_stream()
        # try:
        count = 0
        while self.running:
            count += 1
            # if self.stream.is_stopped():
            #     print('stopped')
            #     break
            data = self.stream.read(self.chunk)
            self.frames.append(data)
            # if count%self.chunkInEachSec==0: # print every second
            #     print(count,'recording')
        # except Exception as e:
        #     print("exception occured", e)

    def stopRecording(self, filename, dontSave=False):

        self.running = False
        # Stop and close the self.stream
        self.stream.stop_stream()
        self.stream.close()
        # Terminate the PortAudio interface
        self.p.terminate()
        if dontSave:
            return
        # print('Finished recording')
        # Save the recorded data as a WAV file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.p.get_sample_size(self.sample_format))
        wf.setframerate(self.fs)
        wf.writeframes(b''.join(self.frames))
        wf.close()

    def start(self):
        self.t = Thread(target=self.startAudio)
        self.t.start()

    def stop(self, file, dontSave=False):
        self.stopRecording(file, dontSave)
        self.t.join()


class VideoRecorder():

    # Video class based on openCV
    def __init__(self):
        self.running = False
        self.device_index = 0
        self.fps = 15  # fps should be the minimum constant rate at which the camera can
        self.fourcc = "MJPG"  # capture images (with no decrease in speed over time; testing is required)
        # self.fourcc = "XVID"       # capture images (with no decrease in speed over time; testing is required)
        self.frameSize = (
            640, 480
        )  # video formats and sizes also depend and vary according to the camera used
        # self.video_filename = "temp_video.avi"
        # print(self.video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.video_writer = cv2.VideoWriter_fourcc(*self.fourcc)

        self.frame_counts = 1
        self.start_time = time.time()
        # print(self.video_cap.get(cv2.CAP_PROP_FPS))

    # Video starts being recorded
    def record(self, fileName):
        self.video_cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        self.video_out = cv2.VideoWriter(fileName,
                                         self.video_writer, self.fps,
                                         self.frameSize)
        #counter = 1
        # timer_start = time.time()
        # timer_current = 0
        self.running = True
        while self.running:
            ret, video_frame = self.video_cap.read()
            if ret == True:

                self.video_out.write(video_frame)
                #print str(counter) + " " + str(self.frame_counts) + " frames written " + str(timer_current)
                # self.frame_counts += 1
                #counter += 1
                #timer_current = time.time() - timer_start
                # time.sleep(0.16)

                # Uncomment the following three lines to make the video to be
                # displayed to screen while recording

                # gray = cv2.cvtColor(video_frame, cv2.COLOR_BGR2GRAY)
                # cv2.imshow('video_frame', gray)
                # cv2.waitKey(1)

    def stop(self):

        if self.running:
            self.running = False
            self.video_out.release()
            self.video_cap.release()
            cv2.destroyAllWindows()
            return self.fileName


    # Launches the video recording function using a thread
    def start(self, fileName):
        self.fileName = fileName
        video_thread = Thread(target=self.record, args=(fileName,))
        video_thread.start()


def timeStamp():
    return datetime.now().strftime('%d%m%Y_%H%M%S')


def takeScreenShot(fileName):
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # 0 -> index of camera

    # The resolution of the camera
    # width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    # height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    # print(width, height)

    # set resolution of the photo taken
    # cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    s, img = cam.read()
    if s:  # frame captured without any errors
        cv2.imwrite(fileName, img)  #save image
    cv2.destroyAllWindows()
    return fileName



if __name__ == '__main__':


    # # import os
    # # # os.remove('./output_new.wav')
    # # r = recordAudio()
    r = VideoRecorder()
    file = f"Video_{timeStamp()}.avi"
    r.start(file)

    sleep(10)
    r.stop()
