FROM debian:buster

RUN apt-get update && apt-get install -y apt-utils net-tools vim curl inetutils-ping telnet wget netcat htop && rm -rf /var/lib/apt/lists/*

RUN groupadd -o -g 1000 -r mfn && useradd -d /opt/mfn -u 1000 -m -r -g mfn mfn
USER mfn

RUN mkdir -p /opt/mfn/triggers_frontend/
COPY ./target/release/TriggersFrontend /opt/mfn/triggers_frontend/
COPY ./dockerrun.sh /
WORKDIR /opt/mfn/triggers_frontend

# ENV variables that can be set while starting the container from k8s
ENV TRIGGERS_FRONTEND_PORT=${TRIGGERS_FRONTEND_PORT:-"4997"}
ENV MANAGEMENT_URL=${MANAGEMENT_URL:-"http://httpbin.org/post"}
ENV MANAGEMENT_UPDATE_INTERVAL_SEC=${MANAGEMENT_UPDATE_INTERVAL_SEC:-"60"}  
ENV TRIGGERS_FRONTEND_LOG_LEVEL=${TRIGGERS_FRONTEND_LOG_LEVEL:-"info"}

CMD ["/dockerrun.sh"]
