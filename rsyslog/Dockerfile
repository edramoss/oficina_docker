FROM alpine:3.24.3

RUN apk add --no-cache rsyslog && mkdir -p /var/spool/rsyslog

COPY rsyslog.conf /etc/rsyslog.conf

EXPOSE 514/udp

# -n: fica em primeiro plano, senão o container terminaria.
CMD ["rsyslogd", "-n", "-f", "/etc/rsyslog.conf"]
