#!/usr/bin/env python3
"""
Simple test client for the Google Ads Expert AI WebSocket API.
Tests the Socket.IO integration and streaming functionality.
"""

import asyncio
from datetime import datetime
from typing import Any
import socketio

# Create Socket.IO client
sio = socketio.AsyncClient()

# Global state for testing
received_events = []
answer_chunks = []


@sio.event
async def connect() -> None:
    print(f"🔗 Connected to server at {datetime.now()}")


@sio.event
async def disconnect() -> None:
    print(f"❌ Disconnected from server at {datetime.now()}")


@sio.event
async def connection_confirmed(data: dict[str, Any]) -> None:
    print(f"✅ Connection confirmed: {data}")
    received_events.append(("connection_confirmed", data))


@sio.event
async def question_start(data: dict[str, Any]) -> None:
    print(f"❓ Question started: {data['question']}")
    received_events.append(("question_start", data))


@sio.event
async def tool_start(data: dict[str, Any]) -> None:
    print(f"🔧 Tool started: {data['tool']} - {data.get('description', 'Processing...')}")
    received_events.append(("tool_start", data))


@sio.event
async def tool_progress(data: dict[str, Any]) -> None:
    print(f"⚙️ Tool progress: {data['tool']} - {data.get('message', 'Working...')}")
    received_events.append(("tool_progress", data))


@sio.event
async def tool_complete(data: dict[str, Any]) -> None:
    print(f"✅ Tool completed: {data['tool']} - Found {data.get('results_count', 'N/A')} results")
    received_events.append(("tool_complete", data))


@sio.event
async def tool_error(data: dict[str, Any]) -> None:
    print(f"❌ Tool error: {data['tool']} - {data['error']}")
    received_events.append(("tool_error", data))


@sio.event
async def answer_chunk(data: dict[str, Any]) -> None:
    chunk = data['chunk']
    answer_chunks.append(chunk)
    print(f"📝 Answer chunk: {chunk[:100]}{'...' if len(chunk) > 100 else ''}")
    received_events.append(("answer_chunk", data))


@sio.event
async def grounding_update(data: dict[str, Any]) -> None:
    if data['type'] == 'source':
        source = data['source']
        print(f"📚 Source added: {source['title']} ({source['domain']})")
    elif data['type'] == 'query':
        print(f"🔍 Query tracked: {data['query']}")
    received_events.append(("grounding_update", data))


@sio.event
async def answer_complete(data: dict[str, Any]) -> None:
    print(f"🎉 Answer complete! Total chunks: {len(answer_chunks)}")
    print(f"📊 Grounding: {len(data['grounding']['sources'])} sources, {len(data['grounding']['queries'])} queries")
    received_events.append(("answer_complete", data))


@sio.event
async def error(data: dict[str, Any]) -> None:
    print(f"💥 Error: {data['message']} ({data.get('error_type', 'unknown')})")
    received_events.append(("error", data))


@sio.event
async def session_info(data: dict[str, Any]) -> None:
    print(f"ℹ️ Session info: {data}")
    received_events.append(("session_info", data))


@sio.event
async def pong(data: dict[str, Any]) -> None:
    print(f"🏓 Pong received: {data}")
    received_events.append(("pong", data))


async def test_basic_connection() -> bool:
    """Test basic connection and capabilities."""
    print("=" * 60)
    print("🧪 Testing Basic Connection")
    print("=" * 60)
    
    try:
        await sio.connect('http://localhost:8000')
        
        # Wait for connection confirmation
        await asyncio.sleep(2)
        
        # Test ping
        await sio.emit('ping', {'test': 'data'})
        await asyncio.sleep(1)
        
        # Get session info
        await sio.emit('get_session_info', {})
        await asyncio.sleep(1)
        
        print("✅ Basic connection test passed")
        
    except Exception as e:
        print(f"❌ Basic connection test failed: {e}")
        return False
    
    return True


async def test_simple_question() -> bool:
    """Test asking a simple question."""
    print("\n" + "=" * 60)
    print("🧪 Testing Simple Question")
    print("=" * 60)
    
    # Clear previous state
    answer_chunks.clear()
    
    question = "What are Google Ads campaign types?"
    
    try:
        print(f"Asking question: {question}")
        await sio.emit('ask_question', {'question': question})
        
        # Wait for processing (adjust timeout as needed)
        await asyncio.sleep(30)
        
        print(f"✅ Question processed. Received {len(answer_chunks)} answer chunks")
        
        if answer_chunks:
            full_answer = ''.join(answer_chunks)
            print(f"📝 Full answer length: {len(full_answer)} characters")
            print(f"📝 Answer preview: {full_answer[:200]}...")
        
    except Exception as e:
        print(f"❌ Simple question test failed: {e}")
        return False
    
    return True


async def test_error_handling() -> bool:
    """Test error handling with invalid input."""
    print("\n" + "=" * 60)
    print("🧪 Testing Error Handling")
    print("=" * 60)
    
    try:
        # Test empty question
        await sio.emit('ask_question', {'question': ''})
        await asyncio.sleep(2)
        
        # Test missing question
        await sio.emit('ask_question', {})
        await asyncio.sleep(2)
        
        print("✅ Error handling test completed")
        
    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False
    
    return True


async def print_event_summary() -> None:
    """Print summary of all received events."""
    print("\n" + "=" * 60)
    print("📊 Event Summary")
    print("=" * 60)
    
    event_counts: dict[str, int] = {}
    for event_type, data in received_events:
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")
    
    print(f"\nTotal events received: {len(received_events)}")


async def main() -> None:
    """Run all tests."""
    print("🚀 Starting WebSocket Integration Tests")
    print(f"Time: {datetime.now()}")
    
    # Test basic connection
    if not await test_basic_connection():
        return
    
    # Test simple question
    if not await test_simple_question():
        await sio.disconnect()
        return
    
    # Test error handling
    await test_error_handling()
    
    # Print summary
    await print_event_summary()
    
    # Disconnect
    await sio.disconnect()
    
    print("\n🎉 All tests completed!")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Tests interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
