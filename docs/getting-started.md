# Getting started

The following guide will help you through the steps needed to run a minimal installation of Hyacinth.

## Creating the Discord Bot

In order to connect Hyacinth to Discord, you must first configure an application for your bot in the [Discord Developer Portal](https://discord.com/developers/applications).

1. In the [Discord Developer Portal](https://discord.com/developers/applications), create an application for Hyacinth
2. In the `Bot` tab, add a new bot and configure the username and icon however you want
3. Still in the `Bot` tab, enable the toggle for "Message Content Intent". This is required to allow executing commands using the `$` prefix without mentioning the bot.
4. Add an OAuth redirect URL in the `OAuth2 -> General` tab. This can be anything, the exact URL does not matter.
5. Generate an invite URL in the `OAuth2 -> URL Generator` tab. Request the "Bot" scope and the following permissions:

   ![required permissions](assets/permissions.png)

6. Copy the generated URL and invite the bot to your server!

## Configuring your environment

- Ensure [Docker](https://docker.com) is installed and working correctly
- Clone the [project repository](https://github.com/stephanlensky/hyacinth)
- In the cloned project folder, create a new file named `.env` with the following content:

  ```env
  # in the unix tz database format, ex. America/New_York
  TZ=<your timezone>

  # copy it from the discord developer portal!
  DISCORD_TOKEN=<your discord token>

  # any password is fine, it will be used for the bot's internal database
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=<a random password>
  ```

  Remember to replace the values inside `<>`!

## Running the bot

After completing the steps above, start Hyacinth with the following Docker command:

```
docker-compose up service
```

If everything worked correctly, the bot's status in Discord will change to online and it will start accepting commands.

### Detached mode

After verifying that everything is working, exit with `Ctrl+c` and restart in detached mode so that the bot will continue to run even after closing the terminal window.

```
docker-compose up -d service
```

To stop the bot after this, use:

```
docker-compose down
```
