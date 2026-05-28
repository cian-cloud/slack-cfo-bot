#!/usr/bin/env python3
"""
Slack CFO Bot v2 - Simplified webhook-based approach
Uses Manus API directly without Socket Mode complications
"""

import os
import json
import requests
from flask import Flask, request
from threading import Thread
import time

app = Flask(__name__)

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
MANUS_API_KEY = os.environ.get("MANUS_API_KEY")
MANUS_PROJECT_ID = os.environ.get("MANUS_PROJECT_ID", "ZMYDA6qbig27FWCA99ZGtK")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

# Store user task mappings
user_tasks = {}

print(f"[INIT] SLACK_BOT_TOKEN set: {bool(SLACK_BOT_TOKEN)}")
print(f"[INIT] MANUS_API_KEY set: {bool(MANUS_API_KEY)}")
print(f"[INIT] MANUS_PROJECT_ID: {MANUS_PROJECT_ID}")


def send_slack_message(channel, text):
    """Send a message to Slack"""
    url = "https://slack.com/api/chat.postMessage"
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "channel": channel,
        "text": text,
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        result = response.json().get("ok", False)
        print(f"[SLACK] Message sent to {channel}: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] Error sending Slack message: {e}")
        return False


def create_manus_task(user_id, message_text):
    """Create a new Manus task"""
    url = "https://api.manus.ai/v2/task.create"
    headers = {
        "Content-Type": "application/json",
        "x-manus-api-key": MANUS_API_KEY,
    }
    payload = {
        "project_id": MANUS_PROJECT_ID,
        "message": {
            "content": message_text
        }
    }
    
    print(f"[MANUS] Creating task with API key: {MANUS_API_KEY[:20] if MANUS_API_KEY else 'NONE'}...")
    print(f"[MANUS] Project ID: {MANUS_PROJECT_ID}")
    print(f"[MANUS] Message: {message_text}")
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        print(f"[MANUS] Response status: {response.status_code}")
        print(f"[MANUS] Response body: {response.text}")
        
        data = response.json()
        if data.get("ok"):
            # The API returns task_id at the top level, not inside 'data'
            task_id = data.get("task_id")
            if not task_id:
                # Fallback in case it's inside data
                task_id = data.get("data", {}).get("task_id")
            
            print(f"[MANUS] Task created successfully: {task_id}")
            return task_id
        else:
            print(f"[MANUS] API returned error: {data}")
    except Exception as e:
        print(f"[ERROR] Exception creating Manus task: {e}")
        import traceback
        traceback.print_exc()
    
    return None


def send_manus_message(task_id, message_text):
    """Send message to existing Manus task"""
    url = "https://api.manus.ai/v2/task.sendMessage"
    headers = {
        "Content-Type": "application/json",
        "x-manus-api-key": MANUS_API_KEY,
    }
    payload = {
        "task_id": task_id,
        "message": {
            "content": message_text
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        result = response.json().get("ok", False)
        print(f"[MANUS] Message sent to task {task_id}: {result}")
        return result
    except Exception as e:
        print(f"[ERROR] Error sending Manus message: {e}")
        return False


def get_task_messages(task_id):
    """Get messages from Manus task"""
    url = f"https://api.manus.ai/v2/task.listMessages?task_id={task_id}"
    headers = {
        "x-manus-api-key": MANUS_API_KEY,
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data.get("ok"):
            messages = data.get("data", {}).get("messages", [])
            print(f"[MANUS] Retrieved {len(messages)} messages from task {task_id}")
            return messages
    except Exception as e:
        print(f"[ERROR] Error getting Manus messages: {e}")
    
    return []


def get_latest_assistant_message(messages):
    """Extract latest assistant response"""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            print(f"[MANUS] Found assistant response: {content[:100]}...")
            return content
    print("[MANUS] No assistant message found")
    return None


def wait_for_cfo_response(task_id, channel, max_wait=300):
    """Wait for CFO response and send to Slack"""
    start_time = time.time()
    last_message_count = 0
    
    print(f"[WAIT] Waiting for response on task {task_id}...")
    
    while time.time() - start_time < max_wait:
        # Check task status first
        status_url = f"https://api.manus.ai/v2/task.get?task_id={task_id}"
        headers = {"x-manus-api-key": MANUS_API_KEY}
        
        try:
            resp = requests.get(status_url, headers=headers, timeout=10)
            task_data = resp.json().get("data", {})
            status = task_data.get("status")
            print(f"[WAIT] Task {task_id} status: {status}")
            
            if status == "completed":
                messages = get_task_messages(task_id)
                response = get_latest_assistant_message(messages)
                if response:
                    send_slack_message(channel, response)
                    return
            elif status == "failed":
                send_slack_message(channel, "❌ The CFO encountered an error. Please try again.")
                return
                
        except Exception as e:
            print(f"[ERROR] Error checking task status: {e}")

        time.sleep(5) # Poll every 5 seconds
    
    print(f"[WAIT] Timeout waiting for response")
    send_slack_message(channel, "⏱️ CFO is taking longer than expected. Check the Manus dashboard for the full report.")


def handle_user_message(user_id, channel, text):
    """Process user message and route to CFO"""
    
    print(f"[HANDLER] Processing message from {user_id} in {channel}: {text}")
    
    # Check if user has existing task
    task_id = user_tasks.get(user_id)
    
    if not task_id:
        # Create new task
        print(f"[HANDLER] No existing task for {user_id}, creating new one...")
        send_slack_message(channel, "🤖 Creating CFO session...")
        task_id = create_manus_task(user_id, text)
        
        if not task_id:
            print(f"[HANDLER] Failed to create task for {user_id}")
            send_slack_message(channel, "❌ Failed to create CFO session. Please try again.")
            return
        
        user_tasks[user_id] = task_id
        print(f"[HANDLER] Task created: {task_id}")
    else:
        # Send to existing task
        print(f"[HANDLER] Sending to existing task {task_id}...")
        success = send_manus_message(task_id, text)
        if not success:
            print(f"[HANDLER] Failed to send message to task {task_id}")
            send_slack_message(channel, "❌ Failed to send message. Please try again.")
            return
    
    # Wait for response in background
    send_slack_message(channel, "💭 CFO is analyzing...")
    thread = Thread(target=wait_for_cfo_response, args=(task_id, channel))
    thread.daemon = True
    thread.start()


@app.route("/slack/events", methods=["POST"])
def slack_events():
    """Handle Slack events"""
    data = request.json
    
    print(f"[SLACK] Received event: {data.get('type')}")
    
    # Slack URL verification
    if data.get("type") == "url_verification":
        print("[SLACK] URL verification challenge")
        return {"challenge": data.get("challenge")}
    
    # Handle events
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        
        # Handle messages (including direct messages to app)
        if event.get("type") == "message" and not event.get("bot_id"):
            user_id = event.get("user")
            # For direct messages to apps, use channel or fall back to user ID
            channel = event.get("channel") or event.get("user")
            text = event.get("text", "").strip()
            
            print(f"[SLACK] Message event: user={user_id}, channel={channel}, text={text[:50]}")
            print(f"[SLACK] DEBUG - Full event: {event}")
            
            if user_id and channel and text:
                handle_user_message(user_id, channel, text)
        
        # Handle app mentions
        elif event.get("type") == "app_mention":
            user_id = event.get("user")
            channel = event.get("channel")
            text = event.get("text", "").strip()
            
            print(f"[SLACK] Mention event: user={user_id}, channel={channel}")
            
            # Remove bot mention
            text = text.replace(f"<@U{user_id}>", "").strip()
            
            if user_id and channel and text:
                handle_user_message(user_id, channel, text)
    
    return {"ok": True}


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.route("/debug", methods=["GET"])
def debug():
    """Debug endpoint to check environment variables"""
    return {
        "slack_bot_token": "set" if SLACK_BOT_TOKEN else "MISSING",
        "manus_api_key": "set" if MANUS_API_KEY else "MISSING",
        "manus_project_id": MANUS_PROJECT_ID,
    }


if __name__ == "__main__":
    # Verify required env vars
    if not all([SLACK_BOT_TOKEN, MANUS_API_KEY]):
        print("[ERROR] Missing required environment variables")
        exit(1)
    
    print("[INIT] ✅ Starting Slack CFO Bot v2...")
    print(f"[INIT] 📦 Project ID: {MANUS_PROJECT_ID}")
    
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=False)
