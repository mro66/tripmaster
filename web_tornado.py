from __future__ import print_function
import os.path
import tornado.web
import tornado.websocket
import tornado.httpserver
import tornado.ioloop
import threading
from random import randrange

DEBUG = 1
httpPort = 8080
websocketPort = 7070

#-------------------------------------------------------------------

# Schreibt eine Message in die Tornado Konsole
def printD(message):
    if DEBUG:
        print(message)

def getUptime():
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
        # uptime = str(timedelta(seconds = uptime_seconds))
        return uptime_seconds # uptime

def getPiRAM():
    with open('/proc/meminfo', 'r') as mem:
        tmp = 0
        for i in mem:
            sline = i.split()
            if str(sline[0]) == 'MemTotal:':
                total = int(sline[1])
            elif str(sline[0]) in ('MemFree:', 'Buffers:', 'Cached:'): 
                tmp += int(sline[1])
        free = tmp
        used = int(total) - int(free)
        usedPerc = (used * 100) / total
        return usedPerc

def getPiTemperature():
    with open("/sys/class/thermal/thermal_zone0/temp", 'r') as f:
        content = f.read().splitlines()
        return float(content[0]) / 1000.0

#-------------------------------------------------------------------

### Parse request from webif
#required format-> command:value
def WebRequestHandler(requestlist):
    returnlist = ""
    for request in requestlist:
        request =  request.strip()
        requestsplit = request.split(':')
        requestsplit.append("dummy")
        command = requestsplit[0]
        value = requestsplit[1]
        if value == "dummy":
            value = "0"

        if command == "localping":
            returnlist += "\n localping:ok"
        elif command == "LoadAVRnum":
            returnlist += "\n LoadAVRnum:"+open("/proc/loadavg").readline().split(" ")[:3][0]
        elif command == "Uptime":
            returnlist += "\n Uptime:"+str(getUptime()).split(".")[0]
        elif command == "RAMperc":
            returnlist += "\n RAMperc:"+str(getPiRAM())
            #returnlist += "\n RAMperc:"+str(psutil.phymem_usage().percent)
        elif command == "PiTEMP":
            returnlist += "\n PiTEMP:"+str(getPiTemperature())
        elif command == "System.Power":
            if value == "off":
                subprocess.Popen(["shutdown","-h","now"])
                return "System.Power:ok"
            elif value == "reboot":
                subprocess.Popen(["shutdown","-r","now"])
                return "System.Power:ok"

    return returnlist

def pushDataTimed(clients, what, when):
    what = str(what)
    when = float(when)
    for index, client in enumerate(clients):
        if client:
            client.write_message( WebRequestHandler(what.splitlines()) )
            timed = threading.Timer( when, pushDataTimed, [clients, what, when] )
            timed.start()
            timers.append(timed)

### WebSocket server tornado <-> WebInterface
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    connections = []
    # the client connected
    def check_origin(self, origin):
        return True   
    def open(self):
        printD("New WebSocket client connected")
        self.write_message("You are connected")
        self.stream.set_nodelay(True)
        self.connections.append(self)
        timed = threading.Timer( 2.0, pushDataTimed, [self.connections, "Uptime", "2.0"] )
        timed.start()
        timers.append(timed)
    # the client sent the message
    def on_message(self, message):
        printD("Message from WebIf: >>>"+message+"<<<")
        requestlist = message.splitlines() 
        self.write_message(WebRequestHandler(requestlist))
    # client disconnected
    def on_close(self):
        printD("WebSocket client disconnected")
        self.connections.remove(self)

#-------------------------------------------------------------------

class Web_Application(tornado.web.Application):
    def __init__(self):
        handlers = [   
              (r"/", MainHandler),
              (r"/static/(.*)", StaticHandler),
          ]
        settings = dict(
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            debug=DEBUG,
            autoescape=None
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class MainHandler(tornado.web.RequestHandler):
    #called every time someone sends a GET HTTP request
    @tornado.web.asynchronous
    def get(self):
        self.render(
            "index.html",
            debug = DEBUG,
            test = randrange(1, 1000),
        )

# deliver static files to page
class StaticHandler(tornado.web.RequestHandler):
    def get(self, filename):
        with open("static/" + filename, "r") as fh:
            self.file = fh.read()
        # write to page
        if filename.endswith(".css"):
            self.set_header("Content-Type", "text/css")
        elif filename.endswith(".js"):
            self.set_header("Content-Type", "text/javascript")
        elif filename.endswith(".png"):
            self.set_header("Content-Type", "image/png")
        self.write(self.file) 

try:
    timers = list()
    ws_app = tornado.web.Application([(r"/", WebSocketHandler),])
    ws_server = tornado.httpserver.HTTPServer(ws_app)
    ws_server.listen(websocketPort)

    web_server = tornado.httpserver.HTTPServer(Web_Application())
    web_server.listen(httpPort)
    tornado.ioloop.IOLoop.instance().start()
except (KeyboardInterrupt, SystemExit):
    for index, timer in enumerate(timers):
        if timer:
            timer.cancel()
    print("\nQuit\n")