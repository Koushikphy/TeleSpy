# https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
import chunk
import os
import cv2
import wave
import pyaudio
import subprocess
from time import sleep, time
from datetime import datetime
from threading import Thread, Timer
# import moviepy.editor as mpe

ASSETS_DIR = 'assets'

# https://stackoverflow.com/questions/14140495/how-to-capture-a-video-and-audio-in-python-from-a-camera-or-webcam

class RepeatTimer(Timer):

    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)


def getFileName(name: str, ext: str) -> str:
    now = datetime.now()
    fileName = f"{name}_{now.strftime('%H_%M_%S')}.{ext}"
    dirPath = os.path.join(ASSETS_DIR, f"{now.strftime('%d_%m_%Y')}")
    os.makedirs(dirPath, exist_ok=True)
    return os.path.join(dirPath, fileName)


def getEnv(var, cast=None, isList=False):
    value = os.getenv(var)
    # print(var,value)
    if isList:
        value = [cast(i) if cast else i for i in value.split()]
    if cast and not isList:
        value = cast(value)
    return value


def removeFile(*fileList):
    # return
    for file in fileList:
        if (os.path.exists(file)):
            os.remove(file)


def takeScreenShot():
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # 0 -> index of camera

    # The resolution of the camera
    # width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    # height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    # print(width, height)

    # set resolution of the photo taken
    # cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    file = getFileName('Photo', 'jpg')
    s, img = cam.read()
    if s:  # frame captured without any errors
        cv2.imwrite(file, img)  #save image
    cv2.destroyAllWindows()
    return file


class AudioRecorder:

    def __init__(self) -> None:
        self._running = False
        self.chunk = 1024  # Record in chunks of 1024 samples
        self.sample_format = pyaudio.paInt16  # 16 bits per sample
        self.channels = 1  # channels for input
        self.fs = 44100  # Record at 44100 samples per second
        self.port = pyaudio.PyAudio()  # Create an interface to PortAudio

    def startAudio(self):
        self._running = True
        self.frames = []  # Initialize array to store frames
        self.stream = self.port.open(format=self.sample_format,
                                     channels=self.channels,
                                     rate=self.fs,
                                     frames_per_buffer=self.chunk,
                                     input=True)
        self.stream.start_stream()
        while self.stream.is_active():
            self.frames.append(self.stream.read(self.chunk))

    def isRunning(self):
        return self._running
        # try:
        #     return self.stream.is_active()
        # except:
        #     return False

    def start(self):
        self.th = Thread(target=self.startAudio)
        self.th.start()

    def closeCapture(self):
        self._running = False
        self.stream.stop_stream()
        self.stream.close()
        self.th.join()

    def terminate(self):
        if self.isRunning():
            self.closeCapture()

    def finish(self,toM4A=False):
        if self.isRunning():
            self.closeCapture()
            file = getFileName('Audio', 'wav')
            wf = wave.open(file, 'wb')
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.port.get_sample_size(self.sample_format))
            wf.setframerate(self.fs)
            wf.writeframes(b''.join(self.frames))
            duration = wf.getnframes()/wf.getframerate() # -or- len(self.frames)*self.chunk/self.fs
            wf.close()
            if toM4A:
                tFile = file
                file = getFileName("Audio",'m4a')
                wavTo_m4a(tFile,file)
            return file, duration


class VideoRecorder():

    # NOTE: openCV doesn't capture/write video stream in a constant fps, its increases/decreases depending on
    # several parameter, but the videowriter doesn't get the information from the capturer and saves the file in
    # a constant fps stream, this makes the video slower/faster than the actual real time stream.
    # There are several non-cv method to fix this. Here the video stream is written in the actual fps provided by the webcam
    #  and the actual real world clock time is measured for the whole duration, which gives us the effective fps for the stream
    # then the fps of the video is fixed using `ffmpeg`

    def __init__(self, fps=15):
        self._running = False
        self.device_index = 0
        self.fps = fps
        self.fourcc = "XVID" #"MJPG"
        self.frames = self.getWidthHeight()
        self.video_writer = cv2.VideoWriter_fourcc(*self.fourcc)
        self.frame_counts = 1

    def isRunning(self):
        return self._running
        # try:
        #     return self.video_out.isOpened()
        # except:  # if not video writer is not opened
        #     return False

    def record(self):
        self._running = True
        self.tempFile = getFileName('Temp','avi') # opencv in this fourcc only records in avi
        self.video_out = cv2.VideoWriter(self.tempFile, self.video_writer, self.fps, self.frames)
        self.video_cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)

        self.starttime = time()
        self.framescount = 0

        while self.video_cap.isOpened():

            ret, video_frame = self.video_cap.read()
            if ret and self.video_out.isOpened():
                self.video_out.write(video_frame)
                self.framescount += 1
                # show the video in a window
                # cv2.imshow('video_frame', gray)
                # cv2.waitKey(1)

    def getWidthHeight(self):
        # get height and width of the camera
        cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        cv2.destroyAllWindows()
        return width, height

    def start(self):
        # start the video recording in a new thread
        self.th = Thread(target=self.record)
        self.th.start()

    def closeCapture(self):
        self._running = False
        totalTime = time() - self.starttime
        self.video_cap.release()
        self.video_out.release()
        cv2.destroyAllWindows()
        self.th.join()
        return totalTime

    def terminate(self):
        if self.isRunning():
            self.closeCapture()

    def finish(self):
        # fixes the fps and returns a mp4 file
        if self.isRunning():
            fileName = getFileName('Video', 'mp4')
            totalTime = self.closeCapture()
            thisFPS = self.framescount / totalTime
            acT = self.fps*totalTime/thisFPS # actual time of the video after the rescaling FPS
            reFFMPEG(self.tempFile, thisFPS, fileName, self.fps)
            return fileName, acT

    def finishWithAudio(self, audioStream):
        # fixes the fps, mux the audiostream and return an mp4
        if self.isRunning():
            fileName = getFileName('Video', 'mp4')
            totalTime = self.closeCapture()
            thisFPS = self.framescount / totalTime
            acT = self.fps*totalTime/thisFPS # actual time of the video after the rescaling FPS
            reMergeFFMPEG(self.tempFile, audioStream, thisFPS, self.fps, fileName)
            return fileName, acT




def reFFMPEG(iFile, iFPS, oFile, oFPS):
    # change fps of the video file, writes output to `ffmpeg.log`
    ret = subprocess.call(f"ffmpeg -y -r {iFPS} -i {iFile} -r {oFPS} {oFile} >> ffmpeg.log 2>&1", shell=True)
    if ret==0:
        os.remove(iFile) # remove the temporary file


def mergeFFMPEG(videoStream, audioStream, videoOut, crf=24):
    # merge audio and video stream, writes output to `ffmpeg.log`
    ret = subprocess.call( f"ffmpeg -ac 2 -y -channel_layout stereo -i {videoStream} -i {audioStream} \
                -vcodec libx265 -crf {crf} {videoOut} >> ffmpeg.log 2>&1",
        shell=True)
    if ret==0:
        os.remove(videoStream)
        os.remove(audioStream)


def wavTo_m4a(inFile,outFile):
    ret= subprocess.call(f"ffmpeg -i {inFile} {outFile} >> ffmpeg.log 2>&1", shell=True)
    if ret==0:
        removeFile(inFile)


def reMergeFFMPEG(videoStream, audioStream,iFPS,oFPS, videoOut,crf=24):
    ret = subprocess.call(
        f"ffmpeg -ac 2 -y -channel_layout stereo -r {iFPS} -i {videoStream} -r {oFPS} -i {audioStream} -vcodec libx265 -crf {crf} {videoOut} >> ffmpeg.log 2>&1",
        shell=True)
    if ret==0:
        removeFile(videoStream, audioStream)




def markedFileName(fName,mark):
    pth,fNme = os.path.split(fName)
    b,e = os.path.splitext(fNme)
    return os.path.join(pth,b+f'_{mark}'+e)


def splitFilesInChunks(inFile, actTime, chunks=300):
    # split in chunks of 5 minutes
    fileSize = os.path.getsize(inFile)/1e6  # filesiz in mb
    if actTime<=chunks:
        print(f'Nothing to split, file is already small. Filesize: {fileSize} MB')
        return [inFile]
    files = []
    nChnks = int(actTime/chunks)
    for i in range(nChnks+1):
        sTime, eTime = i*chunks, (i+1)*chunks
        if eTime> actTime : 
            eTime = actTime
        fName = markedFileName(inFile,i+1)
        subprocess.call(
            f"ffmpeg -i {inFile} -ss {sTime} -to {eTime} {fName} >> ffmpeg.log 2>&1",
        shell=True)
        files.append(fName)
    return files







# def mergeMoviePy(videoStream, audioStream, videoOut, fps=15):
#     my_clip = mpe.VideoFileClip(videoStream)
#     audio_background = mpe.AudioFileClip(audioStream)
#     final_clip = my_clip.set_audio(audio_background)
#     final_clip.write_videofile(videoOut,fps)




if __name__ == '__main__':
    # # # os.remove('./output_new.wav')
    ra = AudioRecorder()
    rv = VideoRecorder()

    ra.start()
    rv.start()

    sleep(600)

    s = time()
    audFile, _ = ra.finish()
    vidFile, _ = rv.finish()


    file = wavTo_m4a(audFile)
    print(f"Time took: {time()-s}")


    file = getFileName('Video', 'mp4')
    mergeFFMPEG(vidFile, audFile, file)


    print(f"Time took: {time()-s}")



    # print(audFile, vidFile, file)


#NOTES:
# 1. re FPS and merging does not work properly in a single command so opt for dual step
# 2. with 265 crf 381/555 and without 787/1010

# TODO
# 1. Video recorder finishWithAudio and normal finish
# 2. all send try split block can be summed up in one function