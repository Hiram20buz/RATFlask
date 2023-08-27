#from flask import Flask,render_template,Response
from flask import Flask, request,render_template,Response


import cv2
import numpy as np
import pyautogui
import time

app=Flask(__name__)
camera=cv2.VideoCapture(0)
def grab():
    img=pyautogui.screenshot()
    frame=np.array(img)
    frame=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    return frame

def generate_frames():
    while True:
            
        ## read the camera frame
        success,frame=camera.read()
        ret,buffer=cv2.imencode('.jpg',frame)
        frame=buffer.tobytes()

        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def generate_frames1():
    while True:
            
        ## read the camera frame
        frame=grab()
        ret,buffer=cv2.imencode('.jpg',frame)
        frame=buffer.tobytes()

        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video')
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')
    
@app.route('/video1')
def video1():
    return Response(generate_frames1(),mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/ip')
def get_ip_route():
    return request.remote_addr
    
if __name__=="__main__":
    app.run(host='0.0.0.0', debug=True)
