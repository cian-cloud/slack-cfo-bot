# Slack CFO Bot - Railway Deployment Guide

This is a Slack bot that connects your Slack workspace to your Manus CFO agent.

## Prerequisites

- Railway account (https://railway.app)
- GitHub account (for connecting your repo)
- Slack bot tokens (you already have these)
- Manus API key (you already have this)

## Deployment Steps

### Step 1: Create a GitHub Repository

1. Go to https://github.com/new
2. Create a new repository named `slack-cfo-bot`
3. Clone it to your computer:
   ```bash
   git clone https://github.com/YOUR_USERNAME/slack-cfo-bot.git
   cd slack-cfo-bot
   ```

### Step 2: Add Bot Files to Repository

Copy these files into your repository:
- `slack_cfo_bot.py` (the main bot script)
- `requirements.txt` (Python dependencies)
- `Procfile` (tells Railway how to run the bot)
- `runtime.txt` (Python version)
- `.env.example` (configuration template)

### Step 3: Push to GitHub

```bash
git add .
git commit -m "Initial commit: Slack CFO bot"
git push origin main
```

### Step 4: Deploy to Railway

1. Go to https://railway.app
2. Click **"New Project"**
3. Select **"Deploy from GitHub"**
4. Authorize Railway to access your GitHub account
5. Select your `slack-cfo-bot` repository
6. Railway will automatically detect it's a Python project and deploy it

### Step 5: Configure Environment Variables

Once the project is created in Railway:

1. Click on the project
2. Go to the **"Variables"** tab
3. Add these environment variables:
   - `SLACK_BOT_TOKEN`: `xoxb-8469336909232-11198154030561-TTMvrCqAcrHczsLfStTMSwio`
   - `SLACK_APP_TOKEN`: `xapp-1-A0B5NT4J0FP-11196310160930-e39b1012919dfb3228f289154c78fa1e6159fc2bcfcae077580861a837281a42`
   - `MANUS_API_KEY`: `sk-Gf2BwROtSJvPEaOsDNxGuqt6Dilvc-LqjFPUt0gk7S9aQrRn3OhKp4egwdrB0ARqIfRP7oIW7Rf15AnsTUfrhIIjvjPn`
   - `MANUS_PROJECT_ID`: `ZMYDA6qbig27FWCA99ZGtK`

4. Click **"Deploy"**

### Step 6: Verify Deployment

1. Go to the **"Logs"** tab in Railway
2. You should see: `✅ Starting Slack CFO Bot...`
3. If you see errors, check the logs for details

### Step 7: Test the Bot

1. Go to your Slack workspace
2. Open the Manus app or DM the CFO bot
3. Send a test message: `"What's our current cash runway?"`
4. The bot should respond with the CFO's analysis

## Troubleshooting

**Bot not responding?**
- Check Railway logs for errors
- Verify all environment variables are set correctly
- Ensure Slack tokens are valid

**"oauth app not found" error?**
- This means the Manus API key is invalid
- Generate a new API key and update the Railway variable

**Bot keeps crashing?**
- Check the logs in Railway
- Common issues: missing dependencies, invalid tokens

## Updating the Bot

To update the bot code:

1. Make changes to `slack_cfo_bot.py`
2. Push to GitHub: `git add . && git commit -m "Update" && git push`
3. Railway will automatically redeploy

## Support

For issues with:
- **Slack bot**: Check Slack API documentation
- **Manus API**: Visit https://help.manus.im
- **Railway**: Visit https://railway.app/support
