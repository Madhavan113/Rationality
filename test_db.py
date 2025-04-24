#!/usr/bin/env python3
import sys
import os
import logging
from datetime import datetime
import json

# Add the backend directory to the path to resolve imports correctly
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

try:
    from backend.common.config import get_settings
    from backend.common.db import SessionLocal
    from sqlalchemy import text
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    def test_db_connection():
        """Test if we can connect to the database and execute a simple query."""
        try:
            # Get database settings
            settings = get_settings()
            logger.info(f"Database URL is configured: {'Yes' if settings.supabase_db_url else 'No'}")
            
            results = {
                "timestamp": datetime.now().isoformat(),
                "tests": []
            }
            
            # Test database connection
            db = SessionLocal()
            try:
                logger.info("Testing database connection...")
                
                # Execute a simple query to check connectivity
                result = db.execute(text("SELECT 1"))
                assert result.scalar() == 1
                connection_test = {
                    "name": "Database Connection",
                    "passed": True,
                    "message": "Successfully connected to the database"
                }
                logger.info("✅ Database connection successful")
                
                # Test each major table exists
                tables_to_check = ["markets", "market_snapshots", "true_prices", 
                                "traders", "trader_scores", "alert_rules", 
                                "alert_notifications"]
                
                for table in tables_to_check:
                    try:
                        result = db.execute(
                            text(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')")
                        )
                        exists = result.scalar()
                        if exists:
                            logger.info(f"✅ Table '{table}' exists")
                            results["tests"].append({
                                "name": f"Table {table} Check",
                                "passed": True,
                                "message": f"Table '{table}' exists"
                            })
                        else:
                            logger.warning(f"❌ Table '{table}' does not exist")
                            results["tests"].append({
                                "name": f"Table {table} Check",
                                "passed": False,
                                "message": f"Table '{table}' does not exist"
                            })
                    except Exception as e:
                        logger.error(f"Error checking table '{table}': {e}")
                        results["tests"].append({
                            "name": f"Table {table} Check",
                            "passed": False,
                            "message": f"Error checking table: {str(e)}"
                        })
                
                # Add the connection test result
                results["tests"].append(connection_test)
                
            except Exception as e:
                logger.error(f"❌ Database connection failed: {e}")
                results["tests"].append({
                    "name": "Database Connection",
                    "passed": False,
                    "message": f"Failed to connect to database: {str(e)}"
                })
            finally:
                db.close()
                
            # Output results as JSON
            print("\nTest Results Summary:")
            print(json.dumps(results, indent=2))
            
            # Determine overall success
            overall_success = all(test["passed"] for test in results["tests"])
            return overall_success
            
        except ImportError as e:
            logger.error(f"❌ Import error: {e}")
            print(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "tests": [{
                    "name": "Module Import",
                    "passed": False,
                    "message": f"Failed to import required modules: {str(e)}"
                }]
            }, indent=2))
            return False
            
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            print(json.dumps({
                "timestamp": datetime.now().isoformat(),
                "tests": [{
                    "name": "General Test",
                    "passed": False,
                    "message": f"Unexpected error: {str(e)}"
                }]
            }, indent=2))
            return False

except Exception as e:
    print(f"Critical error: {e}")
    sys.exit(1)

if __name__ == "__main__":
    success = test_db_connection()
    sys.exit(0 if success else 1)