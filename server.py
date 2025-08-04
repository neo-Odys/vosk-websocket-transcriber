import asyncio
import websockets
import sounddevice as sd
import queue
import json
from vosk import Model, KaldiRecognizer
import threading

samplerate = 16000
model = Model("vosk-model-small-pl-0.22") #you can change vosk model here
rec = KaldiRecognizer(model, samplerate)
q = queue.Queue()
clients = set()

def mic_loop(loop):
    with sd.RawInputStream(samplerate=samplerate, blocksize=8000, dtype='int16', channels=1, callback=mic_callback):
        print("Microphone is active")
        while True:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "")
                if text:
                    print(f"Final: {text}")
                    for ws in list(clients):
                        asyncio.run_coroutine_threadsafe(ws.send(json.dumps({"text": text})), loop)
            else:
                partial = json.loads(rec.PartialResult()).get("partial", "")
                if partial:
                    print(f"Partial: {partial}", end="\r")
                    for ws in list(clients):
                        asyncio.run_coroutine_threadsafe(ws.send(json.dumps({"partial": partial})), loop)

def mic_callback(indata, frames, time, status):
    if status:
        print(f"Audio stream status: {status}")
    q.put(bytes(indata))

async def handler(websocket):
    print("WebSocket client connected")
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)
        print("WebSocket client disconnected")

async def main():
    loop = asyncio.get_running_loop()
    threading.Thread(target=mic_loop, args=(loop,), daemon=True).start()
    print("WebSocket server running on ws://0.0.0.0:8765")
    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()

asyncio.run(main())

