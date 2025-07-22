#Required libraries imports
##################################################################################
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
##################################################################################

#Load blueprint Data from JSON
##################################################################################
with open("blueprints.json", "r") as f:
    BLUEPRINTS = json.load(f)

# Set up Discord bot intents to receive all events
intents = discord.Intents.all()
# Initialize the bot with a command prefix and specified intents
bot = commands.Bot(command_prefix="!", intents=intents)
# Get the command tree for registering application (slash) commands
tree = bot.tree
##################################################################################

# Event handler for when the bot has successfully connected to Discord
##################################################################################
@bot.event
async def on_ready():
    # Print a message to the console indicating the bot is logged in
    print(f"Bot logged in as {bot.user}")
    try:
        # Attempt to synchronize slash commands with Discord
        await tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        # Print any error that occurs during slash command synchronization
        print(f"Error syncing slash commands: {e}")
##################################################################################

# Define a new slash command named "blueprint"
##################################################################################
@tree.command(name="blueprint", description="View a blueprint by ID")
# Define the argument for the "blueprint" command
@app_commands.describe(nameid="The ID of the blueprint (e.g., storm_rage)")
async def blueprint(interaction: discord.Interaction, nameid: str):
    # Search for a blueprint in the BLUEPRINTS list that matches the provided ID (case-insensitive)
    bp = next((b for b in BLUEPRINTS if b["id"].lower() == nameid.lower()), None)
    # If no blueprint is found, send an error message to the user
    if not bp:
        await interaction.response.send_message("❌ Blueprint not found.", ephemeral=True)
        return

# Create a Discord embed to display blueprint information
##################################################################################
    embed = discord.Embed(
        title=bp["name"],
        description=f"🔫 **Weapon:** {bp['weapon']}\n📦 **Pool:** {bp['pool']['name']}",
        color=discord.Color.blurple()
    )
    embed.set_image(url=bp["image"])

    view = discord.ui.View()
    
    # Define a custom button class for viewing the blueprint's pool
    class ViewPoolButton(discord.ui.Button):
        def __init__(self):

            super().__init__(label="View Pool", style=discord.ButtonStyle.primary)

        # Callback function executed when the "View Pool" button is pressed
        async def callback(self, interaction_button: discord.Interaction):

            pool_number = bp["pool"]["number"]
            pool_blueprints = [b for b in BLUEPRINTS if b["pool"]["number"] == pool_number]
            pool_embed = discord.Embed(
                title=f"{bp['pool']['name']}",
                description="\n".join([f"**{i+1}.** {b['name']} (`{b['id']}`)" for i, b in enumerate(pool_blueprints)]),
                color=discord.Color.green()
            )
            await interaction_button.response.send_message(embed=pool_embed, ephemeral=True)

    # Add the custom "View Pool" button to the view
    view.add_item(ViewPoolButton())
    # Send the initial blueprint embed with the button to the user
    await interaction.response.send_message(embed=embed, view=view)
##################################################################################

# Retrieve the Discord bot token from environment variables
##################################################################################
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if DISCORD_BOT_TOKEN:
    bot.run(DISCORD_BOT_TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    print("Please set the DISCORD_BOT_TOKEN environment variable before running the bot.")
##################################################################################

