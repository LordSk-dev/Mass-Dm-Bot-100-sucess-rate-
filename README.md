# Mass-Dm-Bot-100-sucess-rate-

**Mass DM Bot — Fully Automated Edition**

A robust, intelligent, and highly automated Discord Mass DM Bot designed for safety, speed, and reliability. This bot bypasses spam filters, automatically paces itself to avoid IP bans, and manages failed/closed DMs gracefully.

## ✨ Features

- **Intelligent Pacing & Anti-Ban System:** Automatically calculates safe limits using Discord's ratelimit rules to prevent Cloudflare IP bans (strictly caps at 8,000 invalid requests per 10m).
- **Anti-Spam Variation:** Injects zero-width characters and allows for `{rand:a|b}` randomization blocks to bypass exact-message hashing filters.
- **Speed Optimization:** Instantly skips members with closed DMs to maximize speed.
- **Data Persistence:** Keeps track of sent and failed messages (`data/sent.json`, `data/failed.json`). Resumes effortlessly without re-sending to the same users.
- **24/7 Keep-Alive Web Server:** Built-in Flask web server so you can host this bot continuously on platforms like Replit, Render, etc.
- **Smart Placeholders:** Customize your DM with user and server specific information.

## ⚙️ Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LordSk-dev/Mass-Dm-Bot-100-sucess-rate-.git
   cd Mass-Dm-Bot-100-sucess-rate-
   ```

2. **Install requirements:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the Environment variables:**
   Create a `.env` file in the root folder with the following variables:
   ```env
   BOT_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
   PREFIX="!"
   ADMIN_IDS="123456789012345678, 876543210987654321" # Comma-separated Discord User IDs of Bot Admins
   ```

4. **Enable Intends:**
   Ensure that **Server Members Intent** and **Message Content Intent** are enabled for your bot in the [Discord Developer Portal](https://discord.com/developers/applications).

5. **Run the bot:**
   ```bash
   python main.py
   ```

## 💬 Message Formatting (Placeholders)

You can use the following variables in your message:
- `{user}` - Displays the user's Display Name
- `{username}` - Displays the user's Username
- `{mention}` - Pings the user
- `{server}` - Displays the Server's Name
- `{members}` - Displays the Server's Member Count
- `{nl}` - Inserts a new line
- `{rand:word1|word2|word3}` - Chooses a random word from the list.

**Example:**
`!massdm Hello {mention}, welcome to {server}! {nl} We are glad to have you. {rand:Enjoy|Have fun|See ya!}`

## 🛠️ Commands

*Note: All commands require the user to be listed in `ADMIN_IDS`.*

| Command | Description |
|---|---|
| `!massdm <message>` | Starts the mass DM campaign in the current server. You can also reply to an existing message with `!massdm` to use that message's content. |
| `!stop` | Stops the active campaign. |
| `!pause` | Pauses the active campaign. |
| `!resume` | Resumes a paused campaign. |
| `!status` | Shows the progress and statistics of the current campaign. |
| `!servers` | Lists all servers the bot is currently in. |
| `!ping` | Shows the bot's latency. |
| `!reset` | Clears the campaign history (sent/failed logs). Allows you to re-DM users. |

## ⚠️ Disclaimer
This bot is provided for educational and administrative purposes. Abusing the Discord API or sending unsolicited spam violates Discord's Terms of Service and could lead to bot or account termination. Use responsibly.
