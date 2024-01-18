from flask import Flask, render_template, Response
import cv2,os

app = Flask(__name__)

# os.system("v4l2-ctl --set-fmt-video=width=1920,height=1080,pixelformat=1") 
# os.system("v4l2-ctl --set-parm=30")


def gen_frames(camera_id):
     
    # cam = find_camera(camera_id)
    #cap=  cv2.VideoCapture(0)
    



    cap = cv2.VideoCapture(0)#, cv2.CAP_DSHOW) # this is the magic!

    cap.set(3, 1920)
    cap.set(4, 1080)


    while True:
        # for cap in caps:
        # # Capture frame-by-frame
        success, frame = cap.read()  # read the camera frame
        if not success:
            break
        else:
            #frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')  # concat frame one by one and show result


@app.route('/video_feed/<string:id>/', methods=["GET"])
def video_feed(id):
   
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(gen_frames(id),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/', methods=["GET"])
def index():
    print('here')
    return render_template('index.html')



def runTheApp():
    app.run(host='0.0.0.0', port=5555)





if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5555)
    #from multiprocessing import Process

    #server = Process(target=runTheApp)
    #server.start()

    #print('here----------------------')
    #from time import sleep
    #sleep(10)
    #server.terminate()

