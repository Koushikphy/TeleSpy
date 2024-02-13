import os
import subprocess, random, string
from time import time, sleep
from glob import glob
from threading import Timer
from datetime import datetime


ASSETS_DIR = 'assets'
TMP_DIR = f"{ASSETS_DIR}/tmp"
LOG_FILE = open('ffm.log','a')
LOG_FILE2 = open('ffm2.log','a')


class RepeatTimer(Timer):
    def run(self):
        while not self.finished.wait(self.interval):
            self.function(*self.args, **self.kwargs)



#def takeScreenShot(other=None):
#    if other:
#        print(other)
#        # rr = subprocess.run(['bash', 'capture.sh', other])
#        rr = subprocess.run(f'bash capture.sh {other}', shell=True)
#        fl = 'screen_shot.png'
#    else:
#        fl = getFileName('screenshot', 'jpg')
#        rr = subprocess.run(f"DISPLAY=:1 scrot -z {fl}",shell=True)
#    if rr.returncode==0:
#        return fl

def takeScreenShot(other=None):
    rr = subprocess.run(f'bash capture.sh {other}', shell=True)
    fl = 'screen_shot.png'
    if rr.returncode==0:
        return fl

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
        #self.commonFlags = 'ffmpeg -hide_banner -f dshow -y -video_size 1280x720 -rtbufsize 2G'.split()
        #self.commonFlags = 'ffmpeg -hide_banner -y -video_size 1280x720 -rtbufsize 2G'.split()
        self.commonFlags = 'ffmpeg -hide_banner -y -rtbufsize 2G'.split()
        self.vidFlags    = "-pix_fmt yuv420p -profile:v baseline -vcodec libx264 -crf 28 ".split()
        # get list of devices with `ffmpeg -list_devices true -f dshow -i dummy`
        # self.audioInput  = "audio=Headset (realme Buds Wireless 2 Neo Hands-Free AG Audio)"
        # self.videoInput  = "video=HP HD Camera"
        self.videoInput  = "-f video4linux2 -vcodec mjpeg -video_size 1280x720 -i /dev/video0".split()
        self.fragFlags = '-g 64 -movflags frag_keyframe+empty_moov'.split()  
        #^ fragmented video, so that ffmpeg can extract frame while the recording in progress keyframes after every 64 frames
        self.audioInput  = "-f alsa -ac 1 -i hw:1 -filter:a volume=1.5".split()
        self.isRunning   = False


    def startVideoRec(self):
        self.fileName = getFileName('Video', 'mp4')
        self.startTime = time()
        #return self.runCommand([*self.commonFlags, '-i', f"{self.videoInput}:{self.audioInput}", *self.vidFlags, self.fileName])
        return self.runCommand([*self.commonFlags, *self.videoInput, *self.audioInput,*self.fragFlags ,*self.vidFlags, self.fileName])



    def startAudeoRec(self):
        self.fileName = getFileName('Audio', 'm4a')
        self.startTime = time()
        return self.runCommand([*self.commonFlags, *self.audioInput, self.fileName])



    def takePhoto(self):
        fileName = getFileName('Photo', 'jpeg')
        
        if self.isRunning and self.fileName.endswith('mp4'):  # video recording running get the last frame from the video
            command = [*self.commonFlags, '-sseof', '-3', '-i', self.fileName, '-update', '1', '-q:v', '1', fileName] # only if this filename is video
        else: # take picture from webcam
            command = [*self.commonFlags, *self.videoInput, '-frames:v', '10','-update', '1', fileName]

        recorder = subprocess.Popen(
                command,
                shell=False, 
                stdin=subprocess.PIPE,
                stdout=LOG_FILE2,
                stderr=LOG_FILE2,
            )
        sleep(1)
        # wait and check if the command fails
        # it should return None if it working
        recorder.poll()
        recorder.communicate()
        recorder.terminate()
        recorder.kill()

        if not recorder.returncode:
            return fileName
        



    def runCommand(self, command):
        if self.isRunning : return
        # print(command)
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
        #print(ifFailed)
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


    # check list of keyframes 
    # ffprobe -loglevel error -skip_frame nokey -select_streams v:0 -show_entries frame=pkt_pts_time -of csv=print_section=0 test.mp4



if __name__ =="__main__":
    recorder = AVRecorder()
    recorder.takePhoto()
