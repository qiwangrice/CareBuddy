#!/bin/bash

# CareBuddy Neo4j Management Script
# Provides easy commands to start, stop, and manage Neo4j container

set -e

COLOR_GREEN='\033[0;32m'
COLOR_BLUE='\033[0;34m'
COLOR_RED='\033[0;31m'
COLOR_YELLOW='\033[1;33m'
NC='\033[0m' # No Color

COMPOSE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"

# Show a section header
print_header() {
    echo -e "\n${COLOR_BLUE}══════════════════════════════════════${NC}"
    echo -e "${COLOR_BLUE}$1${NC}"
    echo -e "${COLOR_BLUE}══════════════════════════════════════${NC}\n"
}

# Show success message
print_success() {
    echo -e "${COLOR_GREEN}✓ $1${NC}"
}

# Show info message
print_info() {
    echo -e "${COLOR_BLUE}ℹ $1${NC}"
}

# Show warning message
print_warning() {
    echo -e "${COLOR_YELLOW}⚠ $1${NC}"
}

# Show error message
print_error() {
    echo -e "${COLOR_RED}✗ $1${NC}"
}

# Start Neo4j
start_neo4j() {
    print_header "Starting Neo4j"
    
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "docker-compose.yml not found at $COMPOSE_DIR"
        exit 1
    fi
    
    cd "$COMPOSE_DIR"
    docker-compose up -d neo4j
    
    print_success "Neo4j container started"
    
    # Wait for Neo4j to be ready
    print_info "Waiting for Neo4j to be ready..."
    sleep 5
    
    # Check health
    if docker-compose ps | grep -q "neo4j.*healthy"; then
        print_success "Neo4j is healthy and ready!"
        print_info "Browser: http://localhost:7474"
        print_info "Bolt: bolt://localhost:7687"
        print_info "Username: neo4j"
        print_info "Password: carebuddy_password"
    else
        print_warning "Neo4j started but still initializing. Check status with: ./neo4j.sh status"
    fi
}

# Stop Neo4j
stop_neo4j() {
    print_header "Stopping Neo4j"
    
    cd "$COMPOSE_DIR"
    docker-compose down
    
    print_success "Neo4j container stopped"
}

# Restart Neo4j
restart_neo4j() {
    print_header "Restarting Neo4j"
    stop_neo4j
    sleep 2
    start_neo4j
}

# Show Neo4j status
status_neo4j() {
    print_header "Neo4j Status"
    
    cd "$COMPOSE_DIR"
    docker-compose ps neo4j
    
    echo ""
    if docker ps | grep -q carebuddy-neo4j; then
        print_success "Neo4j container is running"
        
        # Get container info
        CONTAINER_ID=$(docker ps --filter "name=carebuddy-neo4j" -q)
        echo ""
        print_info "Container ID: $CONTAINER_ID"
        
        # Try to get health status
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' "$CONTAINER_ID" 2>/dev/null || echo "unknown")
        print_info "Health Status: $HEALTH"
    else
        print_warning "Neo4j container is not running"
    fi
}

# View logs
logs_neo4j() {
    print_header "Neo4j Logs"
    
    cd "$COMPOSE_DIR"
    docker-compose logs -f neo4j
}

# Remove data and start fresh
reset_neo4j() {
    print_header "Reset Neo4j (Full Wipe)"
    print_warning "This will delete all Neo4j data!"
    read -p "Are you sure? (yes/no): " -r
    
    if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        cd "$COMPOSE_DIR"
        docker-compose down -v
        print_success "Neo4j data removed"
        
        # Restart
        docker-compose up -d neo4j
        print_success "Neo4j restarted with clean data"
    else
        print_info "Reset cancelled"
    fi
}

# Open browser
open_browser() {
    print_info "Opening Neo4j Browser at http://localhost:7474"
    
    if command -v open &> /dev/null; then
        open http://localhost:7474
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:7474
    else
        print_warning "Please open http://localhost:7474 manually"
    fi
}

# Show help
show_help() {
    print_header "CareBuddy Neo4j Management"
    
    cat << 'EOF'
Usage: ./neo4j.sh [command]

Commands:
  start        Start Neo4j container
  stop         Stop Neo4j container
  restart      Restart Neo4j container
  status       Show Neo4j status
  logs         Show Neo4j logs (follow mode)
  reset        Reset Neo4j (wipe all data)
  open         Open Neo4j Browser
  help         Show this help message

Examples:
  ./neo4j.sh start           # Start Neo4j
  ./neo4j.sh status          # Check if running
  ./neo4j.sh logs            # View logs
  ./neo4j.sh reset           # Full wipe and restart

Connection Details:
  Browser URL: http://localhost:7474
  Bolt URI:    bolt://localhost:7687
  Username:    neo4j
  Password:    carebuddy_password

EOF
}

# Main command handler
case "${1:-help}" in
    start)
        start_neo4j
        ;;
    stop)
        stop_neo4j
        ;;
    restart)
        restart_neo4j
        ;;
    status)
        status_neo4j
        ;;
    logs)
        logs_neo4j
        ;;
    reset)
        reset_neo4j
        ;;
    open)
        open_browser
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
