#!/bin/bash
# =============================================================================
# startup.sh - Universal Startup Script with Comprehensive Error Handling
# =============================================================================
#
# A robust startup script template that provides:
# - Environment validation and setup
# - Dependency checking (Node.js, npm, Docker, etc.)
# - Service health checks with configurable retries
# - Graceful signal handling and cleanup
# - Cross-platform compatibility (macOS, Linux, Windows/Git Bash)
# - Logging with timestamps and log levels
#
# Usage:
#   ./scripts/startup.sh [options] <command>
#
# Options:
#   --help              Show this help message
#   --env-file FILE     Load environment from FILE (default: .env)
#   --check-deps        Check all dependencies before starting
#   --check-node        Check Node.js is installed
#   --check-docker      Check Docker is installed and running
#   --check-port PORT   Check if PORT is available
#   --wait-for URL      Wait for URL to become available
#   --timeout SECONDS   Timeout for health checks (default: 60)
#   --retries N         Number of retry attempts (default: 30)
#   --quiet             Suppress non-error output
#   --no-colors         Disable colored output
#
# Examples:
#   ./scripts/startup.sh --check-node --check-port 3000 npm start
#   ./scripts/startup.sh --wait-for http://localhost:3000/health npm test
#   ./scripts/startup.sh --check-docker docker compose up
#
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================

SCRIPT_NAME="$(basename "$0")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default settings
ENV_FILE=".env"
TIMEOUT=60
RETRIES=30
QUIET=false
NO_COLORS=false
CHECK_DEPS=false
CHECK_NODE=false
CHECK_DOCKER=false
CHECK_PORTS=()
WAIT_FOR_URLS=()

# Exit codes
EXIT_SUCCESS=0
EXIT_GENERAL_ERROR=1
EXIT_MISSING_DEPENDENCY=2
EXIT_PORT_IN_USE=3
EXIT_HEALTH_CHECK_FAILED=4
EXIT_TIMEOUT=5
EXIT_INVALID_ARGS=6

# =============================================================================
# Color Setup
# =============================================================================

setup_colors() {
    if [[ "$NO_COLORS" == "true" ]] || [[ ! -t 1 ]]; then
        RED=""
        GREEN=""
        YELLOW=""
        BLUE=""
        CYAN=""
        GRAY=""
        BOLD=""
        RESET=""
    else
        RED="\033[0;31m"
        GREEN="\033[0;32m"
        YELLOW="\033[0;33m"
        BLUE="\033[0;34m"
        CYAN="\033[0;36m"
        GRAY="\033[0;90m"
        BOLD="\033[1m"
        RESET="\033[0m"
    fi
}

# =============================================================================
# Logging Functions
# =============================================================================

timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

log_info() {
    [[ "$QUIET" == "true" ]] && return
    echo -e "${BLUE}[INFO]${RESET} ${GRAY}$(timestamp)${RESET} $*"
}

log_success() {
    [[ "$QUIET" == "true" ]] && return
    echo -e "${GREEN}[OK]${RESET}   ${GRAY}$(timestamp)${RESET} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${RESET} ${GRAY}$(timestamp)${RESET} $*" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${RESET} ${GRAY}$(timestamp)${RESET} $*" >&2
}

log_debug() {
    [[ "$QUIET" == "true" ]] && return
    [[ -z "${DEBUG:-}" ]] && return
    echo -e "${GRAY}[DEBUG] $(timestamp) $*${RESET}"
}

# =============================================================================
# Platform Detection
# =============================================================================

detect_platform() {
    case "$OSTYPE" in
        darwin*)
            PLATFORM="macos"
            ;;
        linux*)
            PLATFORM="linux"
            ;;
        msys*|cygwin*|mingw*)
            PLATFORM="windows"
            ;;
        *)
            PLATFORM="unknown"
            ;;
    esac
    log_debug "Detected platform: $PLATFORM"
}

# =============================================================================
# Cleanup & Signal Handling
# =============================================================================

# Track background processes for cleanup
declare -a CHILD_PIDS=()

cleanup() {
    local exit_code=$?
    log_debug "Cleanup triggered with exit code: $exit_code"

    # Kill any tracked child processes
    for pid in "${CHILD_PIDS[@]:-}"; do
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            log_debug "Killing child process: $pid"
            kill -TERM "$pid" 2>/dev/null || true
            # Give it a moment to terminate gracefully
            sleep 0.5 2>/dev/null || sleep 1
            # Force kill if still running
            kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
        fi
    done

    exit "$exit_code"
}

setup_signal_handlers() {
    trap cleanup EXIT
    trap 'log_debug "Received SIGINT"; exit 130' INT
    trap 'log_debug "Received SIGTERM"; exit 143' TERM
    trap 'log_debug "Received SIGHUP"; exit 129' HUP
}

# Track a background process for cleanup
track_pid() {
    local pid="$1"
    CHILD_PIDS+=("$pid")
    log_debug "Tracking PID: $pid"
}

# =============================================================================
# Environment Functions
# =============================================================================

load_env_file() {
    local env_file="${1:-$ENV_FILE}"
    local env_path="$PROJECT_ROOT/$env_file"

    if [[ -f "$env_path" ]]; then
        log_debug "Loading environment from: $env_path"
        # Export variables, ignoring comments and empty lines
        set -a
        # shellcheck source=/dev/null
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            [[ -z "$key" || "$key" =~ ^[[:space:]]*# ]] && continue
            # Remove leading/trailing whitespace from key
            key="${key#"${key%%[![:space:]]*}"}"
            key="${key%"${key##*[![:space:]]}"}"
            # Skip if key is empty after trimming
            [[ -z "$key" ]] && continue
            # Export the variable
            export "$key=$value" 2>/dev/null || true
        done < "$env_path"
        set +a
        log_success "Loaded environment from $env_file"
    else
        log_debug "No environment file found at: $env_path"
    fi
}

# =============================================================================
# Dependency Checking
# =============================================================================

command_exists() {
    command -v "$1" &>/dev/null
}

check_node() {
    log_info "Checking Node.js..."

    if ! command_exists node; then
        log_error "Node.js is not installed"
        log_error "Please install Node.js from https://nodejs.org/"
        return $EXIT_MISSING_DEPENDENCY
    fi

    local node_version
    node_version=$(node -v)
    log_success "Node.js $node_version found"

    # Check npm as well
    if ! command_exists npm; then
        log_error "npm is not installed"
        return $EXIT_MISSING_DEPENDENCY
    fi

    local npm_version
    npm_version=$(npm -v)
    log_success "npm v$npm_version found"

    # Check if Node version meets minimum requirements (22+)
    local major_version
    major_version=$(echo "$node_version" | sed 's/v\([0-9]*\).*/\1/')
    if [[ "$major_version" -lt 22 ]]; then
        log_warn "Node.js version $node_version detected, but v22+ is recommended"
    fi

    return $EXIT_SUCCESS
}

check_docker() {
    log_info "Checking Docker..."

    if ! command_exists docker; then
        log_error "Docker is not installed"
        log_error "Please install Docker from https://docs.docker.com/get-docker/"
        return $EXIT_MISSING_DEPENDENCY
    fi

    # Check if Docker daemon is running
    if ! docker info &>/dev/null; then
        log_error "Docker daemon is not running"

        case "$PLATFORM" in
            macos)
                log_error "Please start Docker Desktop"
                ;;
            linux)
                log_error "Try: sudo systemctl start docker"
                log_error "Or if you need to add yourself to the docker group:"
                log_error "  sudo usermod -aG docker \$USER && newgrp docker"
                ;;
            *)
                log_error "Please start the Docker service"
                ;;
        esac

        return $EXIT_MISSING_DEPENDENCY
    fi

    local docker_version
    docker_version=$(docker --version | awk '{print $3}' | tr -d ',')
    log_success "Docker $docker_version found and running"

    # Check docker compose
    if docker compose version &>/dev/null; then
        local compose_version
        compose_version=$(docker compose version --short 2>/dev/null || echo "unknown")
        log_success "Docker Compose v$compose_version found"
    elif command_exists docker-compose; then
        local compose_version
        compose_version=$(docker-compose --version | awk '{print $4}' | tr -d ',')
        log_warn "Using legacy docker-compose v$compose_version (consider upgrading to Docker Compose V2)"
    else
        log_warn "Docker Compose not found (optional)"
    fi

    return $EXIT_SUCCESS
}

check_port_available() {
    local port="$1"
    log_info "Checking port $port availability..."

    # Validate port number
    if ! [[ "$port" =~ ^[0-9]+$ ]] || [[ "$port" -lt 1 ]] || [[ "$port" -gt 65535 ]]; then
        log_error "Invalid port number: $port"
        return $EXIT_INVALID_ARGS
    fi

    local in_use=false
    local pids=""

    # Check if port is in use
    case "$PLATFORM" in
        macos|linux)
            if command_exists lsof; then
                pids=$(lsof -ti:"$port" 2>/dev/null || true)
                [[ -n "$pids" ]] && in_use=true
            elif command_exists netstat; then
                if netstat -tuln 2>/dev/null | grep -q ":$port "; then
                    in_use=true
                fi
            elif command_exists ss; then
                if ss -tuln 2>/dev/null | grep -q ":$port "; then
                    in_use=true
                fi
            fi
            ;;
        windows)
            if netstat -ano 2>/dev/null | grep -q ":$port .*LISTENING"; then
                in_use=true
                pids=$(netstat -ano 2>/dev/null | grep ":$port .*LISTENING" | awk '{print $5}' | head -1)
            fi
            ;;
    esac

    if [[ "$in_use" == "true" ]]; then
        if [[ -n "$pids" ]]; then
            log_error "Port $port is already in use (PID: $pids)"
        else
            log_error "Port $port is already in use"
        fi
        return $EXIT_PORT_IN_USE
    fi

    log_success "Port $port is available"
    return $EXIT_SUCCESS
}

# =============================================================================
# Health Check Functions
# =============================================================================

wait_for_url() {
    local url="$1"
    local timeout="${2:-$TIMEOUT}"
    local retries="${3:-$RETRIES}"

    log_info "Waiting for $url to become available..."
    log_info "Timeout: ${timeout}s, Max retries: $retries"

    local start_time
    start_time=$(date +%s)
    local attempt=0
    local delay=2

    while [[ $attempt -lt $retries ]]; do
        attempt=$((attempt + 1))

        # Check if we've exceeded the timeout
        local current_time
        current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ $elapsed -ge $timeout ]]; then
            log_error "Timeout after ${elapsed}s waiting for $url"
            return $EXIT_TIMEOUT
        fi

        # Try to reach the URL
        if curl --silent --fail --max-time 5 "$url" &>/dev/null; then
            log_success "$url is available (attempt $attempt, ${elapsed}s elapsed)"
            return $EXIT_SUCCESS
        fi

        log_debug "Attempt $attempt/$retries: $url not yet available..."
        sleep "$delay"

        # Exponential backoff with cap
        delay=$((delay < 10 ? delay + 1 : 10))
    done

    log_error "Failed to reach $url after $retries attempts"
    return $EXIT_HEALTH_CHECK_FAILED
}

wait_for_port() {
    local host="${1:-localhost}"
    local port="$2"
    local timeout="${3:-$TIMEOUT}"

    log_info "Waiting for $host:$port to accept connections..."

    local start_time
    start_time=$(date +%s)

    while true; do
        local current_time
        current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ $elapsed -ge $timeout ]]; then
            log_error "Timeout after ${elapsed}s waiting for $host:$port"
            return $EXIT_TIMEOUT
        fi

        # Try to connect
        if (echo >/dev/tcp/"$host"/"$port") 2>/dev/null; then
            log_success "$host:$port is accepting connections (${elapsed}s elapsed)"
            return $EXIT_SUCCESS
        fi

        sleep 1
    done
}

# =============================================================================
# Help & Usage
# =============================================================================

show_help() {
    cat << 'EOF'
startup.sh - Universal Startup Script with Comprehensive Error Handling

USAGE:
    ./scripts/startup.sh [OPTIONS] [--] <command> [args...]

OPTIONS:
    --help              Show this help message
    --env-file FILE     Load environment from FILE (default: .env)
    --check-deps        Check all dependencies (Node.js, npm, Docker)
    --check-node        Check Node.js is installed
    --check-docker      Check Docker is installed and running
    --check-port PORT   Check if PORT is available (can be used multiple times)
    --wait-for URL      Wait for URL to become available (can be used multiple times)
    --timeout SECONDS   Timeout for health checks (default: 60)
    --retries N         Number of retry attempts (default: 30)
    --quiet             Suppress non-error output
    --no-colors         Disable colored output

EXAMPLES:
    # Check Node.js and start a development server
    ./scripts/startup.sh --check-node npm run dev

    # Check port availability before starting
    ./scripts/startup.sh --check-port 3000 --check-port 3001 npm start

    # Wait for a service to be ready before running tests
    ./scripts/startup.sh --wait-for http://localhost:3000/health npm test

    # Full dependency check with Docker
    ./scripts/startup.sh --check-deps --check-docker docker compose up

    # Load custom environment file
    ./scripts/startup.sh --env-file .env.local npm run dev

    # Quiet mode for CI/CD
    ./scripts/startup.sh --quiet --check-node npm test

EXIT CODES:
    0 - Success
    1 - General error
    2 - Missing dependency
    3 - Port in use
    4 - Health check failed
    5 - Timeout
    6 - Invalid arguments

EOF
}

# =============================================================================
# Argument Parsing
# =============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --help|-h)
                show_help
                exit $EXIT_SUCCESS
                ;;
            --env-file)
                if [[ -z "${2:-}" ]]; then
                    log_error "--env-file requires a file path"
                    exit $EXIT_INVALID_ARGS
                fi
                ENV_FILE="$2"
                shift 2
                ;;
            --check-deps)
                CHECK_DEPS=true
                CHECK_NODE=true
                shift
                ;;
            --check-node)
                CHECK_NODE=true
                shift
                ;;
            --check-docker)
                CHECK_DOCKER=true
                shift
                ;;
            --check-port)
                if [[ -z "${2:-}" ]]; then
                    log_error "--check-port requires a port number"
                    exit $EXIT_INVALID_ARGS
                fi
                CHECK_PORTS+=("$2")
                shift 2
                ;;
            --wait-for)
                if [[ -z "${2:-}" ]]; then
                    log_error "--wait-for requires a URL"
                    exit $EXIT_INVALID_ARGS
                fi
                WAIT_FOR_URLS+=("$2")
                shift 2
                ;;
            --timeout)
                if [[ -z "${2:-}" ]]; then
                    log_error "--timeout requires a number"
                    exit $EXIT_INVALID_ARGS
                fi
                TIMEOUT="$2"
                shift 2
                ;;
            --retries)
                if [[ -z "${2:-}" ]]; then
                    log_error "--retries requires a number"
                    exit $EXIT_INVALID_ARGS
                fi
                RETRIES="$2"
                shift 2
                ;;
            --quiet|-q)
                QUIET=true
                shift
                ;;
            --no-colors)
                NO_COLORS=true
                shift
                ;;
            --)
                shift
                COMMAND=("$@")
                break
                ;;
            -*)
                log_error "Unknown option: $1"
                log_error "Use --help for usage information"
                exit $EXIT_INVALID_ARGS
                ;;
            *)
                # First non-option argument starts the command
                COMMAND=("$@")
                break
                ;;
        esac
    done
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    # Initialize
    setup_colors
    setup_signal_handlers
    detect_platform

    # Load environment
    load_env_file "$ENV_FILE"

    # Run dependency checks
    if [[ "$CHECK_NODE" == "true" ]]; then
        check_node
        local node_result=$?
        if [[ $node_result -ne 0 ]]; then
            exit $node_result
        fi
    fi

    if [[ "$CHECK_DOCKER" == "true" ]]; then
        check_docker
        local docker_result=$?
        if [[ $docker_result -ne 0 ]]; then
            exit $docker_result
        fi
    fi

    # Check ports
    for port in "${CHECK_PORTS[@]:-}"; do
        if [[ -n "$port" ]]; then
            check_port_available "$port"
            local port_result=$?
            if [[ $port_result -ne 0 ]]; then
                exit $port_result
            fi
        fi
    done

    # Wait for URLs
    for url in "${WAIT_FOR_URLS[@]:-}"; do
        if [[ -n "$url" ]]; then
            wait_for_url "$url" "$TIMEOUT" "$RETRIES"
            local url_result=$?
            if [[ $url_result -ne 0 ]]; then
                exit $url_result
            fi
        fi
    done

    # Execute command if provided
    if [[ ${#COMMAND[@]} -gt 0 ]]; then
        log_info "Executing: ${COMMAND[*]}"

        # Change to project root
        cd "$PROJECT_ROOT"

        # Execute the command
        exec "${COMMAND[@]}"
    else
        # No command provided - just run checks and exit
        if [[ "$CHECK_NODE" == "true" ]] || [[ "$CHECK_DOCKER" == "true" ]] || \
           [[ ${#CHECK_PORTS[@]} -gt 0 ]] || [[ ${#WAIT_FOR_URLS[@]} -gt 0 ]]; then
            log_success "All checks passed"
        else
            log_warn "No command or checks specified. Use --help for usage."
        fi
    fi
}

# =============================================================================
# Entry Point
# =============================================================================

declare -a COMMAND=()
parse_args "$@"
main
