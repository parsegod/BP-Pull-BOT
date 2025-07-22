import discord
from discord.ext import commands
from discord import app_commands
import json

# Load blueprints
with open("blueprints.json", "r") as f:
    BLUEPRINTS = json.load(f)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    try:
        await tree.sync()
        print("Slash commands synced.")
    except Exception as e:
        print(e)

# Blueprint command
@tree.command(name="blueprint", description="View a blueprint by ID")
@app_commands.describe(nameid="The ID of the blueprint (e.g., storm_rage)")
async def blueprint(interaction: discord.Interaction, nameid: str):
    bp = next((b for b in BLUEPRINTS if b["id"].lower() == nameid.lower()), None)
    if not bp:
        await interaction.response.send_message("❌ Blueprint not found.", ephemeral=True)
        return

    embed = discord.Embed(
        title=bp["name"],
        description=f"🔫 **Weapon:** {bp['weapon']}\n📦 **Pool:** {bp['pool']['name']}",
        color=discord.Color.blurple()
    )
    embed.set_image(url=bp["image"])

    # Create button
    view = discord.ui.View()
    
    class ViewPoolButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="View Pool", style=discord.ButtonStyle.primary)

        async def callback(self, interaction_button: discord.Interaction):
            pool_number = bp["pool"]["number"]
            pool_blueprints = [b for b in BLUEPRINTS if b["pool"]["number"] == pool_number]

            pool_embed = discord.Embed(
                title=f"{bp['pool']['name']}",
                description="\n".join([f"**{i+1}.** {b['name']} (`{b['id']}`)" for i, b in enumerate(pool_blueprints)]),
                color=discord.Color.green()
            )
            await interaction_button.response.send_message(embed=pool_embed, ephemeral=True)

    view.add_item(ViewPoolButton())
    await interaction.response.send_message(embed=embed, view=view)

bot.run("bot_token_placeholder")
