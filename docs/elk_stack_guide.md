# ELK Stack Guide for Aura Logging System

## 🎯 **Overview**

The Aura ELK (Elasticsearch, Logstash, Kibana) stack provides enterprise-grade centralized logging at scale. This implementation transforms our ULTRATHINK logging system into a truly production-ready, scalable solution that can handle millions of log entries with real-time search, visualization, and alerting capabilities.

## 🏗️ **Architecture**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django App    │    │    Filebeat     │    │    Logstash     │
│                 │───▶│   (Shipper)     │───▶│  (Processing)   │
│   Log Files     │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Kibana      │    │ Elasticsearch   │    │   Metricbeat    │
│ (Visualization) │◀───│   (Storage)     │◀───│   (Metrics)     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Components**

1. **Elasticsearch** - Search and analytics engine for log storage
2. **Logstash** - Data processing pipeline for log enrichment
3. **Kibana** - Web interface for visualization and dashboards
4. **Filebeat** - Lightweight log shipper
5. **Metricbeat** - System and application metrics collector

## 🚀 **Quick Start**

### **Prerequisites**

- Docker and Docker Compose
- At least 4GB RAM (8GB recommended)
- 20GB free disk space
- Linux/macOS (Windows with WSL2)

### **1. Start ELK Stack**

```bash
# Make the startup script executable
chmod +x elk/start-elk.sh

# Start the ELK stack
./elk/start-elk.sh start
```

### **2. Verify Installation**

```bash
# Check status
./elk/start-elk.sh status

# View logs
./elk/start-elk.sh logs
```

### **3. Access Services**

- **Kibana**: http://localhost:5601
- **Elasticsearch**: http://localhost:9200
- **Logstash**: http://localhost:9600
- **Elasticsearch Head**: http://localhost:9100

**Default Credentials:**
- Username: `elastic`
- Password: `aura_elastic_password_2024`

## ⚙️ **Configuration**

### **Django Settings Integration**

Add to your Django settings to enable ELK logging:

```python
# settings/production.py

# ELK Stack Configuration
ELK_ENABLED = True
ELASTICSEARCH_HOSTS = ['http://localhost:9200']
ELASTICSEARCH_USERNAME = 'elastic'
ELASTICSEARCH_PASSWORD = 'aura_elastic_password_2024'

# Add ElasticsearchHandler to logging configuration
LOGGING['handlers']['elasticsearch'] = {
    'level': 'INFO',
    'class': 'aura.core.logging_handlers.ElasticsearchHandler',
    'hosts': ELASTICSEARCH_HOSTS,
    'username': ELASTICSEARCH_USERNAME,
    'password': ELASTICSEARCH_PASSWORD,
    'index_pattern': 'aura-logs-%Y.%m.%d',
    'buffer_size': 100,
    'flush_interval': 5.0,
}

# Add to root logger
LOGGING['loggers']['']['handlers'].append('elasticsearch')
```

### **Environment Variables**

```bash
# .env file
ELK_ELASTICSEARCH_HOST=http://localhost:9200
ELK_KIBANA_HOST=http://localhost:5601
ELK_LOGSTASH_HOST=http://localhost:9600
ELK_USERNAME=elastic
ELK_PASSWORD=aura_elastic_password_2024
```

## 📊 **Index Patterns and Data Flow**

### **Index Structure**

- `aura-logs-YYYY.MM.DD` - Main application logs
- `aura-security-YYYY.MM.DD` - Security events
- `aura-performance-YYYY.MM.DD` - Performance alerts
- `aura-metrics-YYYY.MM.DD` - System metrics

### **Log Processing Pipeline**

1. **Django Application** → Writes structured JSON logs to files
2. **Filebeat** → Ships logs to Logstash
3. **Logstash** → Processes, enriches, and routes logs
4. **Elasticsearch** → Indexes and stores logs
5. **Kibana** → Provides search and visualization

### **Data Enrichment**

Logstash automatically enriches logs with:

- **GeoIP Information** - Location data from IP addresses
- **User Agent Parsing** - Browser and device information
- **Performance Categorization** - Slow/fast request classification
- **Security Threat Detection** - Automated threat scoring
- **Correlation ID Tracking** - Request tracing across services

## 🔧 **Management Commands**

### **ELK Administration**

```bash
# Health check
python manage.py elk_admin health

# Setup ELK stack
python manage.py elk_admin setup

# Clean up old indices
python manage.py elk_admin cleanup --days 30

# List indices
python manage.py elk_admin indices

# Test logging
python manage.py elk_admin test

# Real-time monitoring
python manage.py elk_admin monitor
```

### **Logging Health Check**

```bash
# Comprehensive logging system health check
python manage.py logging_health_check --format json --time-window 1h
```

## 📈 **Kibana Dashboards**

### **Pre-built Dashboards**

1. **Application Overview**
   - Request volume and response times
   - Error rates and status codes
   - User activity patterns

2. **Security Dashboard**
   - Authentication events
   - Threat detection alerts
   - Geographic access patterns

3. **Performance Dashboard**
   - Database query performance
   - Memory and CPU usage
   - Slow request analysis

4. **System Metrics**
   - Server health monitoring
   - Container resource usage
   - ELK stack performance

### **Creating Custom Dashboards**

1. Access Kibana at http://localhost:5601
2. Go to **Management** → **Index Patterns**
3. Create patterns for `aura-logs-*`, `aura-security-*`, etc.
4. Navigate to **Dashboard** → **Create New Dashboard**
5. Add visualizations and save

## 🔍 **Search and Query Examples**

### **Common Kibana Queries**

```bash
# Find all errors in the last hour
levelname:ERROR AND @timestamp:[now-1h TO now]

# Security events by IP
security_event:true AND client_ip:192.168.1.100

# Slow requests (> 2 seconds)
request_duration:>2.0

# User activity for specific user
user_id:"user123" AND @timestamp:[now-24h TO now]

# Database performance issues
db_queries:>20 OR db_time:>1.0

# Authentication failures
threat_type:"authentication_failed"

# Requests by correlation ID
correlation_id:"abc123-def456"
```

### **Elasticsearch API Queries**

```bash
# Search recent logs
curl -X GET "localhost:9200/aura-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -u elastic:aura_elastic_password_2024 \
  -d '{
    "query": {
      "range": {
        "@timestamp": {
          "gte": "now-1h"
        }
      }
    }
  }'

# Aggregate by log level
curl -X GET "localhost:9200/aura-logs-*/_search" \
  -H 'Content-Type: application/json' \
  -u elastic:aura_elastic_password_2024 \
  -d '{
    "size": 0,
    "aggs": {
      "log_levels": {
        "terms": {
          "field": "levelname",
          "size": 10
        }
      }
    }
  }'
```

## 🔧 **Advanced Configuration**

### **Index Lifecycle Management (ILM)**

The ELK stack includes automatic index lifecycle management:

- **Hot Phase**: Active indices for recent data
- **Warm Phase**: Older data (7+ days) with reduced replicas
- **Cold Phase**: Archive data (30+ days)
- **Delete Phase**: Automatic deletion after 90 days

### **Performance Tuning**

#### **Elasticsearch**

```yaml
# elk/elasticsearch/config/elasticsearch.yml
indices.memory.index_buffer_size: 20%
thread_pool.write.size: 4
thread_pool.search.size: 6
```

#### **Logstash**

```yaml
# elk/logstash/config/logstash.yml
pipeline.workers: 4
pipeline.batch.size: 1000
queue.type: persisted
queue.max_events: 50000
```

#### **Filebeat**

```yaml
# elk/filebeat/config/filebeat.yml
queue.mem.events: 4096
queue.mem.flush.min_events: 512
output.logstash.bulk_max_size: 2048
```

### **Security Configuration**

#### **Enable SSL/TLS**

```yaml
# elk/elasticsearch/config/elasticsearch.yml
xpack.security.http.ssl.enabled: true
xpack.security.transport.ssl.enabled: true
```

#### **Custom Authentication**

```bash
# Create additional users
curl -X POST "localhost:9200/_security/user/aura_readonly" \
  -H 'Content-Type: application/json' \
  -u elastic:aura_elastic_password_2024 \
  -d '{
    "password": "readonly_password",
    "roles": ["kibana_user", "aura_logs_reader"]
  }'
```

## 🚨 **Monitoring and Alerting**

### **Built-in Monitoring**

The ELK stack includes comprehensive monitoring:

- **Cluster Health** - Node status and shard allocation
- **Index Performance** - Indexing and search rates
- **Resource Usage** - Memory, CPU, and disk utilization
- **Pipeline Metrics** - Logstash processing statistics

### **Custom Alerts**

#### **Watcher Alerts (X-Pack)**

```json
{
  "trigger": {
    "schedule": {
      "interval": "1m"
    }
  },
  "input": {
    "search": {
      "request": {
        "indices": ["aura-logs-*"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {"term": {"levelname": "ERROR"}},
                {"range": {"@timestamp": {"gte": "now-1m"}}}
              ]
            }
          }
        }
      }
    }
  },
  "condition": {
    "compare": {
      "ctx.payload.hits.total": {
        "gt": 10
      }
    }
  },
  "actions": {
    "send_email": {
      "email": {
        "to": ["admin@aura.com"],
        "subject": "High Error Rate Alert",
        "body": "More than 10 errors in the last minute"
      }
    }
  }
}
```

### **External Monitoring Integration**

#### **Prometheus Metrics**

```yaml
# Add to docker-compose.elk.yml
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
```

#### **Grafana Dashboards**

```yaml
grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
```

## 🔧 **Maintenance and Operations**

### **Daily Operations**

```bash
# Check cluster health
./elk/start-elk.sh status

# Monitor log ingestion
python manage.py elk_admin monitor

# Check index sizes
python manage.py elk_admin indices
```

### **Weekly Maintenance**

```bash
# Optimize indices
python manage.py elk_admin optimize

# Clean up old indices
python manage.py elk_admin cleanup --days 30

# Check template updates
python manage.py elk_admin templates
```

### **Backup and Recovery**

#### **Snapshot Configuration**

```bash
# Create snapshot repository
curl -X PUT "localhost:9200/_snapshot/aura_backup" \
  -H 'Content-Type: application/json' \
  -u elastic:aura_elastic_password_2024 \
  -d '{
    "type": "fs",
    "settings": {
      "location": "/backup/elasticsearch"
    }
  }'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/aura_backup/snapshot_1" \
  -H 'Content-Type: application/json' \
  -u elastic:aura_elastic_password_2024 \
  -d '{
    "indices": "aura-*",
    "ignore_unavailable": true,
    "include_global_state": false
  }'
```

### **Scaling**

#### **Horizontal Scaling**

```yaml
# docker-compose.elk.yml - Add more Elasticsearch nodes
elasticsearch-2:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - node.name=aura-es-node-2
    - cluster.name=aura-logging-cluster
    - discovery.seed_hosts=elasticsearch
    - cluster.initial_master_nodes=aura-es-node
```

#### **Vertical Scaling**

```yaml
# Increase resources
elasticsearch:
  environment:
    - "ES_JAVA_OPTS=-Xms4g -Xmx4g"
  deploy:
    resources:
      limits:
        memory: 8g
      reservations:
        memory: 4g
```

## 🐛 **Troubleshooting**

### **Common Issues**

#### **Elasticsearch Won't Start**

```bash
# Check vm.max_map_count
cat /proc/sys/vm/max_map_count

# Set if needed
sudo sysctl -w vm.max_map_count=262144

# Make permanent
echo 'vm.max_map_count=262144' | sudo tee -a /etc/sysctl.conf
```

#### **Filebeat Not Shipping Logs**

```bash
# Check Filebeat logs
docker logs aura-filebeat

# Verify log file permissions
ls -la logs/

# Test connectivity to Logstash
curl -v http://localhost:5044
```

#### **Logstash Processing Issues**

```bash
# Check Logstash logs
docker logs aura-logstash

# Verify pipeline configuration
curl http://localhost:9600/_node/stats/pipeline

# Check dead letter queue
curl http://localhost:9600/_node/stats/pipeline/dead_letter_queue
```

#### **Kibana Connection Issues**

```bash
# Check Kibana logs
docker logs aura-kibana

# Verify Elasticsearch connection
curl -u elastic:aura_elastic_password_2024 http://localhost:9200/_cluster/health

# Reset Kibana index
curl -X DELETE "localhost:9200/.kibana*" -u elastic:aura_elastic_password_2024
```

### **Performance Issues**

#### **High Memory Usage**

```bash
# Check Elasticsearch heap usage
curl -u elastic:aura_elastic_password_2024 "localhost:9200/_nodes/stats/jvm"

# Adjust heap size
# In docker-compose.elk.yml
environment:
  - "ES_JAVA_OPTS=-Xms2g -Xmx2g"
```

#### **Slow Search Performance**

```bash
# Check index statistics
curl -u elastic:aura_elastic_password_2024 "localhost:9200/aura-logs-*/_stats"

# Force merge indices
python manage.py elk_admin optimize

# Check query performance
curl -u elastic:aura_elastic_password_2024 "localhost:9200/aura-logs-*/_search?explain=true"
```

### **Data Issues**

#### **Missing Logs**

```bash
# Check Filebeat registry
docker exec aura-filebeat cat /usr/share/filebeat/data/registry/filebeat/log.json

# Verify log file format
head -n 5 logs/django.log

# Test log parsing
echo '{"message": "test", "@timestamp": "2024-01-01T00:00:00Z"}' | \
  curl -X POST "localhost:5000" -H "Content-Type: application/json" -d @-
```

#### **Index Corruption**

```bash
# Check index health
curl -u elastic:aura_elastic_password_2024 "localhost:9200/_cluster/health?level=indices"

# Repair index
curl -X POST "localhost:9200/aura-logs-2024.01.01/_recovery" \
  -u elastic:aura_elastic_password_2024
```

## 📚 **Best Practices**

### **Log Management**

1. **Use structured logging** - Always log in JSON format
2. **Include correlation IDs** - Track requests across services
3. **Implement log sampling** - Prevent log storms
4. **Set appropriate log levels** - Use DEBUG sparingly in production
5. **Include context** - Add user, IP, and request information

### **Index Management**

1. **Use time-based indices** - Daily indices for better management
2. **Implement ILM policies** - Automatic lifecycle management
3. **Monitor index sizes** - Prevent oversized indices
4. **Use appropriate mapping** - Optimize field types
5. **Regular maintenance** - Force merge and cleanup

### **Security**

1. **Enable authentication** - Never run without security
2. **Use HTTPS/TLS** - Encrypt data in transit
3. **Implement RBAC** - Role-based access control
4. **Monitor access** - Log all administrative actions
5. **Regular updates** - Keep ELK stack updated

### **Performance**

1. **Optimize hardware** - SSD storage and adequate RAM
2. **Tune JVM settings** - Appropriate heap sizes
3. **Monitor metrics** - Use built-in monitoring
4. **Implement caching** - Query result caching
5. **Load balancing** - Distribute load across nodes

## 🔗 **Integration Examples**

### **Django Middleware Integration**

```python
# middleware.py
class ELKLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        response = self.get_response(request)

        duration = time.time() - start_time

        logger.info("Request processed", extra={
            'correlation_id': getattr(request, 'correlation_id', None),
            'user_id': getattr(request.user, 'id', None),
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'request_duration': duration,
            'client_ip': self.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        })

        return response
```

### **Celery Task Integration**

```python
# tasks.py
from celery import Task
import logging

logger = logging.getLogger(__name__)

class ELKTask(Task):
    def __call__(self, *args, **kwargs):
        start_time = time.time()

        try:
            result = super().__call__(*args, **kwargs)

            logger.info("Task completed", extra={
                'task_name': self.name,
                'task_id': self.request.id,
                'task_duration': time.time() - start_time,
                'task_status': 'success',
            })

            return result
        except Exception as e:
            logger.error("Task failed", extra={
                'task_name': self.name,
                'task_id': self.request.id,
                'task_duration': time.time() - start_time,
                'task_status': 'failed',
                'error_message': str(e),
            }, exc_info=True)
            raise
```

## 📞 **Support and Resources**

### **Documentation Links**

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Logstash Documentation](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Kibana Documentation](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Filebeat Documentation](https://www.elastic.co/guide/en/beats/filebeat/current/index.html)

### **Community Resources**

- [Elastic Community Forum](https://discuss.elastic.co/)
- [Elasticsearch GitHub](https://github.com/elastic/elasticsearch)
- [ELK Stack Examples](https://github.com/elastic/examples)

### **Professional Support**

For production deployments, consider:
- Elastic Cloud (hosted solution)
- Elastic Support subscriptions
- Professional services and training

---

**🎉 Congratulations!** You now have a production-ready ELK stack for centralized logging at scale. This implementation provides enterprise-grade logging capabilities with real-time search, visualization, and alerting for the Aura healthcare platform.
