import json, eventlet
from eventlet import wsgi
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import LColor, LVecBase3, WindowProperties
from socketio import Server, WSGIApp
from threading import Thread

def remapRGB(r, g, b): # на вход значения от 0 до 255, на выходе значения от 0 до 1
    return r / 255, g / 255, b / 255

class WorkspaceSettings: # настройки рабочего протсранства
    def __init__(self, settings):
        self.background = LColor(*remapRGB(settings['background']['r'], settings['background']['g'], settings['background']['b']), 1) # цвет заднего фона
        self.camera_position = LVecBase3(settings['camera']['position']['x'], settings['camera']['position']['y'], settings['camera']['position']['z']) # позиция камеры
        self.camera_angle = LVecBase3(settings['camera']['angle']['yaw'], settings['camera']['angle']['pitch'], settings['camera']['angle']['roll']) # углы наклона камеры

class PolygonSettings: # настройки полигона
    def __init__(self, settings):
        self.image_name = settings['image_name'] # путь до изображения полигона
        self.scale = LVecBase3(settings['scale']['x'] * 0.5, settings['scale']['z'], settings['scale']['y'] * 0.5) # размеры полигона

class ObjectsSetings: # настройки объектов
    def __init__(self, settings):
        self.path = settings['path'] # путь до папки с объектами (файлами .egg)
        self.color = LColor(*remapRGB(settings['color']['r'], settings['color']['g'], settings['color']['b']), 1) # цвета объектов
        self.scale = LVecBase3(settings['scale']['x'], settings['scale']['y'], settings['scale']['z']) # размеры объектов

class ServerSettings:
    def __init__(self, settings):
        self.ip = settings['ip']
        self.port = settings['port']

class SettingsManager: # менеджер настроек
    def __init__(self):
        self.workspace = None
        self.polygon = None
        self.objects = None
        self.server = None

    def load(self, path): # четние настроек из json файла
        with open(path, 'r') as f:
            settings = json.load(f)
            self.workspace = WorkspaceSettings(settings['workspace'])
            self.polygon = PolygonSettings(settings['polygon'])
            self.objects = ObjectsSetings(settings['objects'])
            self.server = ServerSettings(settings['server'])

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

    def run(self): # запуск сокета в потоке
        Thread(target=wsgi.server, args=(eventlet.listen((self.settings.ip, self.settings.port)), self.web_app)).start()

class VisualizationApp(ShowBase): # Приложение визуализатора
    def __init__(self, settings):
        ShowBase.__init__(self)

        self.settings = settings
        self.models = [] # список объектов

        self.setBackgroundColor(settings.workspace.background) # устанавливаем фон

        self.imageObject = OnscreenImage(image=settings.polygon.image_name, pos=(settings.polygon.scale.getX(), settings.polygon.scale.getZ(), 0)) # создаем объект полигона
        self.imageObject.setScale(settings.polygon.scale)
        self.imageObject.setP(270)
        self.imageObject.reparentTo(self.render) # добавляем в сцену объект полигона

        self.disableMouse()
        self.reset_camera() # устанавливаем камеру в стартовое положение

        # бинд клавиш на определенные действия
        self.accept('arrow_left-repeat', self.key_left_event)
        self.accept('arrow_right-repeat', self.key_right_event)
        self.accept('arrow_up-repeat', self.key_up_event)
        self.accept('arrow_down-repeat', self.key_down_event)
        self.accept('r', self.reset_camera)
        self.accept('w-repeat', self.key_w_event)
        self.accept('s-repeat', self.key_s_event)
        self.accept('a-repeat', self.key_a_event)
        self.accept('d-repeat', self.key_d_event)
        self.accept('q-repeat', self.key_q_event)
        self.accept('e-repeat', self.key_e_event)

    def key_left_event(self):
        self.camera.setH(self.camera.getH() + 1)

    def key_right_event(self):
        self.camera.setH(self.camera.getH() - 1)

    def key_up_event(self):
        self.camera.setP(self.camera.getP() + 1)

    def key_down_event(self):
        self.camera.setP(self.camera.getP() - 1)

    def reset_camera(self):
        self.camera.setPos(self.settings.workspace.camera_position)
        self.camera.setHpr(self.settings.workspace.camera_angle)

    def key_w_event(self):
        self.camera.setY(self.camera.getY() + 1)

    def key_s_event(self):
        self.camera.setY(self.camera.getY() - 1)

    def key_a_event(self):
        self.camera.setX(self.camera.getX() - 1)

    def key_d_event(self):
        self.camera.setX(self.camera.getX() + 1)

    def key_q_event(self):
        self.camera.setZ(self.camera.getZ() + 1)

    def key_e_event(self):
        self.camera.setZ(self.camera.getZ() - 1)

    def add_model(self, model_type, position, yaw):
        model = self.loader.loadModel(f"{self.settings.objects.path}/{model_type}.egg") # загружаем модель
        self.models.append(model)
        model.setPos(*position)
        model.setH(yaw)
        model.setScale(settings.objects.scale)
        model.setP(270)
        model.setColor(settings.objects.color)
        model.reparentTo(self.render)

    def change_model_position(self, id, position, yaw):
        self.models[id].setPos(*position)
        self.models[id].setH(yaw)

if __name__ == '__main__':
    settings = SettingsManager()
    settings.load("./settings/settings.json")
    app = VisualizationApp(settings)
    server = ObjectServer(app, settings)
    server.run()
    app.run()