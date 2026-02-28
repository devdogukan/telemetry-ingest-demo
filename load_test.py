"""
Load testing script for telemetry API.

Sends concurrent HTTP requests to test the performance and throughput
of the telemetry collection service.

Usage:
    python load_test.py
    
Configuration:
    Modify the constants below to adjust test parameters.
"""

import sys
import time
import random
import logging
from typing import Tuple, List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median, stdev

import requests
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test Configuration
URL = "http://127.0.0.1:5000/api/telemetry"
NUM_REQUESTS = 5000
CONCURRENCY = 50
TIMEOUT = 10  # seconds
MIN_TEMP = -50.0
MAX_TEMP = 100.0


def send_request(request_id: int) -> Tuple[int, float, int, str]:
    """
    Send a single telemetry request.
    
    Args:
        request_id: Unique identifier for this request
        
    Returns:
        tuple: (request_id, latency, status_code, error_message)
    """
    sensor_id = f"sensor_{request_id % 100}"  # Simulate 100 different sensors
    temperature = random.uniform(MIN_TEMP, MAX_TEMP)
    
    data = {
        "sensor_id": sensor_id,
        "temperature": round(temperature, 2)
    }
    
    start_time = time.time()
    error_message = ""
    status_code = 0
    
    try:
        response = requests.post(
            URL,
            json=data,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        status_code = response.status_code
        latency = time.time() - start_time
        
        if status_code not in [200, 202]:
            error_message = f"Unexpected status: {status_code}"
            logger.debug(f"Request {request_id}: {error_message}")
            
    except RequestException as e:
        latency = time.time() - start_time
        error_message = str(e)
        logger.error(f"Request {request_id} failed: {error_message}")
        
    return request_id, latency, status_code, error_message


def calculate_statistics(latencies: List[float]) -> Dict[str, float]:
    """
    Calculate statistical measures for latencies.
    
    Args:
        latencies: List of latency measurements in seconds
        
    Returns:
        dict: Statistical measures
    """
    if not latencies:
        return {}
    
    sorted_latencies = sorted(latencies)
    count = len(sorted_latencies)
    
    return {
        "count": count,
        "mean": mean(latencies),
        "median": median(latencies),
        "min": min(latencies),
        "max": max(latencies),
        "std_dev": stdev(latencies) if count > 1 else 0,
        "p50": sorted_latencies[int(count * 0.50)],
        "p90": sorted_latencies[int(count * 0.90)],
        "p95": sorted_latencies[int(count * 0.95)],
        "p99": sorted_latencies[int(count * 0.99)],
    }


def run_load_test() -> None:
    """
    Execute the load test and display results.
    """
    logger.info("=" * 70)
    logger.info("Telemetry API Load Test")
    logger.info("=" * 70)
    logger.info(f"Target URL: {URL}")
    logger.info(f"Total Requests: {NUM_REQUESTS:,}")
    logger.info(f"Concurrency: {CONCURRENCY}")
    logger.info(f"Timeout: {TIMEOUT}s")
    logger.info("=" * 70)
    
    # Check if server is reachable
    try:
        response = requests.get(URL.replace("/api/telemetry", "/health"), timeout=5)
        if response.status_code == 200:
            logger.info("✓ Server is reachable")
        else:
            logger.warning(f"⚠ Server responded with status {response.status_code}")
    except Exception as e:
        logger.error(f"✗ Cannot reach server: {e}")
        logger.error("Please ensure the Flask application is running")
        sys.exit(1)
    
    logger.info(f"\nStarting load test...\n")
    
    latencies = []
    status_codes = {}
    errors = []
    successful_requests = 0
    
    start_time = time.time()
    
    # Execute requests concurrently
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [
            executor.submit(send_request, i)
            for i in range(NUM_REQUESTS)
        ]
        
        # Progress tracking
        completed = 0
        for future in as_completed(futures):
            request_id, latency, status_code, error_message = future.result()
            
            latencies.append(latency)
            status_codes[status_code] = status_codes.get(status_code, 0) + 1
            
            if status_code in [200, 202]:
                successful_requests += 1
            
            if error_message:
                errors.append((request_id, error_message))
            
            completed += 1
            
            # Progress indicator
            if completed % (NUM_REQUESTS // 10) == 0:
                progress = (completed / NUM_REQUESTS) * 100
                logger.info(f"Progress: {completed:,}/{NUM_REQUESTS:,} ({progress:.1f}%)")
    
    total_time = time.time() - start_time
    
    # Calculate statistics
    stats = calculate_statistics(latencies)
    
    # Display results
    logger.info("\n" + "=" * 70)
    logger.info("LOAD TEST RESULTS")
    logger.info("=" * 70)
    
    logger.info("\n📊 Overall Statistics:")
    logger.info(f"  Total Requests:        {NUM_REQUESTS:,}")
    logger.info(f"  Successful:            {successful_requests:,} ({successful_requests/NUM_REQUESTS*100:.2f}%)")
    logger.info(f"  Failed:                {len(errors):,} ({len(errors)/NUM_REQUESTS*100:.2f}%)")
    logger.info(f"  Total Duration:        {total_time:.2f}s")
    logger.info(f"  Requests per Second:   {NUM_REQUESTS/total_time:.2f}")
    
    logger.info("\n⏱️  Latency Statistics (ms):")
    logger.info(f"  Mean:                  {stats['mean']*1000:.2f}")
    logger.info(f"  Median:                {stats['median']*1000:.2f}")
    logger.info(f"  Std Dev:               {stats['std_dev']*1000:.2f}")
    logger.info(f"  Min:                   {stats['min']*1000:.2f}")
    logger.info(f"  Max:                   {stats['max']*1000:.2f}")
    
    logger.info("\n📈 Percentiles (ms):")
    logger.info(f"  P50:                   {stats['p50']*1000:.2f}")
    logger.info(f"  P90:                   {stats['p90']*1000:.2f}")
    logger.info(f"  P95:                   {stats['p95']*1000:.2f}")
    logger.info(f"  P99:                   {stats['p99']*1000:.2f}")
    
    logger.info("\n📋 HTTP Status Codes:")
    for status_code, count in sorted(status_codes.items()):
        percentage = (count / NUM_REQUESTS) * 100
        logger.info(f"  {status_code}: {count:,} ({percentage:.2f}%)")
    
    if errors:
        logger.info(f"\n❌ Errors ({len(errors)} total):")
        # Show first 10 errors
        for request_id, error_message in errors[:10]:
            logger.info(f"  Request {request_id}: {error_message}")
        if len(errors) > 10:
            logger.info(f"  ... and {len(errors) - 10} more errors")
    
    logger.info("\n" + "=" * 70)
    
    # Performance assessment
    if successful_requests / NUM_REQUESTS >= 0.99:
        logger.info("✅ EXCELLENT: >99% success rate")
    elif successful_requests / NUM_REQUESTS >= 0.95:
        logger.info("✓ GOOD: >95% success rate")
    elif successful_requests / NUM_REQUESTS >= 0.90:
        logger.info("⚠️  WARNING: 90-95% success rate")
    else:
        logger.info("❌ POOR: <90% success rate")
    
    if stats['p95'] * 1000 < 100:
        logger.info("✅ EXCELLENT: P95 latency < 100ms")
    elif stats['p95'] * 1000 < 500:
        logger.info("✓ GOOD: P95 latency < 500ms")
    else:
        logger.info("⚠️  WARNING: P95 latency > 500ms")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    try:
        run_load_test()
    except KeyboardInterrupt:
        logger.info("\n\nLoad test interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\nLoad test failed: {e}", exc_info=True)
        sys.exit(1)