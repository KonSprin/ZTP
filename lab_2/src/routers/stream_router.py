# src/routers/stream_router.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import redis
import json
import asyncio
import os
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])

executor = ThreadPoolExecutor(max_workers=10)


async def notification_stream(recipient: str):
    """
    FIXED: Generator function that streams notifications for a specific recipient
    Uses Server-Sent Events (SSE) to push updates to browser
    Now properly non-blocking - won't freeze the API
    """
    # Create a new Redis connection for this stream (pub/sub needs dedicated connection)
    r = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD', '2137'),
        db=0,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    
    pubsub = r.pubsub()
    
    try:
        pubsub.subscribe(PUSH_CHANNEL)
        logger.info(f"Client connected to stream for recipient: {recipient}")
        
        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'recipient': recipient})}\n\n"
        
        # Use asyncio to make blocking Redis calls non-blocking
        loop = asyncio.get_event_loop()
        
        # Keep-alive counter
        last_keepalive = asyncio.get_event_loop().time()
        
        while True:
            try:
                # Run blocking get_message in thread pool
                # This prevents blocking the FastAPI event loop
                message = await loop.run_in_executor(
                    executor,
                    pubsub.get_message,
                    0.5  # Timeout: check for messages every 0.5 seconds
                )
                
                if message and message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        
                        # Filter notifications for this recipient
                        if data.get('recipient') == recipient:
                            # Send notification to client
                            yield f"data: {json.dumps(data)}\n\n"
                            logger.info(f"Streamed notification to {recipient}")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                
                # Send keep-alive comment every 30 seconds
                # Prevents connection timeout
                current_time = asyncio.get_event_loop().time()
                if current_time - last_keepalive > 30:
                    yield f": keepalive\n\n"
                    last_keepalive = current_time
                
                # Small async sleep to yield control back to event loop
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                logger.info(f"Client disconnected (cancelled): {recipient}")
                break
            except Exception as e:
                logger.error(f"Error in stream loop: {e}")
                break
                
    except Exception as e:
        logger.error(f"Stream error for {recipient}: {e}")
    finally:
        # Cleanup
        try:
            pubsub.unsubscribe()
            pubsub.close()
            r.close()
            logger.info(f"Cleaned up stream for {recipient}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


@router.get("/notifications/stream/{recipient}")
async def stream_notifications(recipient: str):
    """
    SSE endpoint for streaming real-time notifications to web dashboard
    
    FIXED: Now properly async and won't block the API
    
    Usage in browser:
        const eventSource = new EventSource('/notifications/stream/user@example.com');
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('New notification:', data);
        };
    """
    return StreamingResponse(
        notification_stream(recipient),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Access-Control-Allow-Origin": "*",  # Allow CORS for SSE
        }
    )


# Add global PUSH_CHANNEL variable (was missing)
PUSH_CHANNEL = os.getenv('PUSH_CHANNEL', 'notifications:push')
