from socketio import Client
import json

objects = []
objects.append({"id": 0, "type": "drone", "position": {"x": 0, "y": 1, "z": 4}, "yaw": 0})
objects.append({"id": 1, "type": "car", "position": {"x": 0, "y": 1, "z": 0}, "yaw": 0})
sio = Client() # клиент SocketIO

@sio.event
def response(data): # функция обработки ответа
    global objects
    if data["response"] == "ok": # если ответ получен, отправляем данные
        objects[0]['position']['x'] += 0.02
        sio.emit('position', json.dumps(objects))

sio.connect('http://localhost:8080') # подключаемся 
sio.emit('position', json.dumps(objects)) # начанаем отправку
sio.wait() # бесконечное ожидание
