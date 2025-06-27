#!/bin/bash

# ELK Stack Startup Script for Aura Logging System
# Provides comprehensive initialization and health checking

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
ELK_COMPOSE_FILE="docker-compose.elk.yml"
HEALTH_CHECK_TIMEOUT=300  # 5 minutes
HEALTH_CHECK_INTERVAL=10  # 10 seconds

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if a service is healthy
check_service_health() {
    local service_name=$1
    local health_url=$2
    local expected_status=${3:-200}
    local auth_header=${4:-""}

    print_status "Checking $service_name health..."

    local start_time=$(date +%s)
    local timeout_time=$((start_time + HEALTH_CHECK_TIMEOUT))

    while [ $(date +%s) -lt $timeout_time ]; do
        if [ -n "$auth_header" ]; then
            if curl -s -f -H "$auth_header" "$health_url" > /dev/null 2>&1; then
                print_success "$service_name is healthy"
                return 0
            fi
        else
            if curl -s -f "$health_url" > /dev/null 2>&1; then
                print_success "$service_name is healthy"
                return 0
            fi
        fi

        print_status "Waiting for $service_name to become healthy..."
        sleep $HEALTH_CHECK_INTERVAL
    done

    print_error "$service_name failed to become healthy within $HEALTH_CHECK_TIMEOUT seconds"
    return 1
}

# Function to wait for Elasticsearch to be ready
wait_for_elasticsearch() {
    print_status "Waiting for Elasticsearch to be ready..."

    local start_time=$(date +%s)
    local timeout_time=$((start_time + HEALTH_CHECK_TIMEOUT))

    while [ $(date +%s) -lt $timeout_time ]; do
        if curl -s -u "elastic:aura_elastic_password_2024" "http://localhost:9200/_cluster/health" | grep -q '"status":"green\|yellow"'; then
            print_success "Elasticsearch cluster is ready"
            return 0
        fi

        print_status "Waiting for Elasticsearch cluster..."
        sleep $HEALTH_CHECK_INTERVAL
    done

    print_error "Elasticsearch cluster failed to become ready"
    return 1
}

# Function to setup ELK stack
setup_elk_stack() {
    print_status "Setting up ELK stack configuration..."

    # Wait a bit more for services to fully initialize
    sleep 30

    # Run Django management command to setup ELK
    if command -v python >/dev/null 2>&1; then
        print_status "Running ELK setup via Django management command..."
        python manage.py elk_admin setup --force || {
            print_warning "Django ELK setup failed, continuing with manual setup..."
        }
    fi

    # Manual setup using curl commands
    print_status "Creating index templates..."

    # Create index template
    curl -s -X PUT "http://localhost:9200/_index_template/aura-logs-template" \
        -u "elastic:aura_elastic_password_2024" \
        -H "Content-Type: application/json" \
        -d @elk/logstash/templates/aura-logs-template.json || {
        print_warning "Failed to create index template via curl"
    }

    # Create ILM policy
    print_status "Creating ILM policy..."
    curl -s -X PUT "http://localhost:9200/_ilm/policy/aura-logs-policy" \
        -u "elastic:aura_elastic_password_2024" \
        -H "Content-Type: application/json" \
        -d '{
            "policy": {
                "phases": {
                    "hot": {
                        "actions": {
                            "rollover": {
                                "max_size": "5GB",
                                "max_age": "1d"
                            }
                        }
                    },
                    "warm": {
                        "min_age": "7d",
                        "actions": {
                            "allocate": {
                                "number_of_replicas": 0
                            },
                            "forcemerge": {
                                "max_num_segments": 1
                            }
                        }
                    },
                    "delete": {
                        "min_age": "90d"
                    }
                }
            }
        }' || {
        print_warning "Failed to create ILM policy"
    }

    print_success "ELK stack setup completed"
}

# Function to show ELK stack status
show_elk_status() {
    echo
    print_status "=== ELK Stack Status ==="
    echo

    # Elasticsearch
    echo -n "Elasticsearch: "
    if curl -s -f -u "elastic:aura_elastic_password_2024" "http://localhost:9200/_cluster/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"

        # Get cluster info
        cluster_info=$(curl -s -u "elastic:aura_elastic_password_2024" "http://localhost:9200/_cluster/health")
        status=$(echo $cluster_info | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        nodes=$(echo $cluster_info | grep -o '"number_of_nodes":[0-9]*' | cut -d':' -f2)
        echo "  Status: $status, Nodes: $nodes"
    else
        echo -e "${RED}✗ Not responding${NC}"
    fi

    # Logstash
    echo -n "Logstash: "
    if curl -s -f "http://localhost:9600" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not responding${NC}"
    fi

    # Kibana
    echo -n "Kibana: "
    if curl -s -f -u "elastic:aura_elastic_password_2024" "http://localhost:5601/api/status" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not responding${NC}"
    fi

    # Filebeat
    echo -n "Filebeat: "
    if curl -s -f "http://localhost:5066" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not responding${NC}"
    fi

    # Metricbeat
    echo -n "Metricbeat: "
    if curl -s -f "http://localhost:5067" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Running${NC}"
    else
        echo -e "${RED}✗ Not responding${NC}"
    fi

    echo
    print_status "Access URLs:"
    echo "  Elasticsearch: http://localhost:9200"
    echo "  Kibana: http://localhost:5601"
    echo "  Logstash: http://localhost:9600"
    echo "  Elasticsearch Head: http://localhost:9100"
    echo
    print_status "Default credentials:"
    echo "  Username: elastic"
    echo "  Password: aura_elastic_password_2024"
    echo
}

# Function to create logs directory
create_logs_directory() {
    if [ ! -d "logs" ]; then
        print_status "Creating logs directory..."
        mkdir -p logs
        chmod 755 logs
        print_success "Logs directory created"
    fi
}

# Function to check system requirements
check_requirements() {
    print_status "Checking system requirements..."

    # Check if Docker is installed and running
    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker is not installed"
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running"
        exit 1
    fi

    # Check if Docker Compose is available
    if ! command -v docker-compose >/dev/null 2>&1 && ! docker compose version >/dev/null 2>&1; then
        print_error "Docker Compose is not available"
        exit 1
    fi

    # Check available memory (Elasticsearch needs at least 2GB)
    available_memory=$(free -m | awk 'NR==2{printf "%.0f", $7}')
    if [ "$available_memory" -lt 2048 ]; then
        print_warning "Available memory is less than 2GB. Elasticsearch may not start properly."
    fi

    # Check if ports are available
    for port in 9200 5601 9600 5044 5066 5067; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            print_warning "Port $port is already in use"
        fi
    done

    print_success "System requirements check completed"
}

# Function to set vm.max_map_count for Elasticsearch
set_vm_max_map_count() {
    current_max_map_count=$(cat /proc/sys/vm/max_map_count 2>/dev/null || echo "0")
    required_max_map_count=262144

    if [ "$current_max_map_count" -lt "$required_max_map_count" ]; then
        print_status "Setting vm.max_map_count for Elasticsearch..."

        if [ "$EUID" -eq 0 ]; then
            echo "vm.max_map_count=$required_max_map_count" >> /etc/sysctl.conf
            sysctl -w vm.max_map_count=$required_max_map_count
            print_success "vm.max_map_count set to $required_max_map_count"
        else
            print_warning "Cannot set vm.max_map_count. Run as root or execute:"
            print_warning "sudo sysctl -w vm.max_map_count=$required_max_map_count"
        fi
    fi
}

# Main execution
main() {
    echo "🚀 Starting Aura ELK Stack..."
    echo

    # Check if compose file exists
    if [ ! -f "$ELK_COMPOSE_FILE" ]; then
        print_error "Docker Compose file $ELK_COMPOSE_FILE not found"
        exit 1
    fi

    # Check system requirements
    check_requirements

    # Set vm.max_map_count if needed
    set_vm_max_map_count

    # Create logs directory
    create_logs_directory

    # Start ELK stack
    print_status "Starting ELK stack containers..."

    # Use docker-compose or docker compose based on availability
    if command -v docker-compose >/dev/null 2>&1; then
        COMPOSE_CMD="docker-compose"
    else
        COMPOSE_CMD="docker compose"
    fi

    $COMPOSE_CMD -f $ELK_COMPOSE_FILE up -d

    print_success "ELK stack containers started"

    # Wait for services to be healthy
    print_status "Waiting for services to become healthy..."

    # Wait for Elasticsearch
    if ! wait_for_elasticsearch; then
        print_error "Elasticsearch failed to start properly"
        exit 1
    fi

    # Check other services
    check_service_health "Logstash" "http://localhost:9600" 200
    check_service_health "Kibana" "http://localhost:5601/api/status" 200 "Authorization: Basic $(echo -n 'elastic:aura_elastic_password_2024' | base64)"

    # Setup ELK stack
    setup_elk_stack

    # Show final status
    show_elk_status

    print_success "🎉 ELK stack is ready!"
    echo
    print_status "Next steps:"
    echo "  1. Configure your Django application to use the ELK stack"
    echo "  2. Access Kibana at http://localhost:5601"
    echo "  3. Create index patterns and dashboards"
    echo "  4. Monitor your logs in real-time"
    echo
    print_status "To stop the ELK stack, run:"
    echo "  $COMPOSE_CMD -f $ELK_COMPOSE_FILE down"
    echo
}

# Handle script arguments
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        print_status "Stopping ELK stack..."
        if command -v docker-compose >/dev/null 2>&1; then
            docker-compose -f $ELK_COMPOSE_FILE down
        else
            docker compose -f $ELK_COMPOSE_FILE down
        fi
        print_success "ELK stack stopped"
        ;;
    restart)
        $0 stop
        sleep 5
        $0 start
        ;;
    status)
        show_elk_status
        ;;
    logs)
        service=${2:-""}
        if [ -n "$service" ]; then
            if command -v docker-compose >/dev/null 2>&1; then
                docker-compose -f $ELK_COMPOSE_FILE logs -f $service
            else
                docker compose -f $ELK_COMPOSE_FILE logs -f $service
            fi
        else
            if command -v docker-compose >/dev/null 2>&1; then
                docker-compose -f $ELK_COMPOSE_FILE logs -f
            else
                docker compose -f $ELK_COMPOSE_FILE logs -f
            fi
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [service]}"
        echo "  start   - Start the ELK stack"
        echo "  stop    - Stop the ELK stack"
        echo "  restart - Restart the ELK stack"
        echo "  status  - Show ELK stack status"
        echo "  logs    - Show logs (optionally for specific service)"
        exit 1
        ;;
esac
