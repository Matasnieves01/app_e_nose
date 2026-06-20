#!/usr/bin/env python3
"""Servidor WiFi en el HOST del UNO Q.

El contenedor de App Lab esta aislado de la red local (su puerto NO se ve desde
el telefono). Pero el HOST si tiene la IP de tu WiFi. Asi que el servidor corre
aqui: lee `result.json` (que escribe main.py en el contenedor, carpeta
compartida) y lo transmite por TCP a la app; recibe START/STOP de la app y los
escribe en `command.txt` para que main.py sepa cuando detectar.

Correr en el HOST por SSH (NO en App Lab), y dejarlo abierto:
    cd ~/ArduinoApps/prueba/python
    python3 wifi_host.py

La app se conecta a la IP del UNO Q (hostname -I -> la 192.168.x.x) puerto 8765.
Sin dependencias extra (solo asyncio).
"""
import asyncio
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
RESULT_FILE = os.path.join(_HERE, "result.json")
CMD_FILE = os.path.join(_HERE, "command.txt")

HOST = "0.0.0.0"
PORT = 8765

_clients = set()


async def handle_client(reader, writer):
    addr = writer.get_extra_info("peername")
    print(f"[wifi] cliente conectado: {addr}")
    _clients.add(writer)
    try:
        while not reader.at_eof():
            line = await reader.readline()
            if not line:
                break
            cmd = line.decode("utf-8", "ignore").strip().upper()
            if cmd in ("START", "STOP"):
                with open(CMD_FILE, "w") as f:
                    f.write(cmd)
                print(f"[wifi] comando recibido: {cmd}")
    except Exception as e:
        print(f"[wifi] error con cliente: {e}")
    finally:
        _clients.discard(writer)
        try:
            writer.close()
        except Exception:
            pass
        print(f"[wifi] cliente desconectado: {addr}")


async def broadcaster():
    """Lee result.json y lo manda a los clientes cuando cambia."""
    last = None
    while True:
        try:
            with open(RESULT_FILE) as f:
                content = f.read().strip()
            if content and content != last:
                last = content
                data = (content + "\n").encode("utf-8")
                for w in list(_clients):
                    try:
                        w.write(data)
                        await w.drain()
                    except Exception:
                        _clients.discard(w)
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[wifi] error leyendo resultado: {e}")
        await asyncio.sleep(0.3)


async def main():
    server = await asyncio.start_server(handle_client, HOST, PORT)
    print(f"[wifi] servidor TCP escuchando en {HOST}:{PORT}")
    print("[wifi] conecta la app a la IP del UNO Q (hostname -I) en ese puerto.")
    asyncio.create_task(broadcaster())
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[wifi] detenido.")
