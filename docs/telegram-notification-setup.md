# Telegram Notification Setup Guide for Claude Code (Project-Specific)

This guide will help you set up project-specific Telegram notifications for Claude Code task completions in the DevPocket project.

## Prerequisites

- Telegram account
- Access to your development environment where Claude Code is installed

## Step 1: Create a Telegram Bot

1. **Open Telegram** and search for `@BotFather`
2. **Start a conversation** with BotFather by clicking "Start"
3. **Create a new bot** by sending the command:
   ```
   /newbot
   ```
4. **Choose a name** for your bot (e.g., "Claude Code Notifications")
5. **Choose a username** for your bot (must end with 'bot', e.g., "claude_notifications_bot")
6. **Save the Bot Token** - BotFather will provide you with a token that looks like:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

## Step 2: Get Your Chat ID

1. **Start a conversation** with your newly created bot
2. **Send any message** to the bot (e.g., "Hello")
3. **Open your browser** and navigate to:
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
   Replace `<YOUR_BOT_TOKEN>` with the token from Step 1.

4. **Find your chat ID** in the JSON response. Look for the `"chat"` object and find the `"id"` field:
   ```json
   {
     "update_id": 123456789,
     "message": {
       "chat": {
         "id": 987654321,
         "first_name": "Your Name",
         "type": "private"
       }
     }
   }
   ```
   Your chat ID is the number in the `"id"` field (e.g., `987654321`).

## Step 3: Set Environment Variables

Add the following environment variables to your shell configuration file (`.bashrc`, `.zshrc`, or `.profile`):

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="987654321"
```

Replace the values with your actual bot token and chat ID from the previous steps.

**Apply the changes:**
```bash
source ~/.bashrc  # or ~/.zshrc, depending on your shell
```

## Step 4: Verify the Setup

Test the Telegram notification by running a simple Claude Code task within the DevPocket project:

1. **Navigate to the project directory:**
   ```bash
   cd /path/to/devpocket-warp-api
   ```

2. **Create a test file:**
   ```bash
   echo "console.log('Hello, DevPocket!');" > test.js
   ```

3. **Run Claude Code** and ask it to modify the file:
   ```bash
   claude-code "Add a comment to test.js explaining what it does"
   ```

4. **Check your Telegram** - you should receive a DevPocket-specific notification when Claude completes the task.

## Step 5: Project Configuration

The hook is now configured as a **project-specific** setup. Here's how it works:

### File Locations
- **Hook Script**: `.claude/hooks/telegram_notify.sh` (in project root)
- **Configuration**: `.claude/settings.json` (in project root)
- **Project-specific**: Only triggers for DevPocket project tasks

### Current Configuration
The current setup in `.claude/settings.json`:

```json
{
  "hooks": {
    "matchers": [
      {
        "events": ["Stop", "SubagentStop"],
        "projects": ["*"],
        "action": {
          "type": "script",
          "script": "$CLAUDE_PROJECT_DIR/.claude/hooks/telegram_notify.sh"
        }
      }
    ]
  }
}
```

### Customization Options

**To get notifications for all tool uses** (not just task completion), modify `.claude/settings.json`:

```json
{
  "hooks": {
    "matchers": [
      {
        "events": ["PostToolUse"],
        "projects": ["*"],
        "action": {
          "type": "script",
          "script": "$CLAUDE_PROJECT_DIR/.claude/hooks/telegram_notify.sh"
        }
      }
    ]
  }
}
```

**To add multiple notification types**:

```json
{
  "hooks": {
    "matchers": [
      {
        "events": ["Stop", "SubagentStop"],
        "projects": ["*"],
        "action": {
          "type": "script",
          "script": "$CLAUDE_PROJECT_DIR/.claude/hooks/telegram_notify.sh"
        }
      },
      {
        "events": ["SessionStart"],
        "projects": ["*"],
        "action": {
          "type": "script",
          "script": "$CLAUDE_PROJECT_DIR/.claude/hooks/telegram_notify.sh"
        }
      }
    ]
  }
}
```

## Troubleshooting

### No notifications received
1. **Check environment variables:**
   ```bash
   echo $TELEGRAM_BOT_TOKEN
   echo $TELEGRAM_CHAT_ID
   ```

2. **Test the bot manually:**
   ```bash
   curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d '{"chat_id": "'${TELEGRAM_CHAT_ID}'", "text": "Test message"}'
   ```

3. **Check hook script permissions:**
   ```bash
   ls -la .claude/hooks/telegram_notify.sh
   ```
   Should show executable permissions (`-rwxr-xr-x`).

4. **Verify settings.json syntax:**
   ```bash
   cat .claude/settings.json | jq .
   ```
   Should parse without errors.

5. **Ensure you're in the project directory:**
   ```bash
   pwd  # Should show /path/to/devpocket-warp-api
   ```

### Bot not responding
- Ensure you've started a conversation with the bot
- Verify the bot token is correct
- Check that the chat ID matches your conversation

### Script errors
Check the Claude Code logs for any error messages from the hook script.

## Security Notes

- **Keep your bot token secret** - treat it like a password
- **Don't commit tokens to version control** - use environment variables
- **Consider using a dedicated bot** for development notifications
- **Regularly rotate tokens** if needed through BotFather
- **Project-specific setup**: Hook files are stored in the project but environment variables remain global

## Project-Specific Benefits

- **Isolated configuration**: Each project can have its own notification settings
- **Version controlled**: Hook scripts can be committed and shared with team
- **Portable**: Works consistently across different development environments
- **Customizable**: Different projects can have different notification formats

## Available Hook Events

The current setup triggers on these events:
- **Stop**: When Claude completes a task
- **SubagentStop**: When a specialized Claude agent completes its work

Other available events you can use:
- **PreToolUse**: Before any tool is used
- **PostToolUse**: After any tool is used
- **Notification**: For general notifications
- **UserPromptSubmit**: When user submits a prompt
- **PreCompact**: Before context compression
- **SessionStart**: When a new session starts

Modify the "events" array in `settings.json` to customize which events trigger notifications.