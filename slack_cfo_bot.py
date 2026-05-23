#!/usr/bin/env python3
"""
Slack CFO Bot - Connects Slack messages to Manus CFO Agent
This bot listens for messages in Slack and routes them to the CFO agent via Manus API.
"""

import os
import json
import time
import requests
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

# Configuration
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN")
MANUS_API_KEY = os.environ.get("MANUS_API_KEY")
MANUS_PROJECT_ID = os.environ.get("MANUS_PROJECT_ID", "ZMYDA6qbig27FWCA99ZGtK")

# Initialize Slack app
app = App(token=SLACK_BOT_TOKEN)

# Store task IDs per user for conversation continuity
user_task_map = {}


def create_manus_task(user_id, message_text):
    """Create a new Manus task for the CFO agent"""
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
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok"):
            task_id = data.get("data", {}).get("task_id")
            return task_id
        else:
            print(f"Error creating task: {data}")
            return None
    except Exception as e:
        print(f"Exception creating task: {e}")
        return None


def send_manus_message(task_id, message_text):
    """Send a message to an existing Manus task"""
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
        response.raise_for_status()
        data = response.json()
        return data.get("ok")
    except Exception as e:
        print(f"Exception sending message: {e}")
        return False


def get_task_messages(task_id):
    """Retrieve messages from a Manus task"""
    url = f"https://api.manus.ai/v2/task.listMessages?task_id={task_id}"
    
    headers = {
        "x-manus-api-key": MANUS_API_KEY,
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok"):
            messages = data.get("data", {}).get("messages", [])
            return messages
        else:
            print(f"Error retrieving messages: {data}")
            return []
    except Exception as e:
        print(f"Exception retrieving messages: {e}")
        return []


def extract_cfo_response(messages):
    """Extract the CFO agent's response from messages"""
    for message in reversed(messages):
        if message.get("role") == "assistant":
            return message.get("content", "")
    return None


def wait_for_response(task_id, max_wait=30):
    """Wait for CFO agent to respond"""
    start_time = time.time()
    last_message_count = 0
    
    while time.time() - start_time < max_wait:
        messages = get_task_messages(task_id)
        
        # Check if there's a new assistant message
        if len(messages) > last_message_count:
            response = extract_cfo_response(messages)
            if response:
                return response
            last_message_count = len(messages)
        
        time.sleep(1)
    
    return "The CFO agent is taking longer than expected to respond. Please try again."


@app.message()
def handle_message(message, say):
    """Handle incoming Slack messages"""
    user_id = message.get("user")
    channel_id = message.get("channel")
    message_text = message.get("text", "").strip()
    
    # Ignore bot messages and empty messages
    if message.get("bot_id") or not message_text:
        return
    
    # Ignore messages from the bot itself
    if user_id == app.client.auth_test()["user_id"]:
        return
    
    print(f"Received message from {user_id}: {message_text}")
    
    # Check if user has an existing task
    task_id = user_task_map.get(user_id)
    
    if not task_id:
        # Create a new task for this user
        say("🤖 Creating CFO session...")
        task_id = create_manus_task(user_id, message_text)
        
        if not task_id:
            say("❌ Failed to create CFO session. Please try again.")
            return
        
        user_task_map[user_id] = task_id
        print(f"Created new task {task_id} for user {user_id}")
    else:
        # Send message to existing task
        success = send_manus_message(task_id, message_text)
        if not success:
            say("❌ Failed to send message to CFO. Please try again.")
            return
    
    # Wait for response
    say("💭 CFO is analyzing...")
    response = wait_for_response(task_id)
    
    if response:
        say(response)
    else:
        say("❌ No response from CFO. Please try again.")


@app.event("app_mention")
def handle_mention(body, say):
    """Handle @mentions of the bot"""
    message_text = body["event"]["text"]
    # Remove the bot mention from the message
    message_text = message_text.replace(f"<@{app.client.auth_test()['user_id']}>", "").strip()
    
    if message_text:
        # Treat mention like a regular message
        handle_message({
            "user": body["event"]["user"],
            "channel": body["event"]["channel"],
            "text": message_text,
        }, say)


@app.event("app_home_opened")
def handle_app_home_opened(body, logger):
    """Handle app home opened event"""
    logger.debug(body)


if __name__ == "__main__":
    # Verify required environment variables
    if not all([SLACK_BOT_TOKEN, SLACK_APP_TOKEN, MANUS_API_KEY]):
        print("❌ Missing required environment variables:")
        print("   - SLACK_BOT_TOKEN")
        print("   - SLACK_APP_TOKEN")
        print("   - MANUS_API_KEY")
        exit(1)
    
    print("✅ Starting Slack CFO Bot...")
    print(f"📦 Project ID: {MANUS_PROJECT_ID}")
    
    # Start the bot
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()
