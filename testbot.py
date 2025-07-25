#Required libraries & imports
##################################################################################
import discord
import json
import os
import asyncio
import random
import collections
import time
import logging
import re 

from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands

load_dotenv()
##################################################################################

# Configure logging to theme specific discord.py messages
class DiscordThemeFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()
        if record.name == "discord.client" and "logging in using static token" in message:

            return f"✅ Logged in using static token"
        elif record.name == "discord.gateway" and "has connected to Gateway" in message:
            shard_id = record.args[0] if record.args else "None"
            session_id_match = re.search(r'Session ID: ([a-f0-9]+)', message)
            session_id_str = f" (Session ID: {session_id_match.group(1)})" if session_id_match else ""
            return f"✅ Shard ID {shard_id} has connected to Gateway{session_id_str}"
        if record.name in ['discord.client', 'discord.gateway']:
            return "" 
        
        return super().format(record)
handler = logging.StreamHandler()
handler.setFormatter(DiscordThemeFormatter())

loggers_to_configure = ['discord.client', 'discord.gateway']

for logger_name in loggers_to_configure:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO) 
    if logger.hasHandlers():
        for existing_handler in logger.handlers[:]:
            logger.removeHandler(existing_handler)
    logger.addHandler(handler)
    logger.propagate = False

# Load JSON data
with open("blueprints.json", "r") as f:
    data = json.load(f)

# Constants
WEAPON_TYPES = [
    "assault rifles", 
    "smgs"          ,
    "shotguns"      , 
    "snipers"       ,
    "lmgs"          , 
    "marksman"      , 
    "pistols"       ,
    "launchers"     ,
    "special"       , 
    "melee"         , 
    "all"
]

CATEGORY_MAP = {
    "assault rifles": "1",  
    "smgs"          : "2",            
    "shotguns"      : "3",        
    "lmgs"          : "4",            
    "marksman"      : "5", 
    "snipers"       : "6",       
    "pistols"       : "7",         
    "launchers"     : "8",       
    "special"       : "9",        
    "melee"         : "10"           
}

BASE_IMAGE_PATH = "assets/blueprints/images/"

# Bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Global dictionary
last_ephemeral_messages = {}

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await tree.sync()
    print("✅ Slash commands synced.")
    await bot.change_presence(activity=discord.Game(name="with Blueprints"))
    print("✅ Bot status set to 'Playing with Blueprints'.")

# Rate Limit
EMBED_TIMESTAMPS = collections.deque()
MAX_EMBEDS_PER_PERIOD = 4 # Embed Limit
PERIOD_SECONDS = 35 # Timeout Lengh

def check_and_apply_rate_limit():

    current_time = time.time()

    while EMBED_TIMESTAMPS and EMBED_TIMESTAMPS[0] <= current_time - PERIOD_SECONDS:
        EMBED_TIMESTAMPS.popleft()

    if len(EMBED_TIMESTAMPS) >= MAX_EMBEDS_PER_PERIOD:
        time_left = PERIOD_SECONDS - (current_time - EMBED_TIMESTAMPS[0])
        return True, time_left
    else:
        EMBED_TIMESTAMPS.append(current_time)
        return False, 0
# Delete last ephemeral message
async def send_and_manage_ephemeral(interaction: discord.Interaction, **kwargs):
    """
    Sends an ephemeral message to the user, deleting the previous ephemeral message
    sent by the bot to that user if one exists.
    """
    user_id = interaction.user.id

    # Delete previous ephemeral message if it exists for this user
    if user_id in last_ephemeral_messages:
        try:

            await last_ephemeral_messages[user_id].delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            print(f"Bot lacks permissions to delete ephemeral message for user {user_id}")
        finally:
            del last_ephemeral_messages[user_id]

    # Send the new message
    message = None
    if interaction.response.is_done():
        message = await interaction.followup.send(**kwargs, ephemeral=True)
    else:
        await interaction.response.send_message(**kwargs, ephemeral=True)
        message = await interaction.original_response()

    last_ephemeral_messages[user_id] = message
    return message

# 🔍 Blueprint lookup helper
def find_blueprint(nameid: str):
    nameid_lower = nameid.lower()
    for weapon in data["Weapons"]:
        for bp in weapon["Blueprints"]:

            if bp["Name"].lower() == nameid_lower:
                can_display_image = bp.get("status", "RELEASED") not in ["NOTHING", "NOTEXTURE"]
                image_path = None
                if can_display_image:
                    original_weapon_folder_name = weapon["Name"]
                    original_blueprint_file_name = bp["Name"]
                    name_variants_to_try = [
                        (original_weapon_folder_name, original_blueprint_file_name),
                        (original_weapon_folder_name.replace(" ", "_"), original_blueprint_file_name.replace(" ", "_")),
                    ]
                    final_name_pairs_to_check = []
                    for w_name, bp_name in name_variants_to_try:
                        final_name_pairs_to_check.append((w_name, bp_name))
                        if w_name.lower() != w_name or bp_name.lower() != bp_name:
                            final_name_pairs_to_check.append((w_name.lower(), bp_name.lower()))
                    seen = set()
                    unique_final_name_pairs = []
                    for pair in final_name_pairs_to_check:
                        if pair not in seen:
                            unique_final_name_pairs.append(pair)
                            seen.add(pair)
                    found_image = False
                    attempted_paths = []
                    for w_name, bp_name in unique_final_name_pairs:
                        candidate_image_path = os.path.join(BASE_IMAGE_PATH, w_name, f"{bp_name}.jpg")
                        candidate_image_path_for_url = candidate_image_path.replace('\\', '/')
                        attempted_paths.append(candidate_image_path_for_url)
                        if os.path.exists(candidate_image_path):
                            image_path = candidate_image_path_for_url
                            found_image = True
                            break
                    if not found_image:
                        image_path = None
                return {
                    "weapon": weapon["Name"],
                    "blueprint_name": bp["Name"],
                    "pool": bp["Pool"],
                    "status": bp.get("status", "UNKNOWN"),
                    "image_path": image_path
                }

            full_bp_name = f"{bp['Name']} ({weapon['Name']})".lower()
            if full_bp_name == nameid_lower:
                can_display_image = bp.get("status", "RELEASED") not in ["NOTHING", "NOTEXTURE"]
                image_path = None
                if can_display_image:
                    original_weapon_folder_name = weapon["Name"]
                    original_blueprint_file_name = bp["Name"]
                    name_variants_to_try = [
                        (original_weapon_folder_name, original_blueprint_file_name),
                        (original_weapon_folder_name.replace(" ", "_"), original_blueprint_file_name.replace(" ", "_")),
                    ]
                    final_name_pairs_to_check = []
                    for w_name, bp_name in name_variants_to_try:
                        final_name_pairs_to_check.append((w_name, bp_name))
                        if w_name.lower() != w_name or bp_name.lower() != bp_name:
                            final_name_pairs_to_check.append((w_name.lower(), bp_name.lower()))
                    seen = set()
                    unique_final_name_pairs = []
                    for pair in final_name_pairs_to_check:
                        if pair not in seen:
                            unique_final_name_pairs.append(pair)
                            seen.add(pair)
                    found_image = False
                    attempted_paths = []
                    for w_name, bp_name in unique_final_name_pairs:
                        candidate_image_path = os.path.join(BASE_IMAGE_PATH, w_name, f"{bp_name}.jpg")
                        candidate_image_path_for_url = candidate_image_path.replace('\\', '/')
                        attempted_paths.append(candidate_image_path_for_url)
                        if os.path.exists(candidate_image_path):
                            image_path = candidate_image_path_for_url
                            found_image = True
                            break
                    if not found_image:
                        image_path = None
                return {
                    "weapon": weapon["Name"],
                    "blueprint_name": bp["Name"],
                    "pool": bp["Pool"],
                    "status": bp.get("status", "UNKNOWN"),
                    "image_path": image_path
                }
            unique_value_format = f"{bp['Name']}::{weapon['Name']}::{bp.get('Pool', 'NoPool')}".lower()
            if unique_value_format == nameid_lower:
                can_display_image = bp.get("status", "RELEASED") not in ["NOTHING", "NOTEXTURE"]
                image_path = None
                if can_display_image:
                    original_weapon_folder_name = weapon["Name"]
                    original_blueprint_file_name = bp["Name"]
                    name_variants_to_try = [
                        (original_weapon_folder_name, original_blueprint_file_name),
                        (original_weapon_folder_name.replace(" ", "_"), original_blueprint_file_name.replace(" ", "_")),
                    ]
                    final_name_pairs_to_check = []
                    for w_name, bp_name in name_variants_to_try:
                        final_name_pairs_to_check.append((w_name, bp_name))
                        if w_name.lower() != w_name or bp_name.lower() != bp_name:
                            final_name_pairs_to_check.append((w_name.lower(), bp_name.lower()))
                    seen = set()
                    unique_final_name_pairs = []
                    for pair in final_name_pairs_to_check:
                        if pair not in seen:
                            unique_final_name_pairs.append(pair)
                            seen.add(pair)
                    found_image = False
                    attempted_paths = []
                    for w_name, bp_name in unique_final_name_pairs:
                        candidate_image_path = os.path.join(BASE_IMAGE_PATH, w_name, f"{bp_name}.jpg")
                        candidate_image_path_for_url = candidate_image_path.replace('\\', '/')
                        attempted_paths.append(candidate_image_path_for_url)
                        if os.path.exists(candidate_image_path):
                            image_path = candidate_image_path_for_url
                            found_image = True
                            break
                    if not found_image:
                        image_path = None
                return {
                    "weapon": weapon["Name"],
                    "blueprint_name": bp["Name"],
                    "pool": bp["Pool"],
                    "status": bp.get("status", "UNKNOWN"),
                    "image_path": image_path
                }
    return None

# 📦 Pool blueprint list
def get_pool_blueprints(pool_number: str, weapontype: str = "all"):
    results = []
    seen_values = set() # To track unique values
    for weapon in data["Weapons"]:
        if weapontype != "all":
            if CATEGORY_MAP.get(weapontype, "-1") != weapon["Category"]:
                continue
        for bp in weapon["Blueprints"]:
            if bp["Pool"] == pool_number:

                unique_value = f"{bp['Name']}::{weapon['Name']}::{bp['Pool']}" 
                display_label = f"(Pool **{bp['Pool']}**) (**{weapon['Name']}**) **{bp['Name']}** [`{bp.get('status', 'RELEASED')}`]"
                
                if unique_value not in seen_values: 
                    results.append({"label": display_label, "value": unique_value})
                    seen_values.add(unique_value)
    return results

# 🔄 Autocomplete for weapon type
async def weapontype_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=wt, value=wt)
        for wt in WEAPON_TYPES
        if current.lower() in wt.lower()
    ]

# Define a list of colors to choose from using hexadecimal values or valid attributes
EMBED_COLORS = [
    discord.Color(0x000000),  # Black
    discord.Color.blue(),     # Discord blue
    discord.Color(0xFFFFFF),  # White
    discord.Color.light_grey() # Light grey
]

# ✅ /blueprint command
@tree.command(name="blueprint", description="Look up a blueprint by name")
@app_commands.describe(nameid="Name of the blueprint (e.g., STORM RAGE)")
async def blueprint(interaction: discord.Interaction, nameid: str):
    is_limited, time_left = check_and_apply_rate_limit()
    if is_limited:
        await send_and_manage_ephemeral(
            interaction,
            content=f"Slow down! You can send only {MAX_EMBEDS_PER_PERIOD} embeds every {PERIOD_SECONDS} seconds. Try again in {time_left:.1f} seconds."
        )
        return

    bp = find_blueprint(nameid)
    if not bp:
        await send_and_manage_ephemeral(
            interaction,
            content="❌ Blueprint not found."
        )
        return

    # Choose a random color
    selected_color = random.choice(EMBED_COLORS)

    embed = discord.Embed(
        title=bp["blueprint_name"],
        description=f"📦 **Pool:** **{bp['pool']}**\n🔫 **Weapon:** **{bp['weapon']}**\n✨ **Blueprint:** **{bp['blueprint_name']}**\n📜 **Status:** `{bp['status']}`",
        color=selected_color
    )

    file_to_send = None
    if bp.get("image_path") and os.path.exists(bp["image_path"].replace('/', os.sep)): 
        sanitized_filename = os.path.basename(bp["image_path"]).replace(" ", "_")
        file_to_send = discord.File(bp["image_path"].replace('/', os.sep), filename=sanitized_filename)
        embed.set_image(url=f"attachment://{sanitized_filename}")
    else:
        embed.set_footer(text="No image preview available for this blueprint locally.")


    class ViewPoolButton(discord.ui.Button):
        def __init__(self, pool_number: str, weapon_name: str):
            super().__init__(label="View Model Pool", style=discord.ButtonStyle.primary)
            self.pool_number = pool_number
            self.weapon_name = weapon_name

        async def callback(self, interaction_button: discord.Interaction):
            is_limited, time_left = check_and_apply_rate_limit()
            if is_limited:

                await send_and_manage_ephemeral(
                    interaction_button,
                    content=f"Slow down! You can send only {MAX_EMBEDS_PER_PERIOD} embeds every {PERIOD_SECONDS} seconds. Try again in {time_left:.1f} seconds."
                )
                return

            await interaction_button.response.defer(ephemeral=False)
            weapon_type_string = "all"
            for weapon_data_item in data["Weapons"]:
                if weapon_data_item["Name"] == self.weapon_name:
                    for key, value in CATEGORY_MAP.items():
                        if value == weapon_data_item["Category"]:
                            weapon_type_string = key
                            break
                    break
            all_results_for_pool = get_pool_blueprints(self.pool_number, weapon_type_string)
            if not all_results_for_pool:
                await interaction_button.followup.send("No blueprints found in this pool.", ephemeral=True)
                return
            
            # Choose a random color
            selected_pool_color = random.choice(EMBED_COLORS)

            initial_pool_embed = discord.Embed(
                title=f"📦 Pool {self.pool_number} — {weapon_type_string.upper()}",
                description="Loading blueprints...",
                color=selected_pool_color
            )

            sent_message = await interaction_button.followup.send(
                embed=initial_pool_embed, 
                view=BlueprintPaginationView(all_results_for_pool, self.pool_number, weapon_type_string, initial_pool_embed), 
                ephemeral=False
            )
            await sent_message.delete(delay=90) # 

    class ViewAllFromPoolButton(discord.ui.Button):
        def __init__(self, pool_number: str):
            super().__init__(label="View All Pool Blueprints", style=discord.ButtonStyle.secondary)
            self.pool_number = pool_number

        async def callback(self, interaction_button: discord.Interaction):
            is_limited, time_left = check_and_apply_rate_limit()
            if is_limited:

                await send_and_manage_ephemeral(
                    interaction_button,
                    content=f"Slow down! You can send only {MAX_EMBEDS_PER_PERIOD} embeds every {PERIOD_SECONDS} seconds. Try again in {time_left:.1f} seconds."
                )
                return

            await interaction_button.response.defer(ephemeral=False)
            all_results_for_pool = get_pool_blueprints(self.pool_number, "all")
            if not all_results_for_pool:
                await interaction_button.followup.send("No blueprints found in this pool.", ephemeral=True)
                return
            
            # Choose a random color
            selected_all_pool_color = random.choice(EMBED_COLORS)

            initial_pool_embed = discord.Embed(
                title=f"📦 Pool {self.pool_number} — ALL",
                description="Loading blueprints...",
                color=selected_all_pool_color
            )

            sent_message = await interaction_button.followup.send(
                embed=initial_pool_embed, 
                view=BlueprintPaginationView(all_results_for_pool, self.pool_number, "all", initial_pool_embed), 
                ephemeral=False
            )
            await sent_message.delete(delay=90)

    view = discord.ui.View()
    view.add_item(ViewPoolButton(bp["pool"], bp["weapon"]))
    view.add_item(ViewAllFromPoolButton(bp["pool"]))

    await send_and_manage_ephemeral(
        interaction,
        embed=embed,
        view=view,
        file=file_to_send if file_to_send else discord.utils.MISSING
    )

class BlueprintSelect(discord.ui.Select):
    def __init__(self, page_blueprints: list):
        options = []

        for bp_data in page_blueprints:

            options.append(discord.SelectOption(label=bp_data["label"], value=bp_data["value"]))

        super().__init__(
            placeholder="Select a blueprint to view details...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="blueprint_select_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        is_limited, time_left = check_and_apply_rate_limit()
        if is_limited:

            await send_and_manage_ephemeral(
                interaction,
                content=f"Slow down! You can send only {MAX_EMBEDS_PER_PERIOD} embeds every {PERIOD_SECONDS} seconds. Try again in {time_left:.1f} seconds."
            )
            return

        selected_unique_value = self.values[0] 
        
        try:
            bp_name, weapon_name, _ = selected_unique_value.split("::")

            lookup_name = f"{bp_name} ({weapon_name})"
            bp_details = find_blueprint(lookup_name)
        except ValueError:

            bp_details = find_blueprint(selected_unique_value) 
        
        if bp_details:
            # Choose a random color
            selected_blueprint_color = random.choice(EMBED_COLORS)

            embed = discord.Embed(
                title=bp_details["blueprint_name"],
                description=f"📦 **Pool:** **{bp_details['pool']}**\n🔫 **Weapon:** **{bp_details['weapon']}**\n✨ **Blueprint:** **{bp_details['blueprint_name']}**\n📜 **Status:** `{bp_details['status']}`",
                color=selected_blueprint_color
            )
            
            file_to_send = None
            if bp_details.get("image_path") and os.path.exists(bp_details["image_path"].replace('/', os.sep)):
                sanitized_filename = os.path.basename(bp_details["image_path"]).replace(" ", "_")
                file_to_send = discord.File(bp_details["image_path"].replace('/', os.sep), filename=sanitized_filename)
                embed.set_image(url=f"attachment://{sanitized_filename}")
            else:
                embed.set_footer(text="No image preview available for this blueprint locally.")

            await send_and_manage_ephemeral(
                interaction,
                embed=embed,
                file=file_to_send if file_to_send else discord.utils.MISSING
            )
        else:

            await send_and_manage_ephemeral(
                interaction,
                content="❌ Could not find details for the selected blueprint."
            )

class BlueprintPaginationView(discord.ui.View):
    def __init__(self, all_blueprints: list, pool_number: str, weapontype: str, initial_embed: discord.Embed):
        super().__init__(timeout=180)
        self.all_blueprints = all_blueprints 
        self.pool_number = pool_number
        self.weapontype = weapontype
        self.current_page = 0
        self.max_options_per_page = 25
        self.total_pages = (len(all_blueprints) + self.max_options_per_page - 1) // self.max_options_per_page if all_blueprints else 1
        self.embed = initial_embed
        
        self._update_items()

    def _get_current_page_blueprints(self) -> list:
        start_index = self.current_page * self.max_options_per_page
        end_index = start_index + self.max_options_per_page

        return self.all_blueprints[start_index:end_index]

    def _update_items(self):
        self.clear_items()

        current_page_bps = self._get_current_page_blueprints()
        
        if current_page_bps:

            embed_description = "\n".join(f"{bp_data['label']}" for i, bp_data in enumerate(current_page_bps))
            if self.total_pages > 1:
                embed_description += f"\n\n(Page {self.current_page + 1}/{self.total_pages})"

            embed_description += "\n\n*Public messages are set to delete in 90 seconds to prevent spam.*"
            self.embed.description = embed_description
        else:
            self.embed.description = "No blueprints found on this page."

            embed_description = "No blueprints found on this page."
            embed_description += "\n\n*Public messages are set to delete in 90 seconds to prevent spam.*"
            self.embed.description = embed_description

        if current_page_bps:
            self.add_item(BlueprintSelect(current_page_bps))
# ⏭️🔙 New and Back Logic
        self.add_item(discord.ui.Button(
            label="◀️ Previous Page",
            style=discord.ButtonStyle.secondary,
            custom_id="prev_page_button",
            disabled=(self.current_page == 0)
        ))

        self.add_item(discord.ui.Button(
            label=f"Page {self.current_page + 1}/{self.total_pages}",
            style=discord.ButtonStyle.secondary,
            custom_id="page_indicator",
            disabled=True
        ))

        self.add_item(discord.ui.Button(
            label="Next Page ▶️",
            style=discord.ButtonStyle.secondary,
            custom_id="next_page_button",
            disabled=(self.current_page == self.total_pages - 1)
        ))

    async def previous_page(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            if self.current_page > 0:
                self.current_page -= 1
                self._update_items()
                await interaction.edit_original_response(embed=self.embed, view=self)
            else:
                await interaction.followup.send("You are already on the first page.", ephemeral=True)
        except Exception as e:
            print(f"Error in previous_page: {e}")
            await interaction.followup.send("An error occurred while trying to go to the previous page.", ephemeral=True)

    async def next_page(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer()
            if self.current_page < self.total_pages - 1:
                self.current_page += 1
                self._update_items()
                await interaction.edit_original_response(embed=self.embed, view=self)
            else:

                await interaction.followup.send("You are already on the last page.", ephemeral=True)
        except Exception as e:
            print(f"Error in next_page: {e}")
            await interaction.followup.send("An error occurred while trying to go to the next page.", ephemeral=True)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.data and "custom_id" in interaction.data:
            custom_id = interaction.data["custom_id"]
            if custom_id == "prev_page_button":
                await self.previous_page(interaction)
                return False
            elif custom_id == "next_page_button":
                await self.next_page(interaction)
                return False
        return True

# ✅ /pool command
@tree.command(name="pool", description="View all blueprints in a specific pool")
@app_commands.describe(
    number="Pool number (e.g. 1)",
    weapontype="Weapon type filter (e.g. smgs, ars, all)"
)
@app_commands.autocomplete(weapontype=weapontype_autocomplete)
async def pool(interaction: discord.Interaction, number: int, weapontype: str = "all"):
    is_limited, time_left = check_and_apply_rate_limit()
    if is_limited:
        await send_and_manage_ephemeral(
            interaction,
            content=f"Slow down! You can send only {MAX_EMBEDS_PER_PERIOD} embeds every {PERIOD_SECONDS} seconds. Try again in {time_left:.1f} seconds."
        )
        return

    pool_number = str(number)
    weapontype = weapontype.lower()

    all_results = get_pool_blueprints(pool_number, weapontype)
    
    if not all_results:
        await send_and_manage_ephemeral(
            interaction,
            content="❌ No blueprints found for that pool/type."
        )
        return

    selected_initial_pool_color = random.choice(EMBED_COLORS)

    initial_embed = discord.Embed(
        title=f"📦 Pool **{pool_number}** — {weapontype.upper()}",
        description="Loading blueprints...",
        color=selected_initial_pool_color
    )
    
    view = BlueprintPaginationView(all_results, pool_number, weapontype, initial_embed)

    await interaction.response.send_message(embed=initial_embed, view=view, delete_after=90)

# New command to search blueprints by status
@tree.command(name="search_status", description="Search blueprints by their status")
@app_commands.describe(status="Choose a blueprint status (RELEASED, UNRELEASED, NOTHING, NOTEXTURE)")
@app_commands.choices(status=[
    app_commands.Choice(name="RELEASED", value="RELEASED"),
    app_commands.Choice(name="UNRELEASED", value="UNRELEASED"),
    app_commands.Choice(name="NOTHING", value="NOTHING"),
    app_commands.Choice(name="NOTEXTURE", value="NOTEXTURE")
])
async def search_status(interaction: discord.Interaction, status: app_commands.Choice[str]):
    is_limited, time_left = check_and_apply_rate_limit()
    if is_limited:
        await send_and_manage_ephemeral(
            interaction,
            content=f"Slow down! You can send only {MAX_EMBEDS_PER_PERIOD} embeds every {PERIOD_SECONDS} seconds. Try again in {time_left:.1f} seconds."
        )
        return

    selected_status = status.value
    results = []
    seen_values = set() # To track unique values
    for weapon in data["Weapons"]:
        for bp in weapon["Blueprints"]:
            blueprint_status = bp.get("status", "RELEASED") 
            if blueprint_status == selected_status:

                unique_value = f"{bp['Name']}::{weapon['Name']}::{bp.get('Pool', 'NoPool')}" 
                display_label = f"(Pool **{bp.get('Pool', 'N/A')}**) (**{weapon['Name']}**) **{bp['Name']}** [`{blueprint_status}`]"
                if unique_value not in seen_values: # Check for duplicates
                    results.append({"label": display_label, "value": unique_value})
                    seen_values.add(unique_value)

    if not results:
        await send_and_manage_ephemeral(
            interaction,
            content=f"❌ No blueprints found with status: {selected_status}."
        )
        return

    selected_color = random.choice(EMBED_COLORS)
    initial_embed = discord.Embed(
        title=f"📜 Blueprints with Status: {selected_status}",
        description="Loading blueprints...",
        color=selected_color
    )

    view = BlueprintPaginationView(results, "N/A", "N/A", initial_embed)

    await interaction.response.send_message(
        embed=initial_embed,
        view=view,
        ephemeral=False, 
        delete_after=90 
    )

@tree.command(name="website", description="View the Blueprint Database Website")
async def website(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🔗 Visit the Blueprint Database",
        description="Check out all weapon blueprints and pools on the full website:",
        color=discord.Color.teal()
    )
    embed.add_field(
        name="🌐 Website",
        value="[parsed.top](https://www.parsed.top/)",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="howto", description="Learn how blueprint pulling works")
@app_commands.describe(gamemode="Choose a gamemode: wz/mp or zombies")
@app_commands.choices(gamemode=[
    app_commands.Choice(name="Warzone / Multiplayer", value="wz"),
    app_commands.Choice(name="Zombies", value="zombies")
])
async def howto(interaction: discord.Interaction, gamemode: app_commands.Choice[str]):
    if gamemode.value == "wz":
        embed = discord.Embed(
            title="🎮 Blueprint Pulling — MP & Warzone Method",
            description=(
                "**Working Universally through MP and WZ**\n\n"
                "1️⃣ **Make a Setup Gun** (base of the gun you want to pull)\n"
                "(create new -> delete build -> add att [Same As Receiver slots] -> name build Setup)\n\n"
                "2️⃣ **Find A Print you own** in the same pool as the print you wanna pull, create new build and then fill the same att slots as the Receiver.\n"
                "(Optional: Rename to Receiver)\n\n"
                "3️⃣ **Equip the Receiver** and then **equip the Unowned Camo**\n"
                "(If you are using DB then this is the same just DB shotgun with only DB)\n"
                "⚠️ {RECOMMENDED: DUPE THE UNOWNED CAMO TO PREVENT WIPING!}\n\n"
                "4️⃣ **Kill yourself** and then **requip that Build (setup)**\n\n"
                "5️⃣ **Finally equip the unowned camo again to save it**\n"
                "(or just equip a att 2x on build)\n\n"
                "⚠️ PLEASE KEEP IN MIND IF YOU ARE IN A BROKEN STATE THEN IN ORDER TO SAVE BLUEPRINTS YOU MUST DELETE ANY BUILD AND THEN SAVE IT (THE SAME WAY THE CAMO SWAP SAVE WORKS)\n\n"
                "💡 keep it noted that prints are pulled in half's and currently there is not a way the pull the full prints in one method\n"
                "if you wish to get the full print you must find the right Receiver attachment combo that pulls the full print (likely hood 1/20 roughly)\n"
                "but it doesn't matter just throw a nice camo on and you'll be set! 😎\n\n"
            ),
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url="attachment://logo.png")
        embed.add_field(
            name="🌐 Browse Blueprint Pools",
            value="[parsed.top](https://www.parsed.top/)", inline=False
        )
        embed.set_footer(text="Use /pool and /blueprint for fast lookups.")

        file_to_send = discord.File("assets/logo.png", filename="logo.png")


    elif gamemode.value == "zombies":
        embed = discord.Embed(
            title="🧟 Zombies Blueprint Pulling (Split-Screen Exploit)",
            description=(
                "⚠️ First, it’s important to know that this exploit only works on **PS5 and Xbox Series X/S**, last-gen consoles and PC players do not have access to split-screen, so this won’t work for you.\n"
                "Also, Player 2 doesn’t need a leveled-up account, but having one makes the pulls easier. If Player 2 uses a fresh account, you may need to perform an extra glitch to equip locked weapons in your Zombies loadout.\n\n"
                "🔧 Now, here’s how it comes:\n\n"
                "1️⃣ **Launch Call of Duty** and go into Zombies mode.\n\n"
                "2️⃣ **Connect a second controller** and sign in with your secondary profile.\n\n"
                "3️⃣ **Set up Player 2’s loadout** with the weapon you want to pull prints for (like the LADRA).\n\n"
                "4️⃣ **Back out to the screen** so you can edit your Controller 1 (main account) loadout.\n\n"
                "5️⃣ On your main account, **equip the blueprint you want to use** to pull the print.\n\n"
                "6️⃣ After that, **back out to the main menu** where you can select Multiplayer, Zombies, or Campaign.\n\n"
                "7️⃣ With Controller 2, **select Zombies mode**.\n\n"
                "8️⃣ Finally, **go back to Player 1’s main loadout**, and you should see the print you were trying to pull, as long as you’ve followed everything correctly.\n\n"
        ),
            color=discord.Color.red()
        )
        embed.set_thumbnail(url="attachment://logo.png")
        embed.add_field(
            name="🌐 Browse Blueprint Pools",
            value="[parsed.top](https://www.parsed.top/)", inline=False
        )
        embed.set_footer(text="Use /pool to explore blueprints across pools and categories.")

        file_to_send = discord.File("assets/logo.png", filename="logo.png")

    await interaction.response.send_message(embed=embed, ephemeral=True, file=file_to_send)

#Pool Explain Command
@tree.command(name="pool-explain", description="Learn how blueprint pulling works for pools")
async def pool_explain(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📦 Blueprint Pulling — Pool Explanation",
        description=(
            "Assuming you're familiar with the pulling exploit, here's how it would work:\n\n"
            "Let's walk through an example. We'll use the **C9 \"THE PAINTSTORM\"** variant, which is stored in **Pool 15**.\n\n"
            "1️⃣ You'd transfer the **C9** to your alternate account.\n\n"
            "2️⃣ Then, on your main account, you'd pick any blueprint that's also stored in **Pool 15** (i.e., **TANTTO .22 \"FISSION\"**) and perform the pull exploit.\n\n"
            "3️⃣ You should then successfully pull the\n\n"
            "**C9 \"The PAINTSTORM\"**.\n\n"
        ),
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url="attachment://logo.png")
    embed.add_field(
        name="🌐 Browse Blueprint Pools",
        value="[parsed.top](https://www.parsed.top/)", inline=False
    )
    embed.set_footer(text="Use /pool to explore blueprints across pools and categories.")

    file_to_send = discord.File("assets/logo.png", filename="logo.png")

    await interaction.response.send_message(embed=embed, ephemeral=True, file=file_to_send)

# New help command
@tree.command(name="help", description="Shows a list of all available commands and their usage.")
async def help_command(interaction: discord.Interaction):
    selected_color = random.choice(EMBED_COLORS)

    embed = discord.Embed(
        title="🤖 Blueprint Bot Commands",
        description="Here's a list of commands you can use with the Blueprint Bot:",
        color=selected_color
    )

    embed.add_field(
        name="`/blueprint <nameid>`",
        value="Look up a blueprint by its name (e.g., `/blueprint STORM RAGE`).",
        inline=False
    )
    embed.add_field(
        name="`/pool <number> [weapontype]`",
        value="View all blueprints in a specific pool. You can filter by weapon type (e.g., `/pool 1 smgs`).",
        inline=False
    )
    embed.add_field(
        name="`/search_status <status>`",
        value="Search blueprints by their release status (e.g., `/search_status RELEASED`).",
        inline=False
    )
    embed.add_field(
        name="`/howto <gamemode>`",
        value="Learn how blueprint pulling works for Warzone/Multiplayer or Zombies (e.g., `/howto wz`).",
        inline=False
    )
    embed.add_field(
        name="`/pool-explain`",
        value="Get an explanation on how blueprint pulling works specifically for pools.",
        inline=False
    )
    embed.add_field(
        name="`/website`",
        value="Get a link to the full Blueprint Database website.",
        inline=False
    )
    embed.add_field(
        name="`/help`",
        value="Displays this help message.",
        inline=False
    )

    # Set the thumbnail and footer for consistency
    file_to_send = discord.File("assets/logo.png", filename="logo.png")
    embed.set_thumbnail(url="attachment://logo.png")
    embed.set_footer(text="Use these commands to navigate the blueprint database!")

    await interaction.response.send_message(embed=embed, ephemeral=True, file=file_to_send)
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
