# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
import pyaudio
import wave
from threading import Thread
import time
from datetime import datetime
import cv2
import os
# pip install opencv-python pyTelegramBotAPI
# https://stackoverflow.com/questions/14140495/how-to-capture-a-video-and-audio-in-python-from-a-camera-or-webcam


class AudioRecorder:

    def __init__(self) -> None:
        self.running = False

        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 1
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

    def start(self):
        self.t = Thread(target=self.startAudio)
        self.t.start()

    def stop(self, file=None):
        if not self.running : return
        self.running = False
        # Stop and close the self.stream
        self.stream.stop_stream()
        self.stream.close()
        # Terminate the PortAudio interface
        self.p.terminate()
        if file: # if file not present then it won't be saved
            # print('Finished recording')
            # Save the recorded data as a WAV file
            wf = wave.open(file, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.p.get_sample_size(self.sample_format))
            wf.setframerate(self.fs)
            wf.writeframes(b''.join(self.frames))
            wf.close()
        self.t.join()


class VideoRecorder():

    # Video class based on openCV
    def __init__(self):
        self.running = False
        self.device_index = 0
        self.fps = 15  # fps should be the minimum constant rate at which the camera can
        # self.fourcc = "MJPG"  # capture images (with no decrease in speed over time; testing is required)
        self.fourcc = "XVID"  # capture images (with no decrease in speed over time; testing is required)
        self.frames = self.getWidthHeight()
        self.tempFile = 'temp.avi'
        # print(self.getWidthHeight())

        self.video_writer = cv2.VideoWriter_fourcc(*self.fourcc)

        self.frame_counts = 1
        self.start_time = time.time()

    # Video starts being recorded
    def record(self):
        from time import perf_counter_ns, perf_counter
        self.video_cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)

        self.video_out = cv2.VideoWriter(self.tempFile, self.video_writer, self.fps, self.frames)

        self.running = True
        oldTime = perf_counter()
        self.framescount = 0
        self.starttime = oldTime
        while self.running:
            # opencv doesn't record video in a constant self.framescount per second, so wait for the time to pass before capturing
            # to make a constant video renderer
            if (perf_counter() - oldTime) * self.fps > 1:
                ret, video_frame = self.video_cap.read()
                if ret:
                    self.video_out.write(video_frame)
                    self.framescount +=1
                oldTime = perf_counter()
                # gray = cv2.cvtColor(video_frame, cv2.COLOR_BGR2GRAY)
                # cv2.imshow('video_frame', gray)
                # cv2.waitKey(1)

    def checkFPS(self):
        from time import perf_counter
        cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        start = perf_counter()
        for _ in range(100):
            ret, video_frame = cap.read()
            end = perf_counter()
            print(1 / (end - start))
            start = end

    def getWidthHeight(self):
        cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        cv2.destroyAllWindows()
        return width, height

    def stop(self,file=None):
        if not self.running: return
        from time import perf_counter_ns, perf_counter

        tt = perf_counter() - self.starttime
        self.running = False
        self.video_out.release()
        self.video_cap.release()
        cv2.destroyAllWindows()
        self.th.join()
        if file:
            os.replace(self.tempFile, file)
        return self.framescount/tt
                

    # Launches the video recording function using a thread
    def start(self):
        self.th = Thread(target=self.record)
        self.th.start()


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
    from time import sleep
    # # import os
    # # # os.remove('./output_new.wav')
    ra = AudioRecorder()
    rv = VideoRecorder()
    # r.getWidthHeight()
    # r.checkFPS()
    filev = f"Video_{timeStamp()}.avi"
    filea = f"Audio_{timeStamp()}.wav"
    ra.start()
    from time import perf_counter
    st = perf_counter()
    rv.start()
    sleep(5)
    ra.stop(filea)
    ff = rv.stop(filev)
    end = perf_counter()

    
    

    import subprocess
    subprocess.call(f"ffmpeg -r {ff} -i {filev} -pix_fmt yuv420p -r {rv.fps} out.mp4", shell=True)
    # os.remove('out.mp4')
    subprocess.call(f"ffmpeg -ac 2 -channel_layout stereo -i out.mp4 -i {filea} outfinal.mp4", shell=True)

    import moviepy.editor as mpe

    my_clip = mpe.VideoFileClip(filev)
    audio_background = mpe.AudioFileClip(filea)
    final_clip = my_clip.set_audio(audio_background)
    final_clip.write_videofile('test.mp4',fps=15)
