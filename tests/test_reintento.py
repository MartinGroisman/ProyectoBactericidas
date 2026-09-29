# -*- coding: utf-8 -*-
"""
Prueba de los reintentos de red de scripts/buscar_candidatos.py ante una
respuesta truncada (http.client.IncompleteRead), el corte que dio NCBI en una
descarga de efetch. No se puede provocar contra NCBI real, asi que se usa un
servidor HTTP local que corta la respuesta a mitad de un chunk.

  python tests/test_reintento.py

Se ejecuta la funcion pedir() tal como esta en el script (extraida con ast,
porque el script corre la busqueda al importarse), sin esperas de backoff.
"""
from __future__ import annotations
import ast, http.client, http.server, os, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from types import SimpleNamespace

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "buscar_candidatos.py")


def cargar_pedir():
    with open(SCRIPT, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    fn = next(n for n in arbol.body if isinstance(n, ast.FunctionDef) and n.name == "pedir")
    sin_espera = SimpleNamespace(sleep=lambda s: None)
    ns = dict(http=http, time=sin_espera, urllib=urllib)
    exec(compile(ast.Module([fn], []), SCRIPT, "exec"), ns)
    return ns["pedir"]


class Servidor(http.server.BaseHTTPRequestHandler):
    """/corte: el primer pedido se corta; /siempre: todos se cortan; resto: 'ok'."""
    protocol_version = "HTTP/1.1"
    pedidos = 0

    def log_message(self, *a):
        pass

    def do_GET(self):
        type(self).pedidos += 1
        self.send_response(200)
        self.send_header("Transfer-Encoding", "chunked")
        self.end_headers()
        ruta = self.path.strip("/")
        if ruta == "siempre" or (ruta == "corte" and type(self).pedidos == 1):
            self.wfile.write(b"100\r\n" + b"x" * 50)   # anuncia 256 bytes, manda 50
            self.close_connection = True
            return
        self.wfile.write(b"2\r\nok\r\n0\r\n\r\n")


def main():
    pedir = cargar_pedir()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Servidor)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d/" % srv.server_port
    fallas = 0
    try:
        Servidor.pedidos = 0
        r = pedir(base + "corte")
        ok = r == b"ok" and Servidor.pedidos == 2
        print("  [%s] respuesta truncada: reintenta y recupera (%d pedidos)"
              % ("OK" if ok else "FALLA", Servidor.pedidos))
        fallas += not ok

        Servidor.pedidos = 0
        try:
            pedir(base + "siempre", intentos=3)
            ok = False
        except http.client.IncompleteRead:
            ok = Servidor.pedidos == 3
        print("  [%s] falla persistente: se propaga tras %d intentos"
              % ("OK" if ok else "FALLA", Servidor.pedidos))
        fallas += not ok
    finally:
        srv.shutdown()
    print("RESULTADO: %s" % ("TODO OK" if not fallas else "%d FALLAS" % fallas))
    return 1 if fallas else 0


def test_reintento():                       # para pytest
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
