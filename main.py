import json, eventlet, sys
from eventlet import wsgi
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow
from QPanda3D.Panda3DWorld import Panda3DWorld
from QPanda3D.QPanda3DWidget import QPanda3DWidget
from direct.gui.OnscreenImage import OnscreenImage
from panda3d.core import LColor, LVecBase3, LineSegs, NodePath
from socketio import Server, WSGIApp
from threading import Thread
from math import cos, sin, radians

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

    def close(self):
        try:
            self.session.__exit__()
        except:
            exit()

    def run(self): # запуск сокета в потоке
        self.session = eventlet.listen((self.settings.ip, self.settings.port))
        Thread(target=wsgi.server, args=(self.session, self.web_app)).start()

class VisualizationWorld(Panda3DWorld): # Приложение визуализатора
    def __init__(self, settings, axis=False):
        Panda3DWorld.__init__(self)

        self.settings = settings
        self.models = [] # список объектов

        if axis:
            x_line = LineSegs()
            x_line.setColor(255, 0, 0)
            x_line.moveTo(0, 0, 0)
            x_line.drawTo(settings.polygon.scale.getX() * 2 + 2, 0, 0)
            x_line.setThickness(2)
            NodePath(x_line.create()).reparentTo(self.render)

            y_line = LineSegs()
            y_line.setColor(0, 0, 255)
            y_line.moveTo(0, 0, 0)
            y_line.drawTo(0, settings.polygon.scale.getZ() * 2 + 2, 0)
            y_line.setThickness(2)
            NodePath(y_line.create()).reparentTo(self.render)

            z_line = LineSegs()
            z_line.setColor(0, 255, 0)
            z_line.moveTo(0, 0, 0)
            z_line.drawTo(0, 0, settings.polygon.scale.getY() * 2 + 2)
            z_line.setThickness(2)
            NodePath(z_line.create()).reparentTo(self.render)

        self.setBackgroundColor(settings.workspace.background) # устанавливаем фон

        self.imageObject = OnscreenImage(image=settings.polygon.image_name, pos=(settings.polygon.scale.getX(), settings.polygon.scale.getZ(), 0)) # создаем объект полигона
        self.imageObject.setScale(settings.polygon.scale)
        self.imageObject.setP(270)
        self.imageObject.reparentTo(self.render) # добавляем в сцену объект полигона

        self.disableMouse()
        self.reset_camera() # устанавливаем камеру в стартовое положение

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
        self.camera.setY(self.camera.getY() + cos(radians(self.camera.getH())))
        self.camera.setX(self.camera.getX() - sin(radians(self.camera.getH())))

    def key_s_event(self):
        self.camera.setY(self.camera.getY() - cos(radians(self.camera.getH())))
        self.camera.setX(self.camera.getX() + sin(radians(self.camera.getH())))

    def key_a_event(self):
        self.camera.setY(self.camera.getY() - sin(radians(self.camera.getH())))
        self.camera.setX(self.camera.getX() - cos(radians(self.camera.getH())))

    def key_d_event(self):
        self.camera.setY(self.camera.getY() + sin(radians(self.camera.getH())))
        self.camera.setX(self.camera.getX() + cos(radians(self.camera.getH())))

    def key_q_event(self):
        self.camera.setZ(self.camera.getZ() + 1)

    def key_e_event(self):
        self.camera.setZ(self.camera.getZ() - 1)

    def add_model(self, model_type, position, yaw):
        model = self.loader.loadModel(f"{self.settings.objects.path}/{model_type}.egg") # загружаем модель
        self.models.append(model)
        model.setPos(*position)
        model.setH(yaw)
        model.setScale(self.settings.objects.scale)
        model.setP(270)
        model.setColor(self.settings.objects.color)
        model.reparentTo(self.render)

    def change_model_position(self, id, position, yaw):
        self.models[id].setPos(*position)
        self.models[id].setH(yaw)

class VisWidget(QPanda3DWidget):
    def __init__(self, world, main, server):
        self.world = world
        self.server = server
        self.__main = main
        super().__init__(self.world)

    def close(self):
        self.__main.close()
        self.server.close()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Left:
            self.world.key_left_event()
        elif event.key() == Qt.Key_Right:
            self.world.key_right_event()
        elif event.key() == Qt.Key_Up:
            self.world.key_up_event()
        elif event.key() == Qt.Key_Down:
            self.world.key_down_event()
        elif event.key() == Qt.Key_R:
            self.world.reset_camera()
        elif event.key() == Qt.Key_W:
            self.world.key_w_event()
        elif event.key() == Qt.Key_S:
            self.world.key_s_event()
        elif event.key() == Qt.Key_A:
            self.world.key_a_event()
        elif event.key() == Qt.Key_D:
            self.world.key_d_event()
        elif event.key() == Qt.Key_Q:
            self.world.key_q_event()
        elif event.key() == Qt.Key_E:
            self.world.key_e_event()

if __name__ == '__main__':
    settings = SettingsManager()
    settings.load("./settings/settings.json")
    world = VisualizationWorld(settings)
    server = ObjectServer(world, settings)
    
    app = QApplication(sys.argv)
    appw = QMainWindow()
    appw.setGeometry(50, 50, 800, 600)
    pandaWidget = VisWidget(world, appw, server)
    appw.setCentralWidget(pandaWidget)
    appw.show()

    server.run()
    
    sys.exit(app.exec_())