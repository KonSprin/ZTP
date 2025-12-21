# src/routers/stream_router.py
# BETTER VERSION: Uses async Redis (requires: pip install redis[async])
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from redis.asyncio import Redis
import json
import asyncio
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["streaming"])

PUSH_CHANNEL = os.getenv('PUSH_CHANNEL', 'notifications:push')


async def notification_stream(recipient: str):
    """
    BEST VERSION: Generator using fully async Redis
    No blocking calls, no thread pool needed
    """
    # Create async Redis connection
    r = Redis(
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
        await pubsub.subscribe(PUSH_CHANNEL)
        logger.info(f"Client connected to stream for recipient: {recipient}")
        
        # Send initial connection confirmation
        yield f"data: {json.dumps({'type': 'connected', 'recipient': recipient})}\n\n"
        
        # Keep-alive tracking
        last_keepalive = asyncio.get_event_loop().time()
        
        # Listen for messages (fully async!)
        async for message in pubsub.listen():
            try:
                if message['type'] == 'message':
                    try:
                        data = json.loads(message['data'])
                        
                        # Filter notifications for this recipient
                        if data.get('recipient') == recipient:
                            yield f"data: {json.dumps(data)}\n\n"
                            logger.info(f"Streamed notification to {recipient}")
                            
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                
                # Send keep-alive every 30 seconds
                current_time = asyncio.get_event_loop().time()
                if current_time - last_keepalive > 30:
                    yield f": keepalive\n\n"
                    last_keepalive = current_time
                    
            except asyncio.CancelledError:
                logger.info(f"Client disconnected: {recipient}")
                break
            except Exception as e:
                logger.error(f"Error in stream: {e}")
                break
                
    except Exception as e:
        logger.error(f"Stream error for {recipient}: {e}")
    finally:
        try:
            await pubsub.unsubscribe()
            await pubsub.close()
            await r.close()
            logger.info(f"Cleaned up stream for {recipient}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


@router.get("/notifications/stream/{recipient}")
async def stream_notifications(recipient: str):
    """
    SSE endpoint for streaming real-time notifications
    Fully async, won't block the API
    """
    return StreamingResponse(
        notification_stream(recipient),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        }
    )
