#
from flask import Flask, request,render_template,Response
import cv2
import numpy as np
import pyautogui
import time
import pyaudio
#

#! Python38
import os
import time
import atexit
from functools import wraps

# third party imports
import pyautogui
from PIL import ImageDraw
from werkzeug.utils import secure_filename
from flask import Flask, request, send_from_directory, render_template, jsonify


# let's code!


app = Flask(__name__)
pg = {'methods': ['POST', 'GET']}


config = {
    'admin_login': 'a',
    'admin_pass': 'a',
    'spectators': {'user1': 'pass1', 'user2': 'pass2'},
    'spectators_allowed': True,
    'spectators_allowed_without_password': False,
    'forbidden_ips': ["127.0.0.1"],

    'host': '0.0.0.0',
    'port': 5000,
    'debug': True,

    'logged_users': {},
    'last_shot': time.time()
}


app.config.update(config)


def is_admin(client_ip: str) -> bool:
    for user, ip in config['logged_users'].items():
        if client_ip == ip:
            if user == config['admin_login']:
                return True
    return False


def is_spectator(client_ip: str) -> bool:
    for user, ip in config['logged_users'].items():
        if client_ip == ip:
            if user in config['spectators'].keys():
                return True
    return False


def is_logged(client_ip: str) -> bool:
    result = client_ip in config['logged_users'].values()
    # print('is_logged:', result)
    return result


def is_forbidden_ip(ip: str) -> bool:
    return ip in config['forbidden_ips']


def js_redirect(link: str) -> str:
    link = link if link[0] == '/' else '/' + link
    return f"<script>window.location='{link}';</script>"


@app.route('/', **pg)
def main_route():
    result = ""
    for rule in sorted([str(_) for _ in app.url_map.iter_rules()]):
        result += f'<a href="{rule}">{rule}</a></br>'
    return result
#
@app.route('/hola', **pg)
def index():
    return render_template('index.html')
#
#
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


@app.route('/video',**pg)
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')

FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 44100
CHUNK = 1024
RECORD_SECONDS = 5

audio1 = pyaudio.PyAudio()
 


def genHeader(sampleRate, bitsPerSample, channels):
    datasize = 2000*10**6
    o = bytes("RIFF",'ascii')                                               # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4,'little')                               # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE",'ascii')                                              # (4byte) File type
    o += bytes("fmt ",'ascii')                                              # (4byte) Format Chunk Marker
    o += (16).to_bytes(4,'little')                                          # (4byte) Length of above format data
    o += (1).to_bytes(2,'little')                                           # (2byte) Format type (1 - PCM)
    o += (channels).to_bytes(2,'little')                                    # (2byte)
    o += (sampleRate).to_bytes(4,'little')                                  # (4byte)
    o += (sampleRate * channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
    o += (channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
    o += (bitsPerSample).to_bytes(2,'little')                               # (2byte)
    o += bytes("data",'ascii')                                              # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4,'little')                                    # (4byte) Data size in bytes
    return o

@app.route('/audio',**pg)
def audio():
    # start Recording
    def sound():

        CHUNK = 1024
        sampleRate = 44100
        bitsPerSample = 16
        channels = 2
        wav_header = genHeader(sampleRate, bitsPerSample, channels)

        stream = audio1.open(format=FORMAT, channels=CHANNELS,
                        rate=RATE, input=True,input_device_index=1,
                        frames_per_buffer=CHUNK)
        print("recording...")
        #frames = []
        first_run = True
        while True:
           if first_run:
               data = wav_header + stream.read(CHUNK)
               first_run = False
           else:
               data = stream.read(CHUNK)
           yield(data)

    return Response(sound())

#

@app.route('/ip', **pg)
def get_ip_route():
    return request.remote_addr


@app.route('/login', **pg)
def login_route():

    if request.args.get('error', False) == 'ban':
        return 'Admin disallows you to login'

    if request.method == 'GET':
        if is_admin(request.remote_addr):
            return js_redirect('/rdp')
        if request.remote_addr in config['logged_users'].values():
            return js_redirect('/cast')
        if is_spectator(request.remote_addr):
            return js_redirect('/cast')
        return render_template('login.html')

    if request.method == 'POST':
        args = dict(request.form)

        if 'user' in args and 'pass' in args:
            if args['user'] in config['logged_users']:
                return 'This login is busy'
            if args['user'] == config['admin_login'] and args['pass'] == config['admin_pass']:
                config['logged_users'][args['user']] = request.remote_addr
                print(f'ADMIN {request.remote_addr} has logged in')
                if 'next' in args:
                    return js_redirect(args['next'])
                return js_redirect('/rdp')
            if config['spectators_allowed']:
                for user, passwd in config['spectators'].items():
                    if args['user'] == user and passwd == args['pass']:
                        config['logged_users'][args['user']] = request.remote_addr
                        print(f'User "{user}" at ip:{request.remote_addr} has logged in')
                        return js_redirect('/cast')
            else:
                print(f'Somebody at {request.remote_addr} tried to login but failed due to spectators are disabled')
                return 'Spectators are disabled by admin'
        return 'Pass both valid user name and password. One user cannot login twice'


@app.route('/logout', **pg)
def logout_route():
    name_to_logout = False
    for user, ip in config['logged_users'].items():
        if ip == request.remote_addr:
            name_to_logout = user
            break
    if name_to_logout:
        del config['logged_users'][name_to_logout]
        print(f'User {name_to_logout} at {request.remote_addr} logout')
    return js_redirect('/login?next=/rdp')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_logged(get_ip_route()):
            return f(*args, **kwargs)
        return js_redirect('/login?next=/rdp')
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if is_admin(get_ip_route()):
            return f(*args, **kwargs)
        return js_redirect('/login?next=/rdp')
    return decorated_function


def guard(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = get_ip_route()
        if ip in config['forbidden_ips']:
            return js_redirect('/login?error=ban')
        if is_admin(ip):
            return f(*args, **kwargs)
        if is_logged(ip):
            return f(*args, **kwargs)
        if config['spectators_allowed']:
            if config['spectators_allowed_without_password']:
                return f(*args, **kwargs)
        return js_redirect("/login?next=/cast")
    return decorated_function  # ()


@app.route('/logged', **pg)
@admin_required
def logged_route():
    return str(config['logged_users'])


@app.route('/logout_all')
@admin_required
def logout_all_route():
    config['logged_users'] = {}
    return js_redirect('/login?next=/rdp')


@app.route('/screenshot', methods=['GET'])
@guard
def get_screenshot_route():
    if time.time() - config['last_shot'] > 1.:
        shot = pyautogui.screenshot()
        draw = ImageDraw.Draw(shot)
        x, y = pyautogui.position()
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill='green', outline='red')
        shot.save('screenshots/last.jpg')
        config['last_shot'] = time.time()
    return send_from_directory('screenshots', 'last.jpg', mimetype="image/jpg")


@app.route('/mouse', **pg)
@admin_required
def move_mouse_route():
    args = dict(request.args)
    try:
        x = ''.join(_ for _ in args['x'] if _.isdigit())  # anti-XSS
        y = ''.join(_ for _ in args['y'] if _.isdigit())  # refactor it, wrong way ;>
        pyautogui.moveTo(int(x), int(y))
        buttons = int(args.get('buttons', 0))
        if buttons > 0:
            print('buttons:', buttons)
            pyautogui.click(int(x), int(y))
        return 'OK'
    except (ValueError, Exception) as e:
        return str(e)


@app.route('/special_keys', **pg)
def special_keys():
    return jsonify({'keys': [
            '\t', '\n', '\r', ' ', '!', '"', '#', '$', '%', '&', "'", '(',
            ')', '*', '+', ',', '-', '.', '/', '0', '1', '2', '3', '4', '5', '6', '7',
            '8', '9', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`',
            'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o',
            'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', '{', '|', '}', '~',
            'accept', 'add', 'alt', 'altleft', 'altright', 'apps', 'backspace',
            'capslock', 'clear', 'ctrl', 'ctrlleft', 'ctrlright', 'del', 'divide',
            'down', 'end', 'enter', 'esc', 'escape', 'execute', 'f1', 'f10',
            'f11', 'f12', 'f13', 'f14', 'f15', 'f16', 'f17', 'f18', 'f19', 'f2', 'f20',
            'f21', 'f22', 'f23', 'f24', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9',
            'final', 'fn', 'home', 'insert', 'junja', 'launchapp1',
            'left', 'modechange', 'multiply', 'num0', 'num1', 'num2', 'num3', 'num4',
            'num5', 'num6', 'num7', 'num8', 'num9', 'numlock', 'pagedown', 'pageup',
            'pause', 'pgdn', 'pgup', 'playpause', 'prevtrack', 'print', 'printscreen',
            'prntscrn', 'prtsc', 'prtscr', 'return', 'right', 'scrolllock', 'select', 'separator',
            'shift', 'shiftleft', 'shiftright', 'sleep', 'space', 'stop', 'subtract', 'tab',
            'up', 'volumedown', 'volumemute', 'volumeup', 'win', 'winleft', 'winright', 'yen',
            'command', 'option', 'optionleft', 'optionright'
        ]})


@app.route('/keyboard', **pg)
def keyboard_route():
    if request.method == 'POST':
        if is_admin(request.remote_addr):
            keys = request.args.get('keys', False)
            if keys:
                pyautogui.write(keys)
                return 'Ok'
            else:
                special = request.args.get('special', False)
                if special:
                    try:
                        pyautogui.press(special)
                        return 'Ok'
                    except (RuntimeError, Exception) as e:
                        return str(e)

                specials = request.args.get('specials', False)
                if isinstance(specials, (list, tuple)):
                    try:
                        for s in specials:
                            pyautogui.write(s)
                        return 'Ok'
                    except (RuntimeError, Exception) as e:
                        return str(e)
            return 'No keys'
    return js_redirect('/login?next=/rdp')


@app.route('/rdp', **pg)
@app.route('/remote_desktop', **pg)
@admin_required
def remote_desktop_route():
    if is_forbidden_ip(request.remote_addr):
        return js_redirect('/login?error=ban')
    if request.method == 'GET':
        return render_template('rdp.html')


@app.route('/cast', methods=['GET'])
def screen_cast_route():
    if is_forbidden_ip(request.remote_addr):
        return js_redirect('/login?error=ban')
    if is_admin(request.remote_addr):
        return js_redirect('/rdp')
    if config['spectators_allowed']:
        if config['spectators_allowed_without_password']:
            return render_template('spectator.html')
        if is_spectator(request.remote_addr):
            return render_template('spectator.html')
        return js_redirect('/login?next=/cast')
    return 'Spectators are not allowed by admin'


@app.route('/download', methods=['GET'])
@admin_required
def download():
    path = request.args.get('path', False)
    if path:
        sep = os.path.sep

        if os.name == 'nt':
            path = rf'{path}'.replace('/', '\\')
        else:
            path = rf'{path}'.replace('\\', '/')

        if sep in path:
            split = path.split(sep)
            dir_ = sep.join(split[:-1])
            name = split[-1]
        else:
            dir_ = os.getcwd()
            name = path
        return send_from_directory(secure_filename(dir_), name)
    return 'download error: ' + path


@app.route('/upload', **pg)
@admin_required
def upload_route():
    cwd = os.getcwd()
    if request.method == 'POST':
        dir_ = request.args.get('dir', cwd)
        file = request.files['file']
        if file.filename == '':
            return '/upload error empty filename'

        path = secure_filename(os.path.join(dir_, file.filename))
        file.save(path)
        return '/upload OK: ' + path
    if request.method == 'GET':
        return render_template('upload.html', dest_dir=cwd)


def clean_tmp_png():
    cwd = os.getcwd()
    [os.unlink(os.path.join(cwd, file)) for file in os.listdir(cwd) if file[0] == '.' and file.endswith('.png')]


def do_once():
    if 'do_once' not in config:
        shot = pyautogui.screenshot()
        draw = ImageDraw.Draw(shot)
        x, y = pyautogui.position()
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill='green', outline='red')
        shot.save('screenshots/last.jpg')
        config['do_once'] = True


do_once()
atexit.register(clean_tmp_png)


if __name__ == '__main__':
    app.run(host=config['host'], port=config['port'], debug=config['debug'])
