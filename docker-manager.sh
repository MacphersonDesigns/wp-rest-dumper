#!/bin/bash

# WordPress REST Dumper - Quick Start Script
# This script helps you easily manage the Docker service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}🐳 WordPress REST Dumper - Docker Manager${NC}"
    echo "================================================="
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        echo "Please install Docker Desktop and try again."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running"
        echo "Please start Docker Desktop and try again."
        exit 1
    fi
}

# Main menu
show_menu() {
    echo -e "\nWhat would you like to do?"
    echo "1) Start the service"
    echo "2) Stop the service"
    echo "3) Restart the service"
    echo "4) View logs"
    echo "5) Check status"
    echo "6) Open web interface"
    echo "7) Update and rebuild"
    echo "8) Complete cleanup"
    echo "9) Exit"
}

# Service functions
start_service() {
    print_info "Starting WordPress REST Dumper..."
    docker-compose up -d
    print_success "Service started! Web interface available at: http://localhost:8080"
}

stop_service() {
    print_info "Stopping WordPress REST Dumper..."
    docker-compose down
    print_success "Service stopped"
}

restart_service() {
    print_info "Restarting WordPress REST Dumper..."
    docker-compose restart
    print_success "Service restarted"
}

view_logs() {
    print_info "Showing service logs (Press Ctrl+C to exit)..."
    docker-compose logs -f wp-dumper
}

check_status() {
    print_info "Service status:"
    docker-compose ps
}

open_browser() {
    print_info "Opening web interface..."
    if command -v open &> /dev/null; then
        # macOS
        open http://localhost:8080
    elif command -v xdg-open &> /dev/null; then
        # Linux
        xdg-open http://localhost:8080
    elif command -v start &> /dev/null; then
        # Windows
        start http://localhost:8080
    else
        print_info "Please open http://localhost:8080 in your browser"
    fi
}

update_rebuild() {
    print_info "Updating from Git and rebuilding..."
    git pull origin main
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    print_success "Updated and rebuilt successfully!"
}

cleanup() {
    print_warning "This will remove all containers and images. Continue? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        docker-compose down -v --rmi all
        print_success "Complete cleanup done"
    else
        print_info "Cleanup cancelled"
    fi
}

# Main script
main() {
    print_header
    check_docker

    if [ $# -eq 0 ]; then
        # Interactive mode
        while true; do
            show_menu
            echo -n "Enter your choice (1-9): "
            read -r choice
            
            case $choice in
                1) start_service ;;
                2) stop_service ;;
                3) restart_service ;;
                4) view_logs ;;
                5) check_status ;;
                6) open_browser ;;
                7) update_rebuild ;;
                8) cleanup ;;
                9) echo "Goodbye!"; exit 0 ;;
                *) print_error "Invalid option. Please choose 1-9." ;;
            esac
            
            echo -e "\nPress Enter to continue..."
            read -r
        done
    else
        # Command line mode
        case "$1" in
            start) start_service ;;
            stop) stop_service ;;
            restart) restart_service ;;
            logs) view_logs ;;
            status) check_status ;;
            open) open_browser ;;
            update) update_rebuild ;;
            cleanup) cleanup ;;
            *)
                echo "Usage: $0 [start|stop|restart|logs|status|open|update|cleanup]"
                echo "Run without arguments for interactive mode"
                exit 1
                ;;
        esac
    fi
}

# Run the script
main "$@"