from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json

import crud_clientes
import crud_periodos

port = 3000
crudClientes = crud_clientes.crud_clientes()
crudPeriodos = crud_periodos.crud_periodos()


class miServidor(SimpleHTTPRequestHandler):
    def responder(self, datos, codigo=200):
        # default=str convierte Decimal y fechas (date) a texto para el JSON
        cuerpo = json.dumps(datos, default=str).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_POST(self):
        try:
            longitud = int(self.headers['Content-Length'])
            datos = json.loads(self.rfile.read(longitud).decode("utf-8"))
            ruta = urlparse(self.path).path

            if ruta == "/cliente":
                respuesta = {'msg': crudClientes.administrar(datos)}
            elif ruta == "/calcular":
                respuesta = crudPeriodos.calcular(datos)
            elif ruta == "/periodo":
                respuesta = crudPeriodos.guardar(datos)
            else:
                return self.responder({'ok': False, 'msg': 'Ruta no encontrada'}, 404)
            self.responder(respuesta)
        except Exception as e:
            self.responder({'ok': False, 'msg': f'Error del servidor: {e}'}, 500)

    def do_GET(self):
        urlParse = urlparse(self.path)
        qs = parse_qs(urlParse.query)

        def p(nombre):
            return qs.get(nombre, [''])[0]

        try:
            if urlParse.path == "/clientes":
                self.responder(crudClientes.consultar(p('buscar')) or [])
            elif urlParse.path == "/productos":
                self.responder(crudPeriodos.productos())
            elif urlParse.path == "/periodos":
                self.responder(crudPeriodos.consultar(p('idCliente')))
            elif urlParse.path == "/cobro":
                self.responder(crudPeriodos.cobro(p('idCliente'), p('idProducto'), p('desde'), p('hasta')))
            elif urlParse.path == "/":
                self.path = "/index.html"
                return SimpleHTTPRequestHandler.do_GET(self)
            else:
                # Archivos estáticos (index.html, etc.)
                return SimpleHTTPRequestHandler.do_GET(self)
        except Exception as e:
            self.responder({'ok': False, 'msg': f'Error del servidor: {e}'}, 500)


print(f"Servidor corriendo en el puerto {port}")
server = HTTPServer(("localhost", port), miServidor)
server.serve_forever()