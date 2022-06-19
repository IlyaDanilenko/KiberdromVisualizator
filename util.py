import json, eventlet
from eventlet import wsgi
from socketio import Server, WSGIApp
from threading import Thread

class ObjectServer: # SocketIO сервер, получающий координаты всех объектов
    def __init__(self, visualization, settings):
        self.settings = settings.server

        self.sio = Server(async_mode='threading')
        self.visualization = visualization
        self.web_app = WSGIApp(self.sio)

        @self.sio.event
        def position(sid, data): # функция обработки запроса
            for element in json.loads(data):
                if element['id'] >= len(self.visualization.models):
                    self.visualization.add_model(element['type'], (element['position']['x'], element['position']['y'], element['position']['z']), element['yaw']) # добавление объектов в визуализацию
                else:
                    self.visualization.change_model_position(element['id'], (element['position']['x'], element['position']['y'], element['position']['z']), element['yaw']) # изменение координат объектов по id
            
            self.sio.emit("response", {"response": "ok"}) # возвращаем ответ(необходимо для синхронизации)

    def close(self):
        try:
            self.session.__exit__()
        except:
            exit()

    def run(self): # запуск сокета в потоке
        self.session = eventlet.listen((self.settings.ip, self.settings.port))
        Thread(target=wsgi.server, args=(self.session, self.web_app)).start()