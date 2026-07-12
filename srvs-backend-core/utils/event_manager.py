import asyncio
import json

class EventManager:
    def __init__(self):
        self.queues = set()

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self.queues.discard(queue)

    def publish(self, event_type: str, data: dict):
        event = {
            "type": event_type,
            "data": data
        }
        # Publish event to all active subscribers
        for queue in list(self.queues):
            try:
                queue.put_nowait(event)
            except Exception:
                pass

event_manager = EventManager()
