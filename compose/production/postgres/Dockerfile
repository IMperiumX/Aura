FROM pgvector/pgvector:pg16

COPY ./compose/production/postgres/maintenance /usr/local/bin/maintenance
RUN chmod +x /usr/local/bin/maintenance/*
RUN mv /usr/local/bin/maintenance/* /usr/local/bin \
    && rmdir /usr/local/bin/maintenance

COPY --chown=postgres:postgres ./compose/production/postgres/conf/postgresql.conf /etc/postgresql.conf
CMD [ "-c", "config_file=/etc/postgresql.conf" ]

COPY --chown=postgres:postgres ./compose/production/postgres/conf/pg_hba.conf /etc/postgresql/16/main/pg_hba.conf
