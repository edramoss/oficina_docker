"""Aplicação da oficina: uma página simples que gera logs.

Os logs sempre vão para o stdout (visíveis em `docker logs`). Se a variável
RSYSLOG_HOST estiver definida, também são enviados por syslog (UDP) ao rsyslog.
"""
import logging
import logging.handlers
import os
import random
import socket
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template_string, request

HOSTNAME = socket.gethostname()  # dentro de um container, é o ID do container
VARIANT = os.getenv("APP_VARIANT", "local")
RSYSLOG_HOST = os.getenv("RSYSLOG_HOST")
RSYSLOG_PORT = int(os.getenv("RSYSLOG_PORT", "514"))


class RFC5424Formatter(logging.Formatter):
    """Monta a mensagem no formato syslog RFC 5424.

    O SysLogHandler só acrescenta a prioridade (<PRI>) no início. O restante é
    daqui: é assim que o hostname do container chega como `source` no Graylog.
    """

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created, timezone.utc).isoformat()
        return f"1 {timestamp} {HOSTNAME} oficina-app {record.process} - - {super().format(record)}"


def configure_logging():
    root = logging.getLogger()
    root.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    stdout = logging.StreamHandler()
    stdout.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(message)s"))
    root.addHandler(stdout)

    if not RSYSLOG_HOST:
        root.info("RSYSLOG_HOST não definido: logs apenas no stdout")
        return

    try:
        syslog = logging.handlers.SysLogHandler(
            address=(RSYSLOG_HOST, RSYSLOG_PORT),
            facility=logging.handlers.SysLogHandler.LOG_LOCAL0,
            socktype=socket.SOCK_DGRAM,
        )
    except OSError as exc:
        # Log nunca pode derrubar a aplicação.
        root.warning("rsyslog indisponível em %s: %s", RSYSLOG_HOST, exc)
        return

    syslog.append_nul = False
    syslog.setFormatter(RFC5424Formatter("%(levelname)s %(message)s"))
    root.addHandler(syslog)
    root.info("enviando logs para o rsyslog em %s:%s/udp", RSYSLOG_HOST, RSYSLOG_PORT)


configure_logging()
log = logging.getLogger("oficina")
app = Flask(__name__)

EVENTOS = {
    "info": (logging.INFO, "pedido criado"),
    "warning": (logging.WARNING, "estoque baixo"),
    "error": (logging.ERROR, "falha no pagamento"),
}

PAGINA = """<!doctype html>
<html lang="pt-br"><head><meta charset="utf-8"><title>Oficina Docker</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 40rem; margin: 3rem auto; padding: 0 1rem; }
  code { background: #eef; padding: .1rem .3rem; border-radius: 4px; }
  a { display: inline-block; margin: .25rem; padding: .6rem 1rem; border-radius: 6px;
      color: #fff; text-decoration: none; }
  .info { background: #1565c0; } .warning { background: #ef6c00; } .error { background: #c62828; }
  .erro { background: #4a148c; }
</style></head><body>
<h1>🐳 Oficina Docker</h1>
<p>Container: <code>{{ hostname }}</code></p>
<p>Imagem: <code>{{ variant }}</code></p>
<p>Envio ao rsyslog: <code>{{ rsyslog }}</code></p>
<h2>Gerar logs</h2>
<a class="info" href="/evento/info">INFO</a>
<a class="warning" href="/evento/warning">WARNING</a>
<a class="error" href="/evento/error">ERROR</a>
<a class="erro" href="/erro">Exceção (HTTP 500)</a>
</body></html>"""


@app.after_request
def log_request(response):
    if request.path != "/saude": 
        log.info("http method=%s path=%s status=%s", request.method, request.path, response.status_code)
    return response


@app.get("/")
def index():
    return render_template_string(
        PAGINA,
        hostname=HOSTNAME,
        variant=VARIANT,
        rsyslog=f"{RSYSLOG_HOST}:{RSYSLOG_PORT}" if RSYSLOG_HOST else "desligado (só stdout)",
    )


@app.get("/evento/<nivel>")
def evento(nivel):
    if nivel not in EVENTOS:
        return jsonify(erro="use info, warning ou error"), 404
    level, texto = EVENTOS[nivel]
    pedido = random.randint(1000, 9999)
    log.log(level, "%s pedido=%s", texto, pedido)
    return jsonify(nivel=nivel, mensagem=texto, pedido=pedido, container=HOSTNAME)


@app.get("/erro")
def erro():
    return jsonify(resultado=1 / 0)  # de propósito: o traceback aparece no log


@app.get("/saude")
def saude():
    return jsonify(status="ok")
