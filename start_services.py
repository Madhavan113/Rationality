#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
import time
import json
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("start_services")

def check_docker_installed():
    """Check if Docker is installed and running."""
    try:
        subprocess.run(
            ["docker", "--version"], 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        logger.info("✅ Docker is installed")
        
        # Additional check to verify Docker daemon is running
        result = subprocess.run(
            ["docker", "info"], 
            check=True,
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE
        )
        logger.info("✅ Docker daemon is running")
        return True
    except subprocess.CalledProcessError as e:
        if e.returncode != 0 and "Cannot connect to the Docker daemon" in (e.stderr.decode() if hasattr(e, 'stderr') else ""):
            logger.error("❌ Docker is installed but the daemon is not running. Please start Docker Desktop.")
        else:
            logger.error(f"❌ Docker error: {e.stderr.decode() if hasattr(e, 'stderr') else str(e)}")
        return False
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("❌ Docker is not installed or not in PATH")
        return False

def check_env_file():
    """Check if .env file exists with required variables."""
    env_path = Path(".env")
    
    if not env_path.exists():
        logger.warning("⚠️ .env file not found. Creating a template...")
        with open(env_path, "w") as f:
            f.write("# Supabase Configuration\n")
            f.write("SUPABASE_DB_URL=your_supabase_connection_string\n")
            f.write("SUPABASE_ANON_KEY=your_supabase_anon_key\n")
            f.write("SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key\n")
        
        logger.error("❌ Please edit the .env file with your Supabase credentials")
        return False
    
    # Check if .env file contains the required variables
    with open(env_path, "r") as f:
        env_content = f.read()
        
    required_vars = ["SUPABASE_DB_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if var not in env_content or f"{var}=your_" in env_content:
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing or invalid environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("✅ .env file exists with required variables")
    return True

def start_services():
    """Start all services using Docker Compose."""
    try:
        # Check if services are already running
        result = subprocess.run(
            ["docker-compose", "ps", "--services", "--filter", "status=running"],
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        
        running_services = result.stdout.strip().split('\n')
        if running_services and running_services[0]:  # Check if list is not empty and not just an empty string
            running_services_str = ", ".join(running_services)
            logger.info(f"ℹ️ Services already running: {running_services_str}")
            
            # Ask to restart
            restart = input("Do you want to restart all services? (y/N): ").lower()
            if restart == 'y':
                logger.info("🔄 Stopping all services...")
                subprocess.run(["docker-compose", "down"], check=True)
            else:
                return running_services
        
        # Start all services
        logger.info("🚀 Starting all services...")
        subprocess.run(["docker-compose", "up", "-d"], check=True)
        
        # Check which services started successfully
        time.sleep(5)  # Give services time to start
        result = subprocess.run(
            ["docker-compose", "ps", "--services", "--filter", "status=running"],
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        
        running_services = [s for s in result.stdout.strip().split('\n') if s]
        if running_services:
            logger.info(f"✅ Services started: {', '.join(running_services)}")
            return running_services
        else:
            logger.error("❌ No services started successfully")
            return []
            
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Error starting services: {e}")
        return []

def wait_for_services_ready(services, timeout=60):
    """Wait for services to be ready by checking their health endpoints."""
    import requests
    
    service_ports = {
        "ingestion": 8001,
        "aggregator": 8002,
        "leaderboard": 8003,
        "alerts": 8004,
        "rationality": 8005,
        "frontend": 3000
    }
    
    ready_services = set()
    start_time = time.time()
    
    logger.info(f"⏱️ Waiting up to {timeout} seconds for services to be ready...")
    
    while time.time() - start_time < timeout:
        for service in services:
            if service in ready_services or service == "mailhog" or service not in service_ports:
                continue
                
            port = service_ports.get(service)
            if not port:
                continue
                
            try:
                # For backend services, check health endpoint
                if service != "frontend":
                    url = f"http://localhost:{port}/health"
                else:
                    # For frontend, just check if the server responds
                    url = f"http://localhost:{port}/"
                
                response = requests.get(url, timeout=2)
                
                if response.status_code == 200:
                    logger.info(f"✅ Service {service} is ready on port {port}")
                    ready_services.add(service)
            except requests.RequestException:
                # Service not ready yet
                pass
        
        if len(ready_services) == len([s for s in services if s != "mailhog"]):
            logger.info("✅ All services are ready!")
            break
            
        time.sleep(2)
    
    # Report services that are not ready
    not_ready = [s for s in services if s != "mailhog" and s not in ready_services]
    if not_ready:
        logger.warning(f"⚠️ Services not responding: {', '.join(not_ready)}")
    
    return list(ready_services)

def run_smoke_test():
    """Run the smoke test to verify all services."""
    logger.info("🧪 Running smoke test...")
    
    try:
        result = subprocess.run(
            ["python", "smoke_test.py"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        logger.info("✅ Smoke test completed successfully")
        print(result.stdout)
        return True
    except subprocess.SubprocessError as e:
        logger.error(f"❌ Smoke test failed: {e}")
        print(e.stderr if hasattr(e, 'stderr') else "Unknown error")
        return False

def main():
    """Main function to start all services and run the smoke test."""
    logger.info("🔍 Starting Polymarket-diagnostics SaaS...")
    
    # Check prerequisites
    if not check_docker_installed():
        return 1
    
    if not check_env_file():
        return 1
    
    # Start services
    running_services = start_services()
    if not running_services:
        return 1
    
    # Wait for services to be ready
    ready_services = wait_for_services_ready(running_services)
    
    # Ask if user wants to run the smoke test
    run_test = input("Do you want to run the smoke test now? (Y/n): ").lower()
    if run_test != 'n':
        success = run_smoke_test()
        return 0 if success else 1
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        sys.exit(1)