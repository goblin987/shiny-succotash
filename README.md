# Multi-Group Telegram Portal Bot

A powerful Telegram bot with an admin panel for managing multiple private groups. Features dynamic single-use invite links, customizable welcome messages, and an intuitive button-based interface.

## Features

### For Users:
- **Simple Interface**: Use `/start` to see available groups
- **One-Click Access**: Click a button to get your invite link
- **Secure Links**: Single-use links that expire after joining
- **Custom Welcome**: Personalized welcome message from admins
- **Referral System**: Get your unique referral link and track how many people join through you

### For Admins:
- **Admin Panel**: Full control via `/admin` command
- **Custom Welcome Message**: Edit the message users see
- **Multi-Group Management**: Add, view, and delete groups
- **Button-Based UI**: No complex commands, just click buttons
- **Secure Authentication**: Only authorized admins can access the panel
- **Referral Analytics**: Track user referrals and see top referrers

## Prerequisites

### 1. Telegram Bot Token
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the prompts
3. Save the bot token provided

### 2. Admin User ID
1. Search for `@userinfobot` on Telegram
2. Send any message to get your user ID
3. Save this number (e.g., `123456789`)

### 3. Group Chat IDs
For each group you want to manage:
1. Add your bot to the private group
2. Make the bot an **administrator** with **"Invite Users"** permission
3. Forward any message from the group to `@userinfobot`
4. Copy the Chat ID (negative number like `-1001234567890`)

## Installation & Deployment on Render

### Step 1: Prepare Your Repository

1. **Clone or create the project:**
```bash
git clone <your-repo-url>
cd gateway
```

2. **Push to GitHub** (if not already done):
```bash
git init
git add .
git commit -m "Initial commit - Multi-Group Portal Bot"
git remote add origin https://github.com/yourusername/telegram-portal-bot.git
git branch -M main
git push -u origin main
```

### Step 2: Deploy on Render

1. **Sign up/Login** to [Render](https://render.com/)

2. **Create New Service:**
   - Click **"New +"** → **"Background Worker"**
   - Connect your GitHub repository
   - Select the `gateway` repository

3. **Configure Service:**
   - **Name**: `telegram-portal-bot` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`

4. **Set Environment Variables:**
   Click **"Advanced"** → **"Add Environment Variable"**
   
   - **BOT_TOKEN**
     - Value: Your bot token from BotFather
     - Example: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
   
   - **ADMIN_IDS**
     - Value: Comma-separated list of admin user IDs
     - Example: `123456789,987654321`
     - For single admin: `123456789`

5. **Add Persistent Disk (IMPORTANT):**
   Scroll down to **"Disk"** section and click **"Add Disk"**
   
   - **Mount Path**: `/var/data`
   - This ensures your groups and settings persist across restarts
   - Without this, all data will be lost when the service restarts!

6. **Deploy:**
   - Click **"Create Background Worker"**
   - Wait for deployment to complete
   - Check logs to verify bot is running

### Step 3: Verify Deployment

Look for these messages in Render logs:
```
INFO - Multi-Group Portal Bot started successfully!
INFO - Authorized admin IDs: 123456789
Bot is running...
```

## Usage Guide

### For Admins

#### Initial Setup

1. **Start a chat with your bot** on Telegram

2. **Open Admin Panel:**
```
/admin
```

3. **Set Welcome Message:**
   - Click "📝 Edit Welcome Message"
   - Send your custom welcome text
   - Confirm the update

4. **Add Your First Group:**
   - Click "🔗 Manage Groups"
   - Click "➕ Add New Group"
   - Enter the group name (e.g., "VIP Members")
   - Enter the group's Chat ID (e.g., `-1001234567890`)
   - Verify the bot has admin permissions in that group

#### Managing Groups

**View All Groups:**
- `/admin` → "🔗 Manage Groups" → "📋 View All Groups"

**Add New Group:**
- `/admin` → "🔗 Manage Groups" → "➕ Add New Group"
- Follow the prompts

**Delete Group:**
- `/admin` → "🔗 Manage Groups" → "🗑️ Delete Group"
- Select the group to delete
- Confirm deletion

#### Edit Welcome Message

- `/admin` → "📝 Edit Welcome Message"
- Send your new welcome text
- Supports plain text, emojis, and Telegram markdown

### For Users

1. **Start the bot:**
```
/start
```

2. **Choose what you want to do:**
   - Click a group button to join that group (invite opens directly!)
   - Click **"🔗 Get My Referral Link"** to see your referral link and stats

3. **Join a group:**
   - Accept the invite and you're in!
   - The link works only once for security

4. **Share your referral link:**
   - Get it from the main menu button or by sending `/referral`
   - Share your unique link with others
   - Track how many people join through your link
   - Check your referral statistics anytime

## Referral System

### How It Works

The bot includes a built-in referral tracking system using Telegram's deep linking feature. Every user automatically gets a unique referral link they can share with others.

### For Community Members

**Get Your Referral Link (Two Ways):**

**Option 1 - Main Menu Button (Easiest):**
1. Send `/start` to the bot
2. Click the **"🔗 Get My Referral Link"** button at the bottom

**Option 2 - Command:**
```
/referral
```

Both will display:
- Your unique referral link (e.g., `https://t.me/YourBot?start=ref_123456789`)
- Number of people you've referred
- Simple statistics about your referrals

**Share Your Link:**
- Send your referral link to friends, post it on social media, or share it in communities
- When someone clicks your link, starts the bot, **and joins a group**, they count as your referral
- Each person only counts once (when they join their first group)
- You can check your stats anytime with `/referral`

### For Admins

**View Referral Statistics:**
1. Open admin panel: `/admin`
2. Click "📊 Referral Statistics"

This shows:
- Total registered users (all who started the bot)
- Users who joined groups (actually engaged)
- Total number of referrals (only counts users who joined groups)
- Conversion rate (percentage of users who joined groups)
- Referral rate (percentage of joined users who were referred)
- Top 10 referrers with their user IDs and referral counts
- Medal emojis (🥇🥈🥉) for the top 3 referrers

### Technical Details

- Uses Telegram deep linking with format: `https://t.me/BotUsername?start=ref_USERID`
- **Referrals only count when users join a group** (not just starting the bot)
- Each user counts once (when they join their first group)
- All referral data is stored persistently in `config.json`
- Users cannot refer themselves
- Referral relationships are tracked permanently
- Statistics update in real-time

## Configuration

The bot stores configuration in `config.json`:

**Storage Location:**
- **On Render**: `/var/data/config.json` (persistent disk)
- **Locally**: `/var/data/config.json` (or current directory if `/var/data` doesn't exist)

```json
{
  "welcome_message": "Your custom welcome message",
  "groups": [
    {
      "id": "unique-id-here",
      "name": "Group Name",
      "invite_link": "https://t.me/+xxxxxxxxxxxx"
    }
  ],
  "referrals": {
    "users": {
      "123456789": {
        "referral_count": 5,
        "referred_by": null,
        "joined_at": "2025-10-28T12:00:00.000000",
        "has_joined_group": true
      },
      "987654321": {
        "referral_count": 0,
        "referred_by": "123456789",
        "joined_at": "2025-10-28T12:05:00.000000",
        "has_joined_group": true
      },
      "555555555": {
        "referral_count": 0,
        "referred_by": "123456789",
        "joined_at": "2025-10-28T12:10:00.000000",
        "has_joined_group": false
      }
    }
  }
}
```

This file is automatically created and managed by the bot. **Do not edit manually** unless necessary.

**Field Explanations:**
- `referral_count`: Number of people this user has successfully referred (who joined groups)
- `referred_by`: User ID of who referred this user (null if not referred)
- `joined_at`: When the user first started the bot
- `has_joined_group`: Whether the user has joined at least one group (referrals only count when true)

In the example above:
- User 123456789 has referred 5 people who joined groups
- User 987654321 was referred by user 123456789 and has joined a group (counts as a referral)
- User 555555555 was referred by user 123456789 but hasn't joined a group yet (doesn't count yet)

**Important:** The persistent disk at `/var/data` ensures your configuration survives service restarts on Render.

## Troubleshooting

### Bot doesn't respond to commands

**Check:**
- Bot is running in Render dashboard
- Environment variables are set correctly
- Check Render logs for errors

### "Access denied" when using /admin

**Solution:**
- Verify your user ID is in `ADMIN_IDS` environment variable
- Get your user ID from `@userinfobot`
- Update environment variable in Render
- Restart the service

### "Couldn't generate invite link" error

**Common causes:**
1. Bot is not in the group
   - Add the bot to your private group

2. Bot is not an administrator
   - Make the bot an admin in group settings

3. Bot doesn't have "Invite Users" permission
   - Edit bot's admin permissions
   - Enable "Invite Users via Link"

4. Wrong Chat ID
   - Verify the Chat ID with `@userinfobot`
   - Chat IDs are negative numbers for groups

### Group added but validation failed

**What it means:**
- The group was added to the system
- But the bot couldn't verify access to it

**Fix:**
1. Ensure bot is in the group
2. Make bot an administrator
3. Give "Invite Users" permission
4. Try generating a link by using `/start` as a regular user

### Config file issues

**If config.json gets corrupted:**

1. Stop the bot
2. Delete `config.json`
3. Restart the bot (it will create a new default config)
4. Re-add your groups through the admin panel

## Security Best Practices

1. **Protect Admin IDs:**
   - Never share your `ADMIN_IDS`
   - Only add trusted users as admins

2. **Monitor Bot Activity:**
   - Check Render logs regularly
   - Look for unauthorized access attempts

3. **Bot Permissions:**
   - Only give necessary permissions in groups
   - Remove bot from groups no longer in use

4. **Single-Use Links:**
   - Links automatically expire after one person joins
   - No risk of link sharing

5. **Regular Audits:**
   - Review group list periodically
   - Remove inactive groups

## Advanced Configuration

### Multiple Admins

Add multiple admin user IDs separated by commas:

```
ADMIN_IDS=123456789,987654321,456789123
```

### Custom Welcome Message with Markdown

The bot supports Telegram markdown in welcome messages:

```
*Bold text*
_Italic text_
`Code`
[Link text](https://example.com)
```

### Logging

The bot logs all important events:
- Admin actions (add/delete groups, edit messages)
- Link generation requests
- Errors and exceptions

View logs in the Render dashboard under "Logs" tab.

## Local Development

### Setup

1. **Install Python 3.10+**

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set environment variables:**

**Windows (PowerShell):**
```powershell
$env:BOT_TOKEN="your_bot_token"
$env:ADMIN_IDS="your_user_id"
$env:STORAGE_DIR="."  # Optional: store config.json in current directory for local testing
```

**Linux/Mac:**
```bash
export BOT_TOKEN="your_bot_token"
export ADMIN_IDS="your_user_id"
export STORAGE_DIR="."  # Optional: store config.json in current directory for local testing
```

**Note:** If `STORAGE_DIR` is not set, it defaults to `/var/data` (you may need to create this directory locally or set it to `.` for current directory).

4. **Run the bot:**
```bash
python bot.py
```

5. **Test on Telegram**

### Testing

1. Use `/start` to verify user flow
2. Use `/admin` to test admin functions
3. Add a test group
4. Generate invite links
5. Check logs for errors

## Architecture

```
bot.py
├── Command Handlers
│   ├── /start (user)
│   ├── /admin (admin)
│   └── /cancel (conversation)
│
├── Callback Handlers
│   ├── Group selection (users)
│   ├── Admin menu navigation
│   └── Confirmation dialogs
│
├── Conversation Handlers
│   ├── Edit welcome message
│   ├── Add group (name → chat ID)
│   └── Delete group (select → confirm)
│
└── Helper Functions
    ├── is_admin()
    ├── generate_invite_link()
    └── storage operations

storage.py
├── load_config()
├── save_config()
├── get_groups()
├── add_group()
├── delete_group()
└── update_welcome_message()
```

## API Reference

### Storage Functions

**load_config() → Dict**
- Loads configuration from config.json
- Returns default config if file doesn't exist

**save_config(config: Dict) → bool**
- Saves configuration to config.json
- Returns True on success

**get_groups() → List[Dict]**
- Returns list of all configured groups

**add_group(name: str, chat_id: str) → Dict**
- Adds a new group to configuration
- Returns the created group dict

**delete_group(group_id: str) → bool**
- Deletes a group by its unique ID
- Returns True if successful

**update_welcome_message(message: str) → bool**
- Updates the welcome message
- Returns True on success

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

If you encounter issues:
1. Check the troubleshooting section
2. Review Render logs
3. Verify all prerequisites are met
4. Check bot permissions in groups

## License

This project is open source and available for community use.

## Changelog

### Version 2.0.0
- **NEW: Referral Tracking System**
  - Automatic referral link generation for all users
  - User command `/referral` to view stats and get link
  - **Referrals only count when users actually join a group** (not just starting the bot)
  - Each user counts once (when they join their first group)
  - Admin panel with referral statistics and analytics
  - Conversion tracking (users who started vs users who joined groups)
  - Top referrers leaderboard with medals
  - Tracks referral relationships permanently
  - Deep linking integration using Telegram's start parameters
- **Improved User Experience**
  - Group invite links now open directly when clicking a button (no extra message)
  - Streamlined one-click group joining process
  - Referral link button added to main menu for easy access
- Enhanced admin panel with user and referral metrics
- Persistent referral data storage in config.json

### Version 1.0.0
- Initial release
- Multi-group support
- Admin panel with button UI
- Single-use invite links
- Customizable welcome messages
- JSON-based storage
- Conversation handlers for smooth UX

---

**Happy Managing! 🚀**

For questions or support, refer to the troubleshooting guide or check the Render deployment logs.

