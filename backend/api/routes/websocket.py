from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as aioredis
import json
import asyncio
from config import get_settings

router = APIRouter()
settings = get_settings()


@router.websocket("/{design_id}")
async def websocket_events(websocket: WebSocket, design_id: str):
    """
    WebSocket endpoint streaming real-time agent execution events from Redis pub/sub.
    """
    await websocket.accept()

    redis_client = None
    pubsub = None
    try:
        redis_client = aioredis.from_url(settings.redis_url)
        pubsub = redis_client.pubsub()
        channel = f"design:{design_id}:events"
        await pubsub.subscribe(channel)

        # Notify client connection
        await websocket.send_json({
            "type": "connection_established",
            "design_id": design_id,
            "message": f"Connected to live event stream for design {design_id}",
        })

        while True:
            # Check for Redis messages
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data = json.loads(message["data"])
                await websocket.send_json(data)
                if data.get("type") in ("pipeline_complete", "pipeline_error"):
                    break

            # Heartbeat check to prevent disconnect
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "websocket_error",
                "error": str(e),
            })
        except Exception:
            pass
    finally:
        if pubsub:
            await pubsub.unsubscribe()
            await pubsub.close()
        if redis_client:
            await redis_client.close()
