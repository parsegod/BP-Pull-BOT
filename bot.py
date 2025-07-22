#Required libraries imports
##################################################################################
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
##################################################################################
load_dotenv()
# Load JSON data
with open("blueprints.json", "r") as f:
    data = json.load(f)

# Constants
WEAPON_TYPES = [
    "assault rifles", "smgs", "shotguns", "snipers",
    "lmgs", "marksman", "pistols", "melee", "all"
]

CATEGORY_MAP = {
    "assault rifles": "0",
    "smgs": "1",
    "shotguns": "2",
    "snipers": "3",
    "lmgs": "4",
    "marksman": "5",
    "pistols": "6",
    "melee": "7"
}

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await tree.sync()
    print("✅ Slash commands synced.")

# 🔍 Blueprint lookup helper
def find_blueprint(nameid: str):
    nameid = nameid.lower()
    for weapon in data["Weapons"]:
        for bp in weapon["Blueprints"]:
            if bp["Name"].lower() == nameid:
                return {
                    "weapon": weapon["Name"],
                    "blueprint_name": bp["Name"],
                    "pool": bp["Pool"],
                    "status": bp.get("status", "UNKNOWN")
                }
    return None

# 📦 Pool blueprint list
def get_pool_blueprints(pool_number: str, weapontype: str = "all"):
    results = []
    for weapon in data["Weapons"]:
        if weapontype != "all":
            if CATEGORY_MAP.get(weapontype, "-1") != weapon["Category"]:
                continue
        for bp in weapon["Blueprints"]:
            if bp["Pool"] == pool_number:
                results.append(f"{bp['Name']} ({weapon['Name']})")
    return results

# 🔄 Autocomplete for weapon type
async def weapontype_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=wt, value=wt)
        for wt in WEAPON_TYPES
        if current.lower() in wt.lower()
    ]

# ✅ /blueprint command
@tree.command(name="blueprint", description="Look up a blueprint by name")
@app_commands.describe(nameid="Name of the blueprint (e.g., STORM RAGE)")
async def blueprint(interaction: discord.Interaction, nameid: str):
    bp = find_blueprint(nameid)
    if not bp:
        await interaction.response.send_message("❌ Blueprint not found.", ephemeral=True)
        return

    embed = discord.Embed(
        title=bp["blueprint_name"],
        description=f"🔫 **Weapon:** {bp['weapon']}\n📦 **Pool:** {bp['pool']}\n📜 **Status:** {bp['status']}",
        color=discord.Color.blurple()
    )

    class ViewPoolButton(discord.ui.Button):
        def __init__(self):
            super().__init__(label="View Pool", style=discord.ButtonStyle.primary)

        async def callback(self, interaction_button: discord.Interaction):
            pool_bps = get_pool_blueprints(bp["pool"])
            if not pool_bps:
                await interaction_button.response.send_message("No blueprints found in this pool.", ephemeral=True)
                return

            pool_embed = discord.Embed(
                title=f"Pool {bp['pool']} Blueprints",
                description="\n".join(f"**{i+1}.** {name}" for i, name in enumerate(pool_bps)),
                color=discord.Color.green()
            )
            await interaction_button.response.send_message(embed=pool_embed, ephemeral=True)

    view = discord.ui.View()
    view.add_item(ViewPoolButton())

    await interaction.response.send_message(embed=embed, view=view)

# ✅ /pool command with autocomplete
@tree.command(name="pool", description="View all blueprints in a specific pool")
@app_commands.describe(
    number="Pool number (e.g. 1)",
    weapontype="Weapon type filter (e.g. smgs, ars, all)"
)
@app_commands.autocomplete(weapontype=weapontype_autocomplete)
async def pool(interaction: discord.Interaction, number: int, weapontype: str = "all"):
    pool_number = str(number)
    weapontype = weapontype.lower()

    results = get_pool_blueprints(pool_number, weapontype)
    if not results:
        await interaction.response.send_message("❌ No blueprints found for that pool/type.", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"📦 Pool {pool_number} — {weapontype.upper()}",
        description="\n".join(f"**{i+1}.** {name}" for i, name in enumerate(results)),
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

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

