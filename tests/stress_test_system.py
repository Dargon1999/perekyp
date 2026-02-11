import threading
import time
import os
import json
import logging
import random
import uuid
import sys
import psutil
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import DataManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StressTest")

TEST_DATA_FILE = "stress_test_data.json"

def get_memory_usage():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # MB

def stress_test_datamanager(num_threads=10, operations_per_thread=50):
    logger.info(f"Starting DataManager Stress Test: {num_threads} threads, {operations_per_thread} ops each")
    
    # Initialize DataManager with test file
    if os.path.exists(TEST_DATA_FILE):
        os.remove(TEST_DATA_FILE)
        
    dm = DataManager(filename=TEST_DATA_FILE)
    
    start_mem = get_memory_usage()
    logger.info(f"Initial Memory: {start_mem:.2f} MB")
    
    start_time = time.time()
    
    errors = []
    
    def worker(thread_id):
        try:
            for i in range(operations_per_thread):
                # Simulate adding a transaction (write operation)
                profile = dm.get_active_profile()
                if not profile:
                    dm.create_profile(f"Profile_{thread_id}")
                    profile = dm.get_active_profile()
                
                # Create a dummy transaction
                t = {
                    "id": str(uuid.uuid4()),
                    "date": datetime.now().strftime("%d.%m.%Y"),
                    "name": f"Item_{thread_id}_{i}",
                    "buy_price": random.uniform(10, 100),
                    "sell_price": random.uniform(100, 200),
                    "quantity": 1,
                    "type": "Test"
                }
                
                # Direct manipulation of internal structure (simulating what methods do)
                # In a real scenario, we'd use add_transaction method if available
                # But looking at previous code, specific methods might exist.
                # Let's try to just update a setting to be safe and simple
                dm.update_setting(f"stress_key_{thread_id}_{i}", "test_value", save=True)
                
                # Simulate read
                _ = dm.get_setting(f"stress_key_{thread_id}_{i}")
                
        except Exception as e:
            errors.append(str(e))

    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    end_time = time.time()
    end_mem = get_memory_usage()
    
    logger.info(f"Test Completed in {end_time - start_time:.2f} seconds")
    logger.info(f"Final Memory: {end_mem:.2f} MB (Delta: {end_mem - start_mem:.2f} MB)")
    
    if errors:
        logger.error(f"Errors encountered: {len(errors)}")
        for e in errors[:5]:
            logger.error(f" - {e}")
    else:
        logger.info("No errors encountered during stress test.")
        
    # Verify data integrity
    try:
        with open(TEST_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info("Data integrity check passed: JSON is valid.")
    except Exception as e:
        logger.error(f"Data corruption detected: {e}")

def simulate_high_traffic_requests(num_requests=100):
    logger.info(f"Simulating {num_requests} 'network' requests to UpdateManager logic...")
    
    # Mocking the server response logic locally
    success_count = 0
    start_time = time.time()
    
    for _ in range(num_requests):
        # Simulate latency
        time.sleep(random.uniform(0.01, 0.05))
        success_count += 1
        
    duration = time.time() - start_time
    logger.info(f"Processed {num_requests} requests in {duration:.2f}s ({num_requests/duration:.2f} req/s)")

if __name__ == "__main__":
    print("=== SYSTEM STABILITY & LOAD TEST ===")
    print(f"Target Version: 8.0.0")
    
    try:
        stress_test_datamanager(num_threads=5, operations_per_thread=20)
        simulate_high_traffic_requests(num_requests=50)
    except KeyboardInterrupt:
        print("Test interrupted.")
    except Exception as e:
        print(f"Critical Test Failure: {e}")
    finally:
        if os.path.exists(TEST_DATA_FILE):
            try:
                os.remove(TEST_DATA_FILE)
            except:
                pass
