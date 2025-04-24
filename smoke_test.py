#!/usr/bin/env python3
import sys
import os
import json
import logging
import asyncio
import time
import uuid
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("smoke_test")

# Add backend directory to path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_dir)

# Import test modules
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": []
}

def log_test_result(test_name, passed, message="", details=None):
    """Record test result in the global results dict and log it."""
    result = {
        "name": test_name,
        "passed": passed,
        "message": message
    }
    
    if details:
        result["details"] = details
        
    test_results["tests"].append(result)
    
    if passed:
        logger.info(f"✅ {test_name}: {message}")
    else:
        logger.error(f"❌ {test_name}: {message}")

async def test_database_connection():
    """Test database connectivity."""
    test_name = "Database Connectivity"
    
    try:
        from backend.common.config import get_settings
        from backend.common.db import SessionLocal
        from sqlalchemy import text
        
        # Test connection settings
        settings = get_settings()
        if not settings.supabase_db_url:
            log_test_result(test_name, False, "Database URL not configured")
            return False
        
        # Test actual database connection
        try:
            db = SessionLocal()
            try:
                result = db.execute(text("SELECT 1"))
                if result.scalar() == 1:
                    log_test_result(test_name, True, "Successfully connected to database")
                    
                    # Check tables
                    tables = ["markets", "market_snapshots", "true_prices",
                             "traders", "trader_scores", "alert_rules", 
                             "alert_notifications"]
                    
                    tables_exist = True
                    missing_tables = []
                    
                    for table in tables:
                        result = db.execute(
                            text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                        )
                        exists = result.scalar()
                        if not exists:
                            tables_exist = False
                            missing_tables.append(table)
                    
                    if tables_exist:
                        log_test_result("Database Schema", True, "All required tables exist")
                    else:
                        log_test_result("Database Schema", False, 
                                       f"Missing tables: {', '.join(missing_tables)}")
                    
                    return True
                else:
                    log_test_result(test_name, False, "Database query returned unexpected result")
                    return False
            finally:
                db.close()
        except Exception as e:
            log_test_result(test_name, False, f"Failed to connect to database: {str(e)}")
            return False
            
    except ImportError as e:
        log_test_result(test_name, False, f"Import error: {str(e)}")
        return False
    except Exception as e:
        log_test_result(test_name, False, f"Unexpected error: {str(e)}")
        return False

async def test_api_health_endpoints():
    """Test health check endpoints of all services."""
    import httpx
    
    services = [
        {"name": "Ingestion Service", "port": 8001},
        {"name": "Aggregator Service", "port": 8002},
        {"name": "Leaderboard Service", "port": 8003},
        {"name": "Alerts Service", "port": 8004},
        {"name": "Rationality Service", "port": 8005}
    ]
    
    all_passed = True
    
    for service in services:
        service_name = service["name"]
        port = service["port"]
        test_name = f"{service_name} Health Check"
        
        try:
            url = f"http://localhost:{port}/health"
            logger.info(f"Testing connection to {url}...")
            
            # Add more detailed connection debugging
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    logger.info(f"Sending GET request to {url}...")
                    response = await client.get(url)
                    
                    logger.info(f"Received response with status code: {response.status_code}")
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("status") == "healthy":
                            log_test_result(test_name, True, "Health check passed")
                        else:
                            log_test_result(test_name, False, f"Unexpected health status: {data}")
                            all_passed = False
                    else:
                        response_text = response.text
                        log_test_result(test_name, False, 
                                      f"Health check failed with status code: {response.status_code}, Response: {response_text[:100]}")
                        all_passed = False
            except httpx.ConnectError as e:
                logger.error(f"Connection error to {url}: {str(e)}")
                log_test_result(test_name, False, f"Connection refused to {url}. Is the service running and binding to the correct interface?")
                all_passed = False
            except httpx.ConnectTimeout as e:
                logger.error(f"Connection timeout to {url}: {str(e)}")
                log_test_result(test_name, False, f"Connection timed out to {url}. The service might be running but not responding.")
                all_passed = False
        except httpx.RequestError as e:
            logger.error(f"Request error to {url}: {str(e)}")
            log_test_result(test_name, False, f"Request error: {str(e)}")
            all_passed = False
        except Exception as e:
            logger.error(f"Unexpected error testing {url}: {str(e)}", exc_info=True)
            log_test_result(test_name, False, f"Unexpected error: {str(e)}")
            all_passed = False
    
    return all_passed

async def test_market_endpoints():
    """Test market-related API endpoints."""
    import httpx
    
    test_name = "Market API Endpoints"
    market_id = None
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 1. Get markets
            markets_url = "http://localhost:8001/api/markets"
            response = await client.get(markets_url)
            
            if response.status_code == 200:
                markets_data = response.json()
                log_test_result("Get Markets", True, f"Found {len(markets_data)} markets")
                
                # If there are markets, use the first one for further tests
                if markets_data:
                    market_id = markets_data[0]["id"]
                
                # 2. Create a new test market
                if not market_id:
                    test_market_name = f"Test Market {uuid.uuid4()}"
                    create_market_url = "http://localhost:8001/api/markets"
                    response = await client.post(
                        create_market_url, 
                        params={"name": test_market_name, "description": "Test market for smoke test"}
                    )
                    
                    if response.status_code == 200:
                        market_data = response.json()
                        market_id = market_data["id"]
                        log_test_result("Create Market", True, f"Created test market: {market_id}")
                    else:
                        log_test_result("Create Market", False, 
                                     f"Failed with status code: {response.status_code}, {response.text}")
                        return False
                
                # 3. Test true price endpoint if we have a market
                if market_id:
                    true_price_url = f"http://localhost:8002/api/true-price/{market_id}"
                    try:
                        response = await client.get(true_price_url)
                        
                        if response.status_code == 200:
                            price_data = response.json()
                            log_test_result("Get True Price", True, 
                                         f"Retrieved true price: {price_data.get('value')}")
                        elif response.status_code == 404:
                            log_test_result("Get True Price", True, 
                                         "No true price data yet (404 is expected for new markets)")
                        else:
                            log_test_result("Get True Price", False, 
                                         f"Failed with status code: {response.status_code}")
                    except httpx.RequestError as e:
                        log_test_result("Get True Price", False, f"Request error: {str(e)}")
                
                # 4. Test leaderboard endpoint
                if market_id:
                    leaderboard_url = f"http://localhost:8003/api/leaderboard/{market_id}"
                    try:
                        response = await client.get(leaderboard_url)
                        
                        if response.status_code == 200:
                            leaderboard_data = response.json()
                            log_test_result("Get Leaderboard", True, 
                                          f"Retrieved leaderboard with {len(leaderboard_data.get('entries', []))} entries")
                        elif response.status_code == 404:
                            log_test_result("Get Leaderboard", True, 
                                         "No leaderboard data yet (404 is expected for new markets)")
                        else:
                            log_test_result("Get Leaderboard", False, 
                                         f"Failed with status code: {response.status_code}")
                    except httpx.RequestError as e:
                        log_test_result("Get Leaderboard", False, f"Request error: {str(e)}")
                
                return True
            else:
                log_test_result("Get Markets", False, 
                             f"Failed with status code: {response.status_code}, {response.text}")
                return False
                
        except httpx.RequestError as e:
            log_test_result(test_name, False, f"Request error: {str(e)}")
            return False
        except Exception as e:
            log_test_result(test_name, False, f"Unexpected error: {str(e)}")
            return False

async def test_alert_endpoints():
    """Test alert-related API endpoints."""
    import httpx
    import random
    
    test_name = "Alert API Endpoints"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # 1. Get existing markets to use for alert testing
            markets_url = "http://localhost:8001/api/markets"
            response = await client.get(markets_url)
            
            if response.status_code != 200 or not response.json():
                log_test_result("Get Markets for Alert Test", False, 
                             "No markets available for alert testing")
                return False
            
            markets = response.json()
            market_id = markets[0]["id"]
            
            # 2. Test get alerts endpoint
            alerts_url = "http://localhost:8004/api/alerts"
            response = await client.get(alerts_url)
            
            if response.status_code == 200:
                existing_alerts = response.json()
                log_test_result("Get Alerts", True, 
                             f"Retrieved {len(existing_alerts)} existing alerts")
            else:
                log_test_result("Get Alerts", False, 
                             f"Failed with status code: {response.status_code}")
                return False
            
            # 3. Create a test alert
            test_alert = {
                "name": f"Test Alert {random.randint(1000, 9999)}",
                "market_id": market_id,
                "email": "test@example.com",
                "threshold": 0.05,  # 5% threshold
                "condition": "above"
            }
            
            response = await client.post(alerts_url, json=test_alert)
            
            if response.status_code == 200:
                created_alert = response.json()
                alert_id = created_alert["id"]
                log_test_result("Create Alert", True, f"Created test alert with ID: {alert_id}")
                
                # 4. Delete the test alert
                delete_url = f"http://localhost:8004/api/alerts/{alert_id}"
                response = await client.delete(delete_url)
                
                if response.status_code == 204:
                    log_test_result("Delete Alert", True, f"Deleted test alert: {alert_id}")
                else:
                    log_test_result("Delete Alert", False, 
                                 f"Failed with status code: {response.status_code}")
            else:
                log_test_result("Create Alert", False, 
                             f"Failed with status code: {response.status_code}, {response.text}")
                
            return True
            
        except httpx.RequestError as e:
            log_test_result(test_name, False, f"Request error: {str(e)}")
            return False
        except Exception as e:
            log_test_result(test_name, False, f"Unexpected error: {str(e)}")
            return False

async def main():
    test_suite = [
        ("Database Connection Test", test_database_connection),
        ("API Health Endpoints Test", test_api_health_endpoints),
        ("Market Endpoints Test", test_market_endpoints),
        ("Alert Endpoints Test", test_alert_endpoints)
    ]
    
    logger.info("Starting Polymarket Monitor smoke tests...")
    overall_start_time = time.time()
    
    for test_description, test_func in test_suite:
        logger.info(f"\n--- Running {test_description} ---")
        start_time = time.time()
        await test_func()
        elapsed = time.time() - start_time
        logger.info(f"--- Completed {test_description} in {elapsed:.2f}s ---")
    
    # Calculate overall statistics
    total_tests = len(test_results["tests"])
    passed_tests = sum(1 for test in test_results["tests"] if test["passed"])
    failed_tests = total_tests - passed_tests
    
    test_results["summary"] = {
        "total": total_tests,
        "passed": passed_tests,
        "failed": failed_tests,
        "success_rate": f"{(passed_tests / total_tests * 100):.1f}%" if total_tests > 0 else "0%",
        "total_time": f"{time.time() - overall_start_time:.2f}s"
    }
    
    # Output final results
    print("\n" + "=" * 50)
    print("SMOKE TEST RESULTS SUMMARY")
    print("=" * 50)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Success Rate: {test_results['summary']['success_rate']}")
    print(f"Total Time: {test_results['summary']['total_time']}")
    print("=" * 50)
    
    # Output detailed JSON results
    with open("smoke_test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\nDetailed results saved to smoke_test_results.json")
    
    # Return appropriate exit code
    return 0 if failed_tests == 0 else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        logger.error(f"Critical error in smoke test: {e}", exc_info=True)
        sys.exit(1)