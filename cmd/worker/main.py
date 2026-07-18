import asyncio
import logging
import os
import random
import sys
import uuid
import httpx

# Configure Logging to stream clearly to stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("GPUWorker")

# Configuration constants
API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
TICK_INTERVAL = 3.0  # seconds

# List of realistic GPU specifications to simulate
GPU_MODELS = [
    {"gpu_model": "NVIDIA GeForce RTX 4090", "vram_gb": 24},
    {"gpu_model": "NVIDIA RTX A6000", "vram_gb": 48},
    {"gpu_model": "NVIDIA H100 PCIe", "vram_gb": 80},
    {"gpu_model": "NVIDIA Jetson Orin Nano", "vram_gb": 8}
]


async def register_node(client: httpx.AsyncClient, hostname: str, hardware_specs: dict) -> str:
    """Register the worker node with the control plane API.

    Performs indefinite retries with exponential backoff if the API is offline.
    """
    backoff = 2.0
    while True:
        try:
            logger.info(f"Attempting to register node '{hostname}' with specs: {hardware_specs}...")
            response = await client.post(
                f"{API_URL}/v1/nodes",
                json={
                    "hostname": hostname,
                    "hardware_specs": hardware_specs
                }
            )
            response.raise_for_status()
            node_data = response.json()
            node_id = node_data["id"]
            logger.info(f"Node successfully registered with ID: '{node_id}'")
            return node_id
        except httpx.RequestError as exc:
            logger.warning(f"Failed to reach API server: {exc}. Retrying in {backoff}s...")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                # Handle name collision recovery by appending a random suffix
                logger.error("Hostname collision. Generating new suffix and retrying...")
                hostname = f"{hostname}-retry-{random.randint(100, 999)}"
            else:
                logger.error(f"HTTP error during registration: {exc.response.text}. Retrying...")
        
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60.0)


async def send_heartbeat(client: httpx.AsyncClient, node_id: str) -> bool:
    """Transmit a heartbeat keepalive signal to the API."""
    try:
        response = await client.post(f"{API_URL}/v1/nodes/{node_id}/heartbeat")
        response.raise_for_status()
        logger.info("Heartbeat keepalive sent successfully.")
        return True
    except httpx.RequestError as exc:
        logger.error(f"Network error sending heartbeat: {exc}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"API returned error for heartbeat: {exc.response.text}")
    return False


async def send_telemetry(client: httpx.AsyncClient, node_id: str) -> bool:
    """Simulate and transmit realistic hardware telemetry metrics."""
    cpu = round(random.uniform(10.0, 90.0), 1)
    gpu = round(random.uniform(0.0, 100.0), 1)
    temp = round(random.uniform(40.0, 85.0), 1)
    
    try:
        logger.info(f"Telemetry metrics -> CPU: {cpu}%, GPU: {gpu}%, Temp: {temp}°C")
        response = await client.post(
            f"{API_URL}/v1/nodes/{node_id}/telemetry",
            json={
                "cpu_usage": cpu,
                "gpu_usage": gpu,
                "temperature": temp
            }
        )
        response.raise_for_status()
        logger.info("Telemetry ingested successfully.")
        return True
    except httpx.RequestError as exc:
        logger.error(f"Network error sending telemetry: {exc}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"API returned error for telemetry: {exc.response.text}")
    return False


async def main() -> None:
    # Initialize unique worker metadata
    node_suffix = str(uuid.uuid4())[:8]
    hostname = f"gpu-node-{node_suffix}"
    hardware_specs = random.choice(GPU_MODELS)
    
    logger.info("Starting GPU Fleet Commander Worker Simulator...")
    logger.info(f"Target API Server: {API_URL}")
    
    # Load pre-shared API Key credentials
    api_key = os.getenv("API_KEY", "gpu_fleet_secure_token_2026")
    
    # Setup HTTP client limits and timeouts suited for keeping connections alive
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    timeout = httpx.Timeout(5.0, connect=10.0)
    headers = {"X-API-Key": api_key}
    
    async with httpx.AsyncClient(limits=limits, timeout=timeout, headers=headers) as client:
        # Step 1: Register node
        node_id = await register_node(client, hostname, hardware_specs)
        
        # Step 2: Continuous Ingestion loop
        while True:
            logger.info("Executing keepalive and telemetry transmission task...")
            await asyncio.gather(
                send_heartbeat(client, node_id),
                send_telemetry(client, node_id)
            )
            await asyncio.sleep(TICK_INTERVAL)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker Simulator terminated by user. Exiting gracefully...")
