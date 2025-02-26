FROM docker.io/traefik:3.3.4
# RUN mkdir -p /etc/traefik/acme \
#   && touch /etc/traefik/acme/acme.json \
#   && chmod 600 /etc/traefik/acme/acme.json
RUN mkdir -p /etc/traefik/
COPY ./compose/production/traefik/traefik.yml /etc/traefik
COPY ./certs /etc/traefik/certs
