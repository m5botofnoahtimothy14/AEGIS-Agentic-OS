"""Tests for the core EventBus pub/sub system."""

import asyncio
import threading
import time

from core.event_bus import EventBus


def test_subscribe_and_publish_sync():
    bus = EventBus()
    received = []

    bus.subscribe("test_event", lambda data: received.append(data))
    bus.publish("test_event", {"value": 42})

    assert received == [{"value": 42}]


def test_multiple_handlers_receive_event():
    bus = EventBus()
    first = []
    second = []

    bus.subscribe("multi", lambda d: first.append(d))
    bus.subscribe("multi", lambda d: second.append(d))
    bus.publish("multi", "payload")

    assert first == ["payload"]
    assert second == ["payload"]


def test_publish_with_no_subscribers_is_safe():
    bus = EventBus()
    # Should not raise
    bus.publish("unsubscribed_event", {"anything": True})


def test_subscribers_are_isolated_by_event_type():
    bus = EventBus()
    got_a = []
    got_b = []

    bus.subscribe("event_a", lambda d: got_a.append(d))
    bus.subscribe("event_b", lambda d: got_b.append(d))

    bus.publish("event_a", "only-a")

    assert got_a == ["only-a"]
    assert got_b == []


def test_publish_from_thread_does_not_deadlock():
    bus = EventBus()
    received = []
    done = threading.Event()

    bus.subscribe("thread_event", lambda d: received.append(d))

    def publisher():
        bus.publish("thread_event", "from-thread")
        done.set()

    thread = threading.Thread(target=publisher)
    thread.start()
    assert done.wait(timeout=5)
    thread.join(timeout=5)

    assert received == ["from-thread"]


def test_async_handler_scheduled():
    bus = EventBus()
    results = []
    loop = asyncio.new_event_loop()

    async def handler(data):
        results.append(data)
        return data

    bus.subscribe("async_event", handler)
    bus.loop = loop
    bus.publish("async_event", "async-value")

    # Allow the event loop a moment to process the callback.
    deadline = time.time() + 2
    while not results and time.time() < deadline:
        loop.run_until_complete(asyncio.sleep(0.05))

    assert results == ["async-value"]
    loop.close()
