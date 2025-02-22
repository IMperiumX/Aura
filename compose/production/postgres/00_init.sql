CREATE USER replicator WITH REPLICATION ENCRYPTED PASSWORD 'ff';
SELECT pg_create_physical_replication_slot('replication_slot');
-- You can create other users/databases here as well.
-- CREATE USER app_user WITH PASSWORD 'app_password';
-- CREATE DATABASE app_db;
-- GRANT ALL PRIVILEGES ON DATABASE app_db TO app_user;
