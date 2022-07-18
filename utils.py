import os
import subprocess
from time import sleep, time
from datetime import datetime
from threading import Thread, Timer
from glob import glob

ASSETS_DIR = 'assets'
TMP_DIR = f"{ASSETS_DIR}/tmp"
LOG_FILE = open('ffm.log','a')


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



def splitFilesInChunks(inFile, chunks=10):
    # split in chunks of 10 minutes
    # if os.path.getsize(inFile)/1e6 <= 48.0: # telegram file size limit 50MB
    #     return [inFile]

    if os.path.exists(TMP_DIR):
        for f in glob(f'{TMP_DIR}/*'): os.remove(f)
    else:
        os.makedirs(TMP_DIR)


    subprocess.call(
        ['ffmpeg', '-y','-i', inFile, '-f', 'segment', '-segment_time', f'{chunks}', 
        '-c', 'copy', '-reset_timestamps', 'true', f'{TMP_DIR}/out%03d.mp4'],
        shell=False,
        stdin=subprocess.PIPE,
        stdout=LOG_FILE,
        stderr=LOG_FILE
    )
    return glob(f'{TMP_DIR}/*')




class AVRecorder:

    def __init__(self):
        self.commonFlags = 'ffmpeg -hide_banner -f dshow -y -video_size 1280x720 -rtbufsize 2G'.split()
        self.vidFlags    = "-vcodec libx265 -crf 28 -r 21".split()
        self.audioInput  = "audio=Headset (realme Buds Wireless 2 Neo Hands-Free AG Audio)"
        self.videoInput  = "video=HP HD Camera"
        # self.videoInput  = "video=GENERAL WEBCAM"
        # self.audioInput  = "audio=Microphone (GENERAL WEBCAM)"
        self.isRunning   = False


    def startVideoRec(self):
        self.fileName = getFileName('Video', 'mp4')
        self.startTime = time()
        self.runCommand([*self.commonFlags, '-i', f"{self.videoInput}:{self.audioInput}", *self.vidFlags, self.fileName])


    def startAudeoRec(self):
        self.fileName = getFileName('Audio', 'm4a')
        self.startTime = time()
        self.runCommand([*self.commonFlags, '-i', self.audioInput, self.fileName])


    def takePicture(self):
        fileName = getFileName('Photo', 'jpg')
        self.runCommand([*self.commonFlags, '-i', self.videoInput, '-frames:v', '1', fileName])
        self.release()
        return fileName


    def runCommand(self, command):
        if self.isRunning : return
        self.isRunning = True
        self.recorder = subprocess.Popen(
                command,
                shell=False, 
                stdin=subprocess.PIPE,
                stdout=LOG_FILE,
                stderr=LOG_FILE,
            )

    def close(self):
        self.recorder.stdin.write('q'.encode("GBK")) 
        self.release()
        duration = time() - self.startTime
        return self.fileName, duration


    def release(self):
        self.recorder.communicate()
        self.recorder.wait()
        self.isRunning = False
        self.recorder.terminate()
        self.recorder.kill()
