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
MANUS_API_KEY = "sk-Gf2BwROtSJvPEaOsDNxGuqt6Dilvc-LqjFPUt0gk7S9aQrRn3OhKp4egwdrB0ARqIfRP7oIW7Rf15AnsTUfrhIIjvjPn"
MANUS_PROJECT_ID = os.environ.get("MANUS_PROJECT_ID", "ZMYDA6qbig27FWCA99ZGtK")
SLACK_SIGNING_SECRET = os.environ.get("SLACK_SIGNING_SECRET", "")

# Store user task mappings
user_tasks = {}


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
        return response.json().get("ok", False)
    except Exception as e:
        print(f"Error sending Slack message: {e}")
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
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        data = response.json()
        if data.get("ok"):
            return data.get("data", {}).get("task_id")
    except Exception as e:
        print(f"Error creating Manus task: {e}")
    
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
        return response.json().get("ok", False)
    except Exception as e:
        print(f"Error sending Manus message: {e}")
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
            return data.get("data", {}).get("messages", [])
    except Exception as e:
        print(f"Error getting Manus messages: {e}")
    
    return []


def get_latest_assistant_message(messages):
    """Extract latest assistant response"""
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return msg.get("content", "")
    return None


def wait_for_cfo_response(task_id, channel, max_wait=60):
    """Wait for CFO response and send to Slack"""
    start_time = time.time()
    last_count = 0
    
    while time.time() - start_time < max_wait:
        messages = get_task_messages(task_id)
        
        if len(messages) > last_count:
            response = get_latest_assistant_message(messages)
            if response:
                send_slack_message(channel, response)
                return
            last_count = len(messages)
        
        time.sleep(1)
    
    send_slack_message(channel, "⏱️ CFO is taking longer than expected. Please try again.")


def handle_user_message(user_id, channel, text):
    """Process user message and route to CFO"""
    
    # Check if user has existing task
    task_id = user_tasks.get(user_id)
    
    if not task_id:
        # Create new task
        send_slack_message(channel, "🤖 Creating CFO session...")
        task_id = create_manus_task(user_id, text)
        
        if not task_id:
            send_slack_message(channel, "❌ Failed to create CFO session. Please try again.")
            return
        
        user_tasks[user_id] = task_id
    else:
        # Send to existing task
        success = send_manus_message(task_id, text)
        if not success:
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
    
    # Slack URL verification
    if data.get("type") == "url_verification":
        return {"challenge": data.get("challenge")}
    
    # Handle events
    if data.get("type") == "event_callback":
        event = data.get("event", {})
        
        # Handle messages
        if event.get("type") == "message" and not event.get("bot_id"):
            user_id = event.get("user")
            channel = event.get("channel")
            text = event.get("text", "").strip()
            
            if user_id and channel and text:
                print(f"Message from {user_id}: {text}")
                handle_user_message(user_id, channel, text)
        
        # Handle app mentions
        elif event.get("type") == "app_mention":
            user_id = event.get("user")
            channel = event.get("channel")
            text = event.get("text", "").strip()
            
            # Remove bot mention
            text = text.replace(f"<@U{user_id}>", "").strip()
            
            if user_id and channel and text:
                print(f"Mention from {user_id}: {text}")
                handle_user_message(user_id, channel, text)
    
    return {"ok": True}


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    # Verify required env vars
    if not all([SLACK_BOT_TOKEN, MANUS_API_KEY]):
        print("❌ Missing required environment variables")
        exit(1)
    
    print("✅ Starting Slack CFO Bot v2...")
    print(f"📦 Project ID: {MANUS_PROJECT_ID}")
    
    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=False)
