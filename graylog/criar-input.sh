#!/bin/sh
# Cria no Graylog o input que recebe os logs do rsyslog.
set -eu

API="http://graylog:9000/api"
TITLE="Syslog TCP (rsyslog)"
AUTH="admin:$(cat /run/secrets/graylog_admin_password)"

echo "Aguardando a API do Graylog..."
until curl -fsS -o /dev/null -u "$AUTH" "$API/system/inputs"; do
  sleep 5
done

if curl -fsS -u "$AUTH" "$API/system/inputs" | grep -q "\"title\":\"$TITLE\""; then
  echo "Input '$TITLE' já existe."
  exit 0
fi

curl -fsS -u "$AUTH" -H "Content-Type: application/json" -H "X-Requested-By: criar-input" \
  -X POST "$API/system/inputs" -d @- <<JSON
{
  "title": "$TITLE",
  "type": "org.graylog2.inputs.syslog.tcp.SyslogTCPInput",
  "global": true,
  "configuration": {
    "bind_address": "0.0.0.0",
    "port": 1514,
    "recv_buffer_size": 1048576,
    "number_worker_threads": 2,
    "force_rdns": false,
    "allow_override_date": true,
    "store_full_message": false,
    "expand_structured_data": false
  }
}
JSON
echo
echo "Input '$TITLE' criado."
