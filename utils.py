import os
import subprocess, random, string
from time import time, sleep
from glob import glob
from threading import Timer
from datetime import datetime


ASSETS_DIR = 'assets'
TMP_DIR = f"{ASSETS_DIR}/tmp"
LOG_FILE = open('ffm.log','a')


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)




def getRandomString():
    return ''.join(random.choice(string.ascii_letters) for _ in range(10))


def getFileName(name: str, ext: str) -> str:
    now = datetime.now()
    fileName = f"{name}_{now.strftime('%d%m%y_%H%M%S')}.{ext}"
    dirPath = os.path.join(ASSETS_DIR, f"{now.strftime('%d_%m_%Y')}")
    os.makedirs(dirPath, exist_ok=True)
    return os.path.join(dirPath, fileName)



def splitFilesInChunks(inFile, chunks=300):
    # split in chunks of 5 minutes

    if os.path.exists(TMP_DIR):
        for f in glob(f'{TMP_DIR}/*'): os.remove(f)
    else:
        os.makedirs(TMP_DIR)

    _, extn = os.path.splitext(inFile)

    subprocess.call(
        ['ffmpeg', '-y','-i', inFile, '-f', 'segment', '-segment_time', f'{chunks}', 
        '-c', 'copy', '-reset_timestamps', 'true', f'{TMP_DIR}/out%03d.{extn}'],
        shell=False,
        stdin=subprocess.PIPE,
        stdout=LOG_FILE,
        stderr=LOG_FILE
    )
    return glob(f'{TMP_DIR}/*')




class AVRecorder:

    def __init__(self):
        self.commonFlags = 'ffmpeg -hide_banner -f dshow -y -video_size 1280x720 -rtbufsize 2G'.split()
        self.vidFlags    = "-vcodec libx265 -crf 28 -r 17".split()
        # get list of devices with `ffmpeg -list_devices true -f dshow -i dummy`
        # self.audioInput  = "audio=Headset (realme Buds Wireless 2 Neo Hands-Free AG Audio)"
        # self.videoInput  = "video=HP HD Camera"
        self.videoInput  = "video=GENERAL WEBCAM"
        self.audioInput  = "audio=Microphone (GENERAL WEBCAM)"
        self.isRunning   = False


    def startVideoRec(self):
        self.fileName = getFileName('Video', 'mp4')
        self.startTime = time()
        return self.runCommand([*self.commonFlags, '-i', f"{self.videoInput}:{self.audioInput}", *self.vidFlags, self.fileName])


    def startAudeoRec(self):
        self.fileName = getFileName('Audio', 'm4a')
        self.startTime = time()
        return self.runCommand([*self.commonFlags, '-i', self.audioInput, self.fileName])


    def takePicture(self):
        # take 5 photo to focus the camera and use the last photo
        self.runCommand([*self.commonFlags, '-i', self.videoInput, '-frames:v', '5', f'{TMP_DIR}/pic%03d.jpg'])
        ret = self.release()
        if ret:
            self.isRunning = False
            return None
        fileName = getFileName('Photo', 'jpg')
        os.rename(f'{TMP_DIR}/pic005.jpg',fileName)
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
        sleep(1)
        # wait and check if the command fails
        # it should return None if it working
        ifFailed = self.recorder.poll()
        if ifFailed: self.isRunning = False
        return ifFailed


    def close(self):
        self.recorder.stdin.write('q'.encode("GBK")) 
        self.release()
        duration = time() - self.startTime
        return self.fileName, duration


    def release(self):
        self.recorder.communicate()
        # self.recorder.wait()   # communicate explicitly calls the wait
        self.isRunning = False
        self.recorder.terminate()
        self.recorder.kill()
        return self.recorder.returncode
