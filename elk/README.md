# Aura ELK Stack - Production-Ready Centralized Logging

## 🎯 Overview

This ELK (Elasticsearch, Logstash, Kibana) stack implementation provides enterprise-grade centralized logging for the Aura healthcare platform. It transforms our ULTRATHINK logging system into a truly scalable, production-ready solution.

## 🏗️ Architecture

- **Elasticsearch** - Search and analytics engine for log storage
- **Logstash** - Data processing pipeline for log enrichment
- **Kibana** - Web interface for visualization and dashboards
- **Filebeat** - Lightweight log shipper
- **Metricbeat** - System and application metrics collector

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- At least 4GB RAM (8GB recommended)
- 20GB free disk space

### Start ELK Stack

```bash
# Make startup script executable
chmod +x start-elk.sh

# Start the ELK stack
./start-elk.sh start

# Check status
./start-elk.sh status
```

### Access Services

- **Kibana**: <http://localhost:5601>
- **Elasticsearch**: <http://localhost:9200>
- **Logstash**: <http://localhost:9600>
- **Elasticsearch Head**: <http://localhost:9100>

**Credentials**: `elastic` / `aura_elastic_password_2024`

## 📊 Management

### Django Commands

```bash
# Health check
python manage.py elk_admin health

# Setup ELK stack
python manage.py elk_admin setup

# Clean up old indices
python manage.py elk_admin cleanup --days 30

# Test logging
python manage.py elk_admin test

# Real-time monitoring
python manage.py elk_admin monitor
```

### Script Commands

```bash
./start-elk.sh start    # Start ELK stack
./start-elk.sh stop     # Stop ELK stack
./start-elk.sh status   # Show status
./start-elk.sh logs     # View logs
```

## 📈 Features

### Automatic Log Processing

- **GeoIP Enrichment** - Location data from IP addresses
- **User Agent Parsing** - Browser and device information
- **Performance Categorization** - Request speed classification
- **Security Threat Detection** - Automated threat scoring
- **Correlation ID Tracking** - Request tracing across services

### Index Management

- **Time-based Indices** - Daily index rotation
- **Index Lifecycle Management** - Automatic retention policies
- **Optimized Mappings** - Performance-tuned field types
- **Compression** - Storage optimization

### Monitoring & Alerting

- **Real-time Dashboards** - Application and system metrics
- **Health Monitoring** - Cluster and node status
- **Performance Tracking** - Request and database metrics
- **Security Monitoring** - Threat detection and analysis

## 🔍 Search Examples

### Kibana Queries

```bash
# Find errors in last hour
levelname:ERROR AND @timestamp:[now-1h TO now]

# Security events by IP
security_event:true AND client_ip:192.168.1.100

# Slow requests (> 2 seconds)
request_duration:>2.0

# User activity
user_id:"user123" AND @timestamp:[now-24h TO now]

# Database performance issues
db_queries:>20 OR db_time:>1.0
```

## 🔧 Configuration Files

- `docker-compose.elk.yml` - Main ELK stack configuration
- `elasticsearch/config/elasticsearch.yml` - Elasticsearch settings
- `logstash/config/logstash.yml` - Logstash configuration
- `logstash/pipeline/aura-logs.conf` - Log processing pipeline
- `kibana/config/kibana.yml` - Kibana settings
- `filebeat/config/filebeat.yml` - Log shipping configuration
- `metricbeat/config/metricbeat.yml` - Metrics collection

## 🐛 Troubleshooting

### Common Issues

**Elasticsearch won't start:**

```bash
# Check vm.max_map_count
cat /proc/sys/vm/max_map_count

# Set if needed (requires sudo)
sudo sysctl -w vm.max_map_count=262144
```

**Filebeat not shipping logs:**

```bash
# Check Filebeat logs
docker logs aura-filebeat

# Verify log file permissions
ls -la ../logs/
```

**Memory issues:**

```bash
# Check container memory usage
docker stats

# Adjust heap sizes in docker-compose.elk.yml
```

## 📚 Index Patterns

- `aura-logs-YYYY.MM.DD` - Main application logs
- `aura-security-YYYY.MM.DD` - Security events
- `aura-performance-YYYY.MM.DD` - Performance alerts
- `aura-metrics-YYYY.MM.DD` - System metrics

## 🔒 Security

- Basic authentication enabled by default
- SSL/TLS can be configured for production
- Role-based access control available
- Audit logging included

## 📊 Performance

- Optimized for high-throughput logging
- Automatic index optimization
- Circuit breaker patterns
- Buffer management and batching
- Compression and efficient storage

## 🔄 Maintenance

### Daily

```bash
./start-elk.sh status
python manage.py elk_admin monitor
```

### Weekly

```bash
python manage.py elk_admin optimize
python manage.py elk_admin cleanup --days 30
```

### Monthly

```bash
# Review index sizes and performance
python manage.py elk_admin indices

# Update templates if needed
python manage.py elk_admin templates
```

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review Docker logs: `./start-elk.sh logs [service]`
3. Run health checks: `python manage.py elk_admin health`
4. Monitor real-time: `python manage.py elk_admin monitor`

## 🎉 Success

Your ELK stack is now ready for production-scale centralized logging with real-time search, visualization, and alerting capabilities!
