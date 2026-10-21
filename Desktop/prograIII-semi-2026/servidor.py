import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, HTTPServer

from crud import Crud

os.chdir(os.path.dirname(os.path.abspath(__file__)))

crud = Crud()
sesiones = set()  # tokens de las sesiones iniciadas


class Servidor(BaseHTTPRequestHandler):

    def autenticado(self):
        cookie = self.headers.get("Cookie", "")
        for parte in cookie.split(";"):
            parte = parte.strip()
            if parte.startswith("sesion="):
                return parte[len("sesion="):] in sesiones
        return False

    def enviar_archivo(self, nombre, tipo):
        with open(nombre, "rb") as f:
            contenido = f.read()
        self.send_response(200)
        self.send_header("Content-Type", tipo + "; charset=utf-8")
        self.send_header("Content-Length", str(len(contenido)))
        self.end_headers()
        self.wfile.write(contenido)

    def redirigir(self, destino, cookie=None):
        self.send_response(302)
        self.send_header("Location", destino)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    def enviar_json(self, datos, codigo=200, cookie=None):
        cuerpo = json.dumps(datos).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0]

        if ruta == "/" or ruta == "/login.html":
            self.enviar_archivo("login.html", "text/html")
        elif ruta == "/login.js":
            self.enviar_archivo("login.js", "application/javascript")
        elif ruta == "/usuarios.js":
            self.enviar_archivo("usuarios.js", "application/javascript")
        elif ruta == "/usuarios.html":
            if self.autenticado():
                self.enviar_archivo("usuarios.html", "text/html")
            else:
                self.redirigir("/")
        elif ruta == "/logout":
            cookie = self.headers.get("Cookie", "")
            for parte in cookie.split(";"):
                parte = parte.strip()
                if parte.startswith("sesion="):
                    sesiones.discard(parte[len("sesion="):])
            self.redirigir("/", "sesion=; Max-Age=0; Path=/")
        else:
            self.send_error(404, "No encontrado")

    def do_POST(self):
        largo = int(self.headers.get("Content-Length", 0))
        datos = json.loads(self.rfile.read(largo).decode("utf-8"))

        if self.path == "/login":
            if crud.validar_login(datos.get("usuario", ""), datos.get("clave", "")):
                token = secrets.token_hex(16)
                sesiones.add(token)
                self.enviar_json({"ok": True}, cookie="sesion=" + token + "; Path=/")
            else:
                self.enviar_json({"ok": False, "msg": "Acceso denegado: usuario o clave incorrectos"})

        elif self.path == "/crud":
            if not self.autenticado():
                self.enviar_json({"ok": False, "msg": "Sesión no válida"}, 401)
                return
            self.enviar_json(crud.crud_usuarios_usss002025(datos))

        else:
            self.send_error(404, "No encontrado")


if __name__ == "__main__":
    servidor = HTTPServer(("127.0.0.1", 8000), Servidor)
    print("Servidor en http://127.0.0.1:8000  (Ctrl+C para detener)")
    servidor.serve_forever()