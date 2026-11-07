# Handoff: create the MicroDuck Discord bot token

Goal: give Claude Code read and send access to the 16-831 · Microduck Discord server through an official Discord bot, so it no longer needs the Discord web page.

Server: 16-831 · Microduck, guild ID 1547655727579926589 (Shawn owns it). Channel #general, ID 1547655730352357399.

## Steps (in Shawn's Chrome, logged in to Discord)

1. Open https://discord.com/developers/applications and click **New Application**. Name: `MicroDuck Assistant`. Accept the developer terms.
2. Left menu **Bot**:
   - Click **Reset Token**, then **Copy**. Do not paste it anywhere except step 4.
   - Under **Privileged Gateway Intents**, turn on **Message Content Intent** and **Server Members Intent**. Save.
3. Left menu **OAuth2 → URL Generator**:
   - Scopes: `bot`.
   - Bot permissions: View Channels, Send Messages, Read Message History, Add Reactions, Embed Links, Attach Files.
   - Open the generated URL, choose **16-831 · Microduck**, click **Authorize**.
4. Store the token in the macOS Keychain from Terminal. The command prompts for the token, so it never lands in a file or shell history:

   ```bash
   security add-generic-password -U -s discord-bot-token -a microduck -w
   ```

   Paste the token at the `password data for new item` prompt (twice).

## Check that it worked

```bash
TOKEN=$(security find-generic-password -s discord-bot-token -a microduck -w)
curl -s -H "Authorization: Bot $TOKEN" https://discord.com/api/v10/users/@me/guilds
```

Success: the JSON lists a guild with id `1547655727579926589`. After that, Claude installs the MCP server (SaseQ/discord-mcp, Docker) reading the token from the Keychain, and registers it in Claude Code.
