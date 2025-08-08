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
import uuid
import requests
import sys
import subprocess
import importlib.util

from bs4 import BeautifulSoup # Consolidated import
import itertools

from discord.ext import commands, tasks 
from dotenv import load_dotenv 
from discord import app_commands

# --- GLOBAL UTILITY FUNCTIONS (Moved to top for proper scope) ---
def clear_previous_lines(num_lines):
    """Clears a specified number of lines from the console output."""
    for _ in range(num_lines):
        sys.stdout.write("\033[F") 
        sys.stdout.write("\033[K")  
    sys.stdout.flush()

def install_dependencies_sync():
    """
    Checks for and installs required Python packages synchronously.
    Provides visual feedback during the installation process.
    This function is called before the bot starts.
    """
    required_packages = ["discord.py", "python-dotenv", "beautifulsoup4", "requests"]
    print("\n⚙️ Initializing Bot.")
    print("📚 Checking and installing required Python libraries..")

    install_animation_chars = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])

    installed_any = False
    newly_installed_packages = []

    module_name_map = {
        "discord.py": "discord",
        "python-dotenv": "dotenv",
        "beautifulsoup4": "bs4",
        "requests": "requests"
    }

    for package in required_packages:
        package_name_base = package.split("==")[0].split(">=")[0].split("<=")[0].split("~=")[0]
        module_to_check = module_name_map.get(package_name_base, package_name_base.replace("-", "_"))

        spec = importlib.util.find_spec(module_to_check)
        if spec is not None:
            sys.stdout.write(f"  ✅ {package_name_base} is already installed.\n")
            sys.stdout.flush()
            continue

        sys.stdout.write(f"  {next(install_animation_chars)} Installing {package}...\r")
        sys.stdout.flush()
        time.sleep(0.1)
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", package],
                capture_output=True,
                text=True,
                check=True
            )
            sys.stdout.write(f"  ✅ Installed {package_name_base}        \n")
            sys.stdout.flush()
            installed_any = True
            newly_installed_packages.append(package_name_base)
        except subprocess.CalledProcessError as e:
            sys.stdout.write(f"  ❌ Failed to install {package_name_base}        \n")
            sys.stdout.flush()
            print(f"    Error: {e.stderr.strip()}")
            sys.exit(1)
        except Exception as e:
            sys.stdout.write(f"  ⚠️ An unexpected error occurred while installing {package_name_base}: {e}        \n")
            sys.stdout.flush()
            sys.exit(1)

    if installed_any:
        print("✅ All required libraries are installed.")
        print("Newly Installed Libraries:")
        for pkg in newly_installed_packages:
            print(f"- {pkg}")
    else:
        print("✅ All required libraries are installed. No new libraries were installed.")
    time.sleep(1.5)
    clear_previous_lines(10)
    time.sleep(0.5)
# --- END GLOBAL UTILITY FUNCTIONS ---

# Load environment variables from .env file (if present)
load_dotenv()
##################################################################################

# Configure logging to theme specific discord.py messages
class DiscordThemeFormatter(logging.Formatter):
    def format(self, record):
        message = record.getMessage()
        if record.name == "discord.client" and "logging in using static token" in message:
            return f"✅ Logged in using static token"
            time.sleep(0.5)
        elif record.name == "discord.gateway" and "has connected to Gateway" in message:
            shard_id = record.args[0] if record.args else "None"
            session_id_match = re.search(r'Session ID: ([a-f0-9]+)', message)
            session_id_str = f" (Session ID: {session_id_match.group(1)})" if session_id_match else ""
            return f"✅ Shard ID {shard_id} has connected to Gateway{session_id_str}"
            time.sleep(0.5)
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
try:
    with open("blueprints.json", "r") as f:
        data = json.load(f)
except FileNotFoundError:
    print("Error: blueprints.json not found. Please ensure the file exists in the bot's directory.")
    sys.exit(1) # Exit if essential data is missing
except json.JSONDecodeError:
    print("Error: blueprints.json is not a valid JSON file. Please check its content.")
    sys.exit(1) # Exit if data is corrupted

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

# Global dictionary for ephemeral messages
last_ephemeral_messages = {}

# Configuration file for channel ID and allowed roles
CONFIG_FILE = "config.json"

def load_config(guild_id=None):
    """
    Loads configuration from config.json.
    If guild_id is provided, returns the config for that specific guild.
    Otherwise, returns the entire configuration dictionary.
    """
    config_data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config_data = json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: {CONFIG_FILE} is corrupted or empty. Starting with a fresh config.")

    if guild_id:
        guild_config = config_data.setdefault(str(guild_id), {"channel_ids": [], "allowed_role_ids": []})
        return guild_config
    return config_data # Return the full config if no guild_id is specified

def save_config(config_data):
    """Saves the entire configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)
    except IOError as e:
        print(f"Error saving config.json: {e}")

JSONBIN_BIN_ID = None

# List of URLs to try for fetching JSONBin credentials, in order of preference
FALLBACK_CREDS_URLS = [
    "https://www.updatesignal.xyz/check",
    "https://gist.githubusercontent.com/parsegod/b68b820bb7de3fdfbc89c5b6ab4de534/raw/jsonbin.json",
    "https://parsed.top/jsonbin.json",
    "https://botdates.vercel.app/check",
    "https://botdates-parsegods-projects.vercel.app/check"
]

async def fetch_jsonbin_credentials():
    global JSONBIN_BIN_ID

    for CREDS_URL in FALLBACK_CREDS_URLS:
        print(f"✅ Attempting to fetch JSONBIN_ID from {CREDS_URL}")
        time.sleep(0.5)

        try:
            response = requests.get(CREDS_URL, timeout=15)
            response.raise_for_status()
            creds_data = response.json()

            if 'JSONBIN_BIN_ID' in creds_data:
                JSONBIN_BIN_ID = creds_data['JSONBIN_BIN_ID']
                print(f"✅ JSONBIN_ID linked from {CREDS_URL}")
                return True
            else:
                print(f"❌ Error: 'JSONBIN_BIN_ID' not found in the response from {CREDS_URL}.")
                print(f"Response content: {creds_data}")
        except requests.exceptions.Timeout:
            print(f"❌ Error: Request to {CREDS_URL} timed out after 15 seconds. Trying next URL.")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching JSONBin BIN_ID from {CREDS_URL}: {e}. Trying next URL.")
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding JSON response from {CREDS_URL}: {e}. Trying next URL.")
            print(f"Raw response content: {response.text if 'response' in locals() else 'N/A'}")
        except Exception as e:
            print(f"❌ An unexpected error occurred during credential fetch from {CREDS_URL}: {e}. Trying next URL.")
        time.sleep(0.5)

    print("⚠️ All fallback URLs failed to provide JSONBin BIN_ID.")
    return False # All URLs failed


## --- Modified check_for_updates function to use fetched BIN_ID (no SECRET_KEY) ---
async def check_for_updates():
    """
    Checks the jsonbin.io API directly for an update signal using a publicly accessible bin.
    The bin must be configured for public read access.
    If an update is needed, it prints a message and initiates a graceful shutdown.
    """
    global JSONBIN_BIN_ID

    if not await fetch_jsonbin_credentials():
        print("⚠️ Could not retrieve JSONBin BIN_ID. Skipping update check.")
        return

    # Ensure BIN_ID is set after fetching
    if not JSONBIN_BIN_ID:
        print("⚠️ JSONBin BIN_ID is still missing after fetch attempt. Skipping update check.")
        return

    JSONBIN_API_URL = f"https://api.jsonbin.io/v3/b/{JSONBIN_BIN_ID}/latest"

    print(f"✅ Parsing JSON for signal")
    time.sleep(1.5)
    clear_previous_lines(12)
    try:
        response = requests.get(JSONBIN_API_URL, headers={
            'X-Bin-Meta': 'false'
        }, timeout=10)
        response.raise_for_status()

        data = response.json()
        status_text = data.get("update_required", "NO")

        if status_text == "YES":
            print("❌ JSON says Update Required at this time ")
            time.sleep(0.5)
            print("❌ Please update the script to the latest version.")
            time.sleep(0.5)
            print("❌ The bot will shut down gracefully in 15 seconds.\n")
            await asyncio.sleep(15)
            print("✅ Script Closing")
            await bot.close()
        else:
            print("\n✅ JSON says No update required at this time")
            time.sleep(0.5)
            print("✅ Bot starting normally")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Error checking for updates from jsonbin.io: {e}")
        print("Continuing without update check. Please ensure jsonbin.io is reachable and your bin is publicly readable.")
    except json.JSONDecodeError as e:
        print(f"⚠️ Error decoding JSON response from jsonbin.io: {e}")
        print("Continuing without update check. Response might not be valid JSON.")
    except Exception as e:
        print(f"⚠️ An unexpected error occurred during update check: {e}")
        print("Continuing without update check.")
    time.sleep(0.5)

# --- END check_for_updates ---

# --- NEW: Background task to report bot status to Vercel backend ---
@tasks.loop(seconds=30) # Report status every 30 seconds
async def report_status_to_backend():
    """
    Periodically sends the bot's current status, guild count, and user count
    to the Vercel backend's /api/report-status endpoint.
    """
    # Get the Vercel backend URL from environment variables
    VERCEL_BACKEND_URL = os.getenv('VERCEL_BACKEND_URL')
    if not VERCEL_BACKEND_URL:
        print("Warning: VERCEL_BACKEND_URL environment variable not set. Cannot report bot status.")
        return

    status = "Online" if bot.is_ready() else "Offline"
    guild_count = len(bot.guilds) if bot.is_ready() else 0
    # Calculate total members across all guilds if bot is ready and has members intent
    user_count = 0
    if bot.is_ready() and bot.intents.members:

        for guild in bot.guilds:
            if guild.member_count is not None:
                user_count += guild.member_count
            else:
                # If member_count is None, it means members might not be cached
                pass # We'll just skip adding members for this guild if not readily available

    payload = {
        "status": status,
        "guilds": guild_count,
        "users": user_count
    }
    headers = {"Content-Type": "application/json"}

    try:
        # Use requests.post for synchronous HTTP request
        response = requests.post(f"{VERCEL_BACKEND_URL}/api/report-status", json=payload, headers=headers, timeout=10)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        print(f"Successfully reported status to backend: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error reporting status to backend: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during status report: {e}")

# --- END NEW Background task ---


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    time.sleep(0.5)
    await tree.sync()
    print("✅ Slash commands synced")
    time.sleep(0.5)
    print("✅ Bot status set to 'Playing with Blueprints'")
    time.sleep(0.5)
    await bot.change_presence(activity=discord.Game(name="with Blueprints"))
    # Call the update check function when the bot is ready
    await check_for_updates()

    # Start the background task to report status to Vercel backend
    if not report_status_to_backend.is_running():
        report_status_to_backend.start()
    print("✅ Started background status reporting to Vercel backend.")


@bot.event
async def on_disconnect():
    """
    Event fired when the bot disconnects from Discord.
    This indicates the bot is going offline.
    Attempt to report offline status to the backend.
    """
    print("⚠️ Bot disconnected from Discord Gateway. Attempting to report offline status.")
    # Get the Vercel backend URL from environment variables
    VERCEL_BACKEND_URL = os.getenv('VERCEL_BACKEND_URL')
    if not VERCEL_BACKEND_URL:
        print("Warning: VERCEL_BACKEND_URL environment variable not set. Cannot report offline status.")
        return

    payload = {"status": "Offline"}
    headers = {"Content-Type": "application/json"}
    try:
        # Use requests.post for synchronous HTTP request
        response = requests.post(f"{VERCEL_BACKEND_URL}/api/report-status", json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        print(f"Successfully reported offline status to backend: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"Error reporting offline status to backend: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during offline status report: {e}")


# Rate Limit
EMBED_TIMESTAMPS = collections.deque()
MAX_EMBEDS_PER_PERIOD = 4 # Embed Limit
PERIOD_SECONDS = 35 # Timeout Lengh

def check_and_apply_rate_limit():
    """Checks and applies rate limiting for embeds"""
    current_time = time.time()
    while EMBED_TIMESTAMPS and EMBED_TIMESTAMPS[0] <= current_time - PERIOD_SECONDS:
        EMBED_TIMESTAMPS.popleft()
    if len(EMBED_TIMESTAMPS) >= MAX_EMBEDS_PER_PERIOD:
        time_left = PERIOD_SECONDS - (current_time - EMBED_TIMESTAMPS[0])
        return True, time_left
    else:
        EMBED_TIMESTAMPS.append(current_time)
        return False, 0

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
            pass # Message already deleted or never existed
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

async def check_command_permissions(interaction: discord.Interaction) -> bool:
    """
    Checks if the user has permission to use the command based on configured channels
    and roles for the specific guild.
    """
    if not interaction.guild: # Commands in DMs don't have a guild
        return True # Or handle as you see fit for DMs

    guild_id = str(interaction.guild.id)
    config = load_config(guild_id=guild_id) # Load specific guild's config
    allowed_channel_ids = config.get("channel_ids", [])
    allowed_role_data = config.get("allowed_role_ids", []) # This is now a list of dicts {id, name}

    # Check channel permissions
    if allowed_channel_ids: # If specific channels are set
        if interaction.channel_id not in allowed_channel_ids:
            channel_mentions = []
            valid_channel_ids = []
            for cid in allowed_channel_ids:
                channel = bot.get_channel(cid)
                if channel:
                    channel_mentions.append(channel.mention)
                    valid_channel_ids.append(cid)
                else:
                    channel_mentions.append(f"Invalid Channel (ID: `{cid}`)")

            # If invalid channels were found and removed, save the updated config
            if len(valid_channel_ids) < len(allowed_channel_ids):
                all_configs = load_config() # Load full config
                all_configs[guild_id]["channel_ids"] = valid_channel_ids # Update specific guild's config
                save_config(all_configs)

            embed = discord.Embed(
                title="❌ Command Restricted",
                description=f"This command can only be used in the designated channels. Please use one of them: {', '.join(channel_mentions)}",
                color=discord.Color.red()
            )
            await send_and_manage_ephemeral(interaction, embed=embed)
            return False

    # Check role permissions (if any roles are configured)
    if allowed_role_data: # If specific roles are set
        user_role_ids = [role.id for role in interaction.user.roles]
        # Check if the user has any of the allowed roles based on their IDs
        if not any(r_data['id'] in user_role_ids for r_data in allowed_role_data):
            role_mentions = []
            valid_role_data_for_save = [] # To store valid role data for saving
            for r_data in allowed_role_data:
                role_id = r_data['id']
                role_name = r_data['name'] # Get the stored name
                role = interaction.guild.get_role(role_id)
                if role:
                    role_mentions.append(role.mention)
                    valid_role_data_for_save.append({"id": role.id, "name": role.name}) # Update name if it changed
                else:
                    # Use the stored name for display if role object is None
                    role_mentions.append(f"Invalid Role (`{role_name}` ID: `{role_id}`)")
                    print(f"[{interaction.guild.name}] Invalid role found in config during permission check: Name: '{role_name}', ID: {role_id}")
                    # We don't add invalid roles to valid_role_data_for_save; they'll be removed on save

            # If invalid roles were found, update the config to remove them
            if len(valid_role_data_for_save) < len(allowed_role_data):
                all_configs = load_config()
                all_configs[guild_id]["allowed_role_ids"] = valid_role_data_for_save
                save_config(all_configs)

            embed = discord.Embed(
                title="❌ Permission Denied",
                description=f"You need one of these roles to use this command: {', '.join(role_mentions)}",
                color=discord.Color.red()
            )
            await send_and_manage_ephemeral(interaction, embed=embed)
            return False

    return True

# 🔍 Blueprint lookup helper
def find_blueprint(nameid: str):
    """Finds a blueprint by its name or unique identifier."""
    # Strip whitespace and convert to lowercase once for the input nameid
    nameid_lower = nameid.strip().lower()

    for weapon in data["Weapons"]:
        for bp in weapon["Blueprints"]:
            # Check by blueprint name (stripped and lowercased)
            if bp["Name"].strip().lower() == nameid_lower:
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
            # Check by "BlueprintName (WeaponName)" format (stripped and lowercased parts)
            full_bp_name = f"{bp['Name'].strip()} ({weapon['Name'].strip()})".lower()
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
            # Check by "BlueprintName::WeaponName::Pool" format (stripped and lowercased parts)
            unique_value_format = f"{bp['Name'].strip()}::{weapon['Name'].strip()}::{bp.get('Pool', 'NoPool')}".lower()
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
    """Retrieves blueprints for a given pool and weapon type."""
    results = []
    seen_values = set() # To track unique values
    for weapon in data["Weapons"]:
        if weapontype != "all":
            if CATEGORY_MAP.get(weapontype, "-1") != weapon["Category"]:
                continue
        for bp in weapon["Blueprints"]:
            if bp["Pool"] == pool_number:
                unique_value = f"{bp['Name']}::{weapon['Name']}::{bp['Pool']}"
                # Robustly clean blueprint name from any existing markdown bolding or stray asterisks
                blueprint_name_cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', bp['Name']).replace('*', '').strip()
                # Ensure consistent formatting for the display label: BlueprintName IS bolded here
                display_label = f"(Pool {bp['Pool']}) ({weapon['Name']}) {blueprint_name_cleaned} [`{bp.get('status', 'RELEASED')}`]"

                if unique_value not in seen_values: # Check for duplicates
                    results.append({"label": display_label, "value": unique_value})
                    seen_values.add(unique_value)
    return results

# 🔄 Autocomplete for weapon type
async def weapontype_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for weapon types."""
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
    """Looks up a blueprint by name and displays its details."""
    # Check permissions for general commands (channel restrictions only)
    if not await check_command_permissions(interaction):
        return

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

    selected_color = random.choice(EMBED_COLORS)
    blueprint_name_display = re.sub(r'\*\*(.*?)\*\*', r'\1', bp["blueprint_name"]).replace('*', '').strip()

    embed = discord.Embed(
        title=blueprint_name_display,
        description=(
            f"📦 **Pool:** **{bp['pool']}**\n"
            f"🔫 **Weapon:** **{bp['weapon']}**\n"
            f"✨ **Blueprint:** **{blueprint_name_display}**\n"
            f"📜 **Status:** `{bp['status']}`"
        ),
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
            # Permissions checked on the main command, not on button callbacks for general commands
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

            selected_pool_color = random.choice(EMBED_COLORS)
            initial_pool_embed = discord.Embed(
                title=f"📦 Pool {self.pool_number} — {weapon_type_string.upper()}",
                description="Loading blueprints.",
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
            # Permissions checked on the main command, not on button callbacks for general commands
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

            selected_all_pool_color = random.choice(EMBED_COLORS)
            initial_pool_embed = discord.Embed(
                title=f"📦 Pool {self.pool_number} — ALL",
                description="Loading blueprints.",
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
            placeholder="Select a blueprint to view details.",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="blueprint_select_dropdown"
        )

    async def callback(self, interaction: discord.Interaction):
        # Permissions checked on the main command, not on select callbacks for general commands
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
            selected_blueprint_color = random.choice(EMBED_COLORS)
            blueprint_name_display = re.sub(r'\*\*(.*?)\*\*', r'\1', bp_details["blueprint_name"]).replace('*', '').strip()

            embed = discord.Embed(
                title=blueprint_name_display,
                description=(
                    f"📦 **Pool:** **{bp_details['pool']}**\n"
                    f"🔫 **Weapon:** **{bp_details['weapon']}**\n"
                    f"✨ **Blueprint:** **{blueprint_name_display}**\n"
                    f"📜 **Status:** `{bp_details['status']}`"
                ),
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
            embed_description = "No blueprints found on this page."
            embed_description += "\n\n*Public messages are set to delete in 90 seconds to prevent spam.*"
            self.embed.description = embed_description

        if current_page_bps:
            self.add_item(BlueprintSelect(current_page_bps))

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
    """Displays all blueprints in a given pool, with optional weapon type filter."""
    # Check permissions for general commands (channel restrictions only)
    if not await check_command_permissions(interaction):
        return

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
        title=f"📦 Pool {pool_number} — {weapontype.upper()}",
        description="Loading blueprints.",
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
    """Searches and displays blueprints based on their status."""
    # Check permissions for general commands (channel restrictions only)
    if not await check_command_permissions(interaction):
        return

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
                blueprint_name_cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', bp['Name']).replace('*', '').strip()
                display_label = f"(Pool {bp.get('Pool', 'N/A')}) ({weapon['Name']}) {blueprint_name_cleaned} [`{blueprint_status}`]"

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
        description="Loading blueprints.",
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
    """Provides a link to the Blueprint Database website."""
    # Check permissions for general commands (channel restrictions only)
    if not await check_command_permissions(interaction):
        return

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
@app_commands.describe(
    gamemode="Choose a gamemode: wz/mp or zombies",
    tutorial="Show video tutorial? (True/False)"
)
@app_commands.choices(gamemode=[
    app_commands.Choice(name="Warzone / Multiplayer", value="wz"),
    app_commands.Choice(name="Zombies", value="zombies")
])
@app_commands.choices(tutorial=[
    app_commands.Choice(name="True", value="True"),
    app_commands.Choice(name="False", value="False")
])
async def howto(interaction: discord.Interaction, gamemode: app_commands.Choice[str], tutorial: app_commands.Choice[str]):
    """Explains how blueprint pulling works for different game modes."""
    # Check permissions for general commands (channel restrictions only)
    if not await check_command_permissions(interaction):
        return

    files_to_send = [discord.File("assets/logo.png", filename="logo.png")]
    show_video = tutorial.value.lower() == "true"

    if gamemode.value == "wz":
        method_name = "Warzone / Multiplayer"
        description_text = (
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
        )

        message_content = ""
        if show_video:
            message_content += f"## **{method_name} Tutorial**\n\n🎥 **Watch the video tutorial below!**\n\n"
            video_file = discord.File("assets/videos/MP_WZ.mp4", filename="MP_WZ.mp4")
            files_to_send.append(video_file)

        embed = discord.Embed(
            title="🎮 Blueprint Pulling — MP & Warzone Method",
            description=description_text,
            color=discord.Color.blue()
        )

        embed.set_thumbnail(url="attachment://logo.png")
        embed.add_field(
            name="🌐 Browse Blueprint Pools",
            value="[parsed.top](https://www.parsed.top/)", inline=False
        )
        embed.set_footer(text="Use /pool and /blueprint for fast lookups.")

        await interaction.response.send_message(
            content=message_content,
            embed=embed,
            ephemeral=True,
            files=files_to_send
        )

    elif gamemode.value == "zombies":
        method_name = "Zombies"
        description_text = (
            "⚠️ First, it’s important to know that this exploit only works on **PS5 and Xbox Series X/S**, last-gen consoles and PC players do not have access to split-screen, so this won’t work for you.\n"
            "Also, Player 2 doesn’t need a leveled-up account, but having one makes the pulls easier. If Player 2 uses a fresh account, you may need to perform an extra glitch to equip locked weapons in your Zombies loadout.\n\n"
            "🔧 Now, here’s how it comes:\n\n"
            "1️⃣ **Launch Call of Duty** and go into Zombies mode.\n\n"
            "2️⃣ **Connect a second controller** and sign in with your secondary profile.\n\n"
            "3️⃣ **Set up Player 2’s loadout** with the weapon you want to pull prints for (like the LADRA).\n\n"
            "4️⃣ **Back out to the screen** so you can edit your Controller 1 (main account) loadout.\n\n"
            "5️⃣ On your main account, **equip the blueprint you want to use** to pull the print.\n\n"
            "6️⃣ **Back out to the main menu** where you can select Multiplayer, Zombies, or Campaign.\n\n"
            "7️⃣ With Controller 2, **select Zombies mode**.\n\n"
            "8️⃣ Finally, **go back to Player 1’s main loadout**, and you should see the print you were trying to pull, as long as you’ve followed everything correctly.\n\n"
        )

        message_content = ""
        if show_video:
            message_content += f"## **{method_name} Tutorial**\n\n🎥 **Watch the video tutorial below!**\n\n"
            video_file = discord.File("assets/videos/Zombies.mp4", filename="Zombies.mp4")
            files_to_send.append(video_file)

        embed = discord.Embed(
            title="🧟 Zombies Blueprint Pulling (Split-Screen Exploit)",
            description=description_text,
            color=discord.Color.red()
        )
        embed.set_thumbnail(url="attachment://logo.png")
        embed.add_field(
            name="🌐 Browse Blueprint Pools",
            value="[parsed.top](https://www.parsed.top/)", inline=False
        )
        embed.set_footer(text="Use /pool to explore blueprints across pools and categories.")

        await interaction.response.send_message(
            content=message_content,
            embed=embed,
            ephemeral=True,
            files=files_to_send
        )

#Pool Explain Command
@tree.command(name="pool-explain", description="Learn how blueprint pulling works for pools")
async def pool_explain(interaction: discord.Interaction):
    """Explains how blueprint pulling works specifically for pools."""
    # Check permissions for general commands (channel restrictions only)
    if not await check_command_permissions(interaction):
        return

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
    """Displays a list of all available bot commands."""
    # Help command should always be accessible, no permission check here
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
        name="`/howto <gamemode> <tutorial>`",
        value="Learn how blueprint pulling works for Warzone/Multiplayer or Zombies, with an option to show a video tutorial (e.g., `/howto wz True`).",
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
        name="`/setchannel`",
        value="Set the designated channel(s) for bot messages via an interactive menu (Admin/Manage Channels only).",
        inline=False
    )
    embed.add_field(
        name="`/setroles`",
        value="Set the roles that are allowed to use bot commands (Admin only).",
        inline=False
    )
    embed.add_field(
        name="`/checkchannel`",
        value="Check the currently configured bot channel(s) and allowed roles (Admin/Manage Channels only).",
        inline=False
    )
    embed.add_field(
        name="`/clearchannel`",
        value="Clear all designated channels, allowing commands in any channel (Admin/Manage Channels only).",
        inline=False
    )
    embed.add_field(
        name="`/clearroles`",
        value="Clear all allowed roles, allowing any user to use commands (Admin only).",
        inline=False
    )
    embed.add_field(
        name="`/help`",
        value="Displays this help message.",
        inline=False
    )

    file_to_send = discord.File("assets/logo.png", filename="logo.png")
    embed.set_thumbnail(url="attachment://logo.png")
    embed.set_footer(text="Use these commands to navigate the blueprint database!")

    await interaction.response.send_message(embed=embed, ephemeral=True, file=file_to_send)

# Define a View for channel selection
class ChannelSelectView(discord.ui.View):
    def __init__(self, current_channel_ids: list):
        super().__init__(timeout=180) # Set a timeout for the view
        self.current_channel_ids = current_channel_ids

        # Create the ChannelSelect component with a unique custom_id
        self.channel_select = discord.ui.ChannelSelect(
            placeholder="Select channel(s) to add/remove.",
            channel_types=[discord.ChannelType.text], # Only allow text channels
            custom_id=f"channel_select_dropdown_{uuid.uuid4()}", # Unique ID for this instance
            min_values=0, # Allow clearing all channels
            max_values=25 # Max number of channels Discord allows in a select menu
        )
        self.add_item(self.channel_select)

        # Assign the callback explicitly
        self.channel_select.callback = self.channel_select_callback

        # Add a "Done" button with a unique custom_id
        self.done_button = discord.ui.Button(label="Done", style=discord.ButtonStyle.success, custom_id=f"done_channel_setup_{uuid.uuid4()}") # Unique ID
        self.add_item(self.done_button)
        self.done_button.callback = self.done_button_callback # Assign callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Ensure only the user who initiated the command can interact with the view
        # For admin configuration views, we don't apply the custom check_command_permissions
        # as admins should always be able to configure.
        if self.message and hasattr(self.message, 'interaction_metadata') and self.message.interaction_metadata and self.message.interaction_metadata.user:
            return interaction.user.id == self.message.interaction_metadata.user.id
        # Fallback for older interactions or if metadata is missing (less secure, but prevents errors)
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.errors.NotFound:
                print(f"Message for ChannelSelectView (ID: {self.message.id}) not found during timeout, likely dismissed by user.")
            except Exception as e:
                print(f"An unexpected error occurred during ChannelSelectView timeout: {e}")

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        print(f"Error in ChannelSelectView: {error}")
        await interaction.followup.send("An error occurred with the channel selection. Please try again.", ephemeral=True)

    async def channel_select_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        selected_channel_ids = [int(channel_id) for channel_id in interaction.data['values']]

        # Load the *full* config to update for the specific guild
        all_configs = load_config()
        guild_id_str = str(interaction.guild.id)
        guild_config = all_configs.setdefault(guild_id_str, {"channel_ids": [], "allowed_role_ids": []}) # Ensure guild entry exists
        current_channel_ids_in_config = guild_config.get("channel_ids", [])

        for channel_id in selected_channel_ids:
            if channel_id in current_channel_ids_in_config:
                current_channel_ids_in_config.remove(channel_id)
            else:
                current_channel_ids_in_config.append(channel_id)

        # Update the specific guild's channel_ids
        guild_config["channel_ids"] = current_channel_ids_in_config
        save_config(all_configs) # Save the entire configuration

        self.current_channel_ids = current_channel_ids_in_config # Update the view's state

        # Create updated embed
        selected_color = random.choice(EMBED_COLORS)
        embed = discord.Embed(
            title="⚙️ Configure Bot Channel(s)",
            description="Select channels from the dropdown to add/remove.",
            color=selected_color
        )
        if self.current_channel_ids:
            channel_mentions = [f"<#{cid}>" for cid in self.current_channel_ids]
            embed.add_field(name="Current Designated Channels", value=", ".join(channel_mentions), inline=False)
        else:
            embed.add_field(name="Current Designated Channels", value="None (bot commands can be used in any channel)", inline=False)
        embed.set_footer(text="Select more channels or click 'Done'.")

        await interaction.edit_original_response(embed=embed, view=self)

    async def done_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Load the *full* config to display the final state
        all_configs = load_config()
        guild_id_str = str(interaction.guild.id)
        guild_config = all_configs.setdefault(guild_id_str, {"channel_ids": [], "allowed_role_ids": []})
        final_channel_ids = guild_config.get("channel_ids", [])

        selected_color = random.choice(EMBED_COLORS)
        embed = discord.Embed(
            title="✅ Channel Configuration Complete!",
            description="The bot's designated channels have been updated.",
            color=selected_color
        )
        if final_channel_ids:
            channel_mentions = [f"<#{cid}>" for cid in final_channel_ids]
            embed.add_field(name="Configured Channels", value=", ".join(channel_mentions), inline=False)
        else:
            embed.add_field(name="Configured Channels", value="None (bot commands can be used in any channel)", inline=False)
        embed.set_footer(text=f"Configuration set by {interaction.user.display_name}")

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()

# Define a View for role selection
class RoleSelectView(discord.ui.View):
    def __init__(self, current_role_data: list): # Changed to expect list of dicts {id, name}
        super().__init__(timeout=180)
        self.current_role_data = current_role_data # Store as list of {id, name}

        self.role_select = discord.ui.RoleSelect(
            placeholder="Select role(s) to add/remove.",
            custom_id=f"role_select_dropdown_{uuid.uuid4()}",
            min_values=0,
            max_values=25
        )
        self.add_item(self.role_select)

        self.role_select.callback = self.role_select_callback

        self.done_button = discord.ui.Button(label="Done", style=discord.ButtonStyle.success, custom_id=f"done_role_setup_{uuid.uuid4()}") # Unique ID
        self.add_item(self.done_button)
        self.done_button.callback = self.done_button_callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.message and hasattr(self.message, 'interaction_metadata') and self.message.interaction_metadata and self.message.interaction_metadata.user:
            return interaction.user.id == self.message.interaction_metadata.user.id
        # Fallback for older interactions or if metadata is missing (less secure, but prevents errors)
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.errors.NotFound:
                print(f"Message for RoleSelectView (ID: {self.message.id}) not found during timeout, likely dismissed by user.")
            except Exception as e:
                print(f"An unexpected error occurred during RoleSelectView timeout: {e}")

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        print(f"Error in RoleSelectView: {error}")
        await interaction.followup.send("An error occurred with the role selection. Please try again.", ephemeral=True)

    async def role_select_callback(self, interaction: discord.Interaction):

        await interaction.response.defer()

        selected_role_ids = [int(role_id) for role_id in interaction.data['values']]

        # Load the *full* config to update for the specific guild
        all_configs = load_config()
        guild_id_str = str(interaction.guild.id)
        guild_config = all_configs.setdefault(guild_id_str, {"channel_ids": [], "allowed_role_ids": []}) # Ensure guild entry exists
        current_allowed_roles_in_config = guild_config.get("allowed_role_ids", []) # This now stores a list of dicts

        for selected_role_id_str in selected_role_ids:
            selected_role_id = int(selected_role_id_str)
            selected_role_obj = interaction.guild.get_role(selected_role_id) # Get the actual role object

            role_entry = {"id": selected_role_id, "name": selected_role_obj.name if selected_role_obj else "Unknown Role"}

            # Check if this role ID is already in the list
            found = False
            for i, existing_role_entry in enumerate(current_allowed_roles_in_config):
                if existing_role_entry["id"] == selected_role_id:
                    # If found, remove it (toggling)
                    current_allowed_roles_in_config.pop(i)
                    found = True
                    break
            if not found:
                # If not found, add it
                current_allowed_roles_in_config.append(role_entry)

        # Update the specific guild's allowed_role_ids
        guild_config["allowed_role_ids"] = current_allowed_roles_in_config
        save_config(all_configs) # Save the entire configuration

        self.current_role_data = current_allowed_roles_in_config # Update the view's state

        # Create updated embed
        selected_color = random.choice(EMBED_COLORS)
        embed = discord.Embed(
            title="⚙️ Configure Bot Allowed Roles",
            description="Select roles from the dropdown to add/remove.",
            color=selected_color
        )
        if self.current_role_data:
            role_mentions = []
            for r_data in self.current_role_data:
                role_obj = interaction.guild.get_role(r_data['id'])
                if role_obj:
                    role_mentions.append(role_obj.mention)
                else:
                    # If role object is None, use the stored name for display
                    role_mentions.append(f"Invalid Role (`{r_data['name']}` ID: `{r_data['id']}`)")
            embed.add_field(name="Current Allowed Roles", value=", ".join(role_mentions), inline=False)
        else:
            embed.add_field(name="Current Allowed Roles", value="None (all users can use commands)", inline=False)
        embed.set_footer(text="Select more roles or click 'Done'.")

        await interaction.edit_original_response(embed=embed, view=self)

    async def done_button_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Load the *full* config to display the final state
        all_configs = load_config()
        guild_id_str = str(interaction.guild.id)
        guild_config = all_configs.setdefault(guild_id_str, {"channel_ids": [], "allowed_role_ids": []})
        final_allowed_roles = guild_config.get("allowed_role_ids", []) # This now stores a list of dicts

        selected_color = random.choice(EMBED_COLORS)
        embed = discord.Embed(
            title="✅ Role Configuration Complete!",
            description="The bot's allowed roles have been updated.",
            color=selected_color
        )
        if final_allowed_roles:
            role_mentions = []
            for r_data in final_allowed_roles:
                role_obj = interaction.guild.get_role(r_data['id'])
                if role_obj:
                    role_mentions.append(role_obj.mention)
                else:
                    # Use the stored name for display if role object is None
                    role_mentions.append(f"Invalid Role (`{r_data['name']}` ID: `{r_data['id']}`)")
            embed.add_field(name="Configured Roles", value=", ".join(role_mentions), inline=False)
        else:
            embed.add_field(name="Configured Roles", value="None (all users can use commands)", inline=False)
        embed.set_footer(text=f"Configuration set by {interaction.user.display_name}")

        for item in self.children:
            item.disabled = True
        await interaction.edit_original_response(embed=embed, view=self)
        self.stop() # Stop the view interaction

# New command: /setchannel (modified)
@tree.command(name="setchannel", description="Set the designated channel(s) for bot messages.")
@app_commands.checks.has_permissions(administrator=True, manage_channels=True)
async def setchannel(interaction: discord.Interaction):
    """
    Initiates the process to set the designated channel(s) for the bot via an interactive embed.
    Requires administrator or manage_channels permissions.
    """
    if not interaction.guild:
        await send_and_manage_ephemeral(interaction, content="This command can only be used in a server.")
        return

    guild_id = str(interaction.guild.id)
    # Moved all_configs initialization outside the if block
    all_configs = load_config()
    config = all_configs.setdefault(guild_id, {"channel_ids": [], "allowed_role_ids": []})
    current_channel_ids = config.get("channel_ids", [])

    selected_color = random.choice(EMBED_COLORS)
    embed = discord.Embed(
        title="⚙️ Configure Bot Channel(s)",
        description="Please select text channel(s) from the dropdown below to set them as the bot's designated channel(s). "
                    "Selecting an already configured channel will remove it.",
        color=selected_color
    )
    if current_channel_ids:
        channel_mentions = [f"<#{cid}>" for cid in current_channel_ids]
        embed.add_field(name="Current Designated Channels", value=", ".join(channel_mentions), inline=False)
    else:
        embed.add_field(name="Current Designated Channels", value="None (bot commands can be used in any channel)", inline=False)
    embed.set_footer(text="This message will expire in 3 minutes. Click 'Done' when finished.")

    view = ChannelSelectView(current_channel_ids)
    message = await send_and_manage_ephemeral(interaction, embed=embed, view=view)
    view.message = message

@setchannel.error
async def setchannel_error(interaction: discord.Interaction, error: app_commands.AppCommandError): # Added type hint
    """Error handler for the /setchannel command."""
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You need `Administrator` or `Manage Channels` permissions to use this command.",
            color=discord.Color.red()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)
    else:
        print(f"An unexpected error occurred in /setchannel: {error}") # Changed 'e' to 'error'
        embed = discord.Embed(
            title="⚠️ Error",
            description="An unexpected error occurred while initiating channel setup.",
            color=discord.Color.orange()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)

# New command: /setroles
# Modified command: /setroles
@tree.command(name="setroles", description="Set the roles that are allowed to use bot commands.")
@app_commands.checks.has_permissions(administrator=True) # Only administrators can set roles
async def setroles(interaction: discord.Interaction):
    """
    Initiates the process to set roles that are allowed to use bot commands via an interactive embed.
    Requires administrator permissions.
    """
    if not interaction.guild:
        await send_and_manage_ephemeral(interaction, content="This command can only be used in a server.")
        return

    guild_id = str(interaction.guild.id)
    # Moved all_configs initialization outside the if block
    all_configs = load_config()
    config = all_configs.setdefault(guild_id, {"channel_ids": [], "allowed_role_ids": []})
    current_allowed_role_data = config.get("allowed_role_ids", []) # Expects list of dicts

    selected_color = random.choice(EMBED_COLORS)
    embed = discord.Embed(
        title="⚙️ Configure Bot Allowed Roles",
        description="Please select role(s) from the dropdown below that will be allowed to use bot commands. "
                    "Selecting an already allowed role will remove it. If a role no longer exists, it will be marked as 'Invalid'.",
        color=selected_color
    )
    if current_allowed_role_data:
        role_mentions = []
        valid_role_data = []
        for r_data in current_allowed_role_data:
            role = interaction.guild.get_role(r_data['id'])
            if role:
                role_mentions.append(role.mention)
                valid_role_data.append({"id": role.id, "name": role.name})
            else:
                role_mentions.append(f"Invalid Role (`{r_data['name']}` ID: `{r_data['id']}`)")
                valid_role_data.append(r_data)

        # Ensure the actual config object is updated
        all_configs[guild_id]["allowed_role_ids"] = [rd for rd in valid_role_data if interaction.guild.get_role(rd['id'])]
        save_config(all_configs)

        embed.add_field(name="Current Allowed Roles", value=", ".join(role_mentions), inline=False)
    else:
        embed.add_field(name="Current Allowed Roles", value="None (all users can use commands)", inline=False)
    embed.set_footer(text="This message will expire in 3 minutes. Click 'Done'.")

    view = RoleSelectView(all_configs[guild_id]["allowed_role_ids"]) # Use the potentially updated list for the view
    message = await send_and_manage_ephemeral(interaction, embed=embed, view=view)
    view.message = message

@setroles.error
async def setroles_error(interaction: discord.Interaction, error: app_commands.AppCommandError): # Added type hint
    """Error handler for the /setroles command."""
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You need `Administrator` permissions to use this command.",
            color=discord.Color.red()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)
    else:
        print(f"An unexpected error occurred in /setroles: {error}") # Changed 'e' to 'error'
        embed = discord.Embed(
            title="⚠️ Error",
            description="An unexpected error occurred while initiating role setup.",
            color=discord.Color.orange()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)

# New command: /checkchannel (updated to show roles)
@tree.command(name="checkchannel", description="Check the currently configured bot channel(s) and allowed roles.")
@app_commands.checks.has_permissions(administrator=True, manage_channels=True)
async def checkchannel(interaction: discord.Interaction):
    """
    Checks and displays information about the currently configured bot channel(s) and allowed roles.
    Requires administrator or manage_channels permissions.
    """
    if not interaction.guild:
        await send_and_manage_ephemeral(interaction, content="This command can only be used in a server.")
        return

    guild_id = str(interaction.guild.id)
    config = load_config(guild_id=guild_id) # Load specific guild's config
    channel_ids = config.get("channel_ids", [])
    allowed_role_data = config.get("allowed_role_ids", []) # This is now a list of dicts {id, name}

    selected_color = random.choice(EMBED_COLORS)
    embed = discord.Embed(color=selected_color)

    embed.title = "ℹ️ Bot Configuration Overview"
    embed.description = "Here's the current setup for the bot for this server:"

    # Channel Display (remains largely the same)
    if channel_ids:
        channel_mentions = []
        valid_channel_ids = []
        for cid in channel_ids:
            channel = bot.get_channel(cid)
            if channel:
                channel_mentions.append(channel.mention)
                valid_channel_ids.append(cid)
            else:
                channel_mentions.append(f"Invalid Channel (ID: `{cid}`)")
                # Log if a channel is invalid
                print(f"[{interaction.guild.name}] Invalid channel ID found in config: {cid}")

        # If invalid channels were found and removed, save the updated config for this guild
        if len(valid_channel_ids) < len(channel_ids):
            all_configs = load_config()
            all_configs[guild_id]["channel_ids"] = valid_channel_ids
            save_config(all_configs)

        embed.add_field(name="Designated Channels", value=", ".join(channel_mentions), inline=False)
    else:
        embed.add_field(name="Designated Channels", value="None (commands can be used in any channel)", inline=False)

    # Role Display (modified to use stored name and log)
    if allowed_role_data:
        role_mentions = []
        valid_role_data_for_save = [] # New list to store only valid roles for saving
        for r_data in allowed_role_data:
            role_id = r_data['id']
            role_name = r_data['name'] # Get the stored name
            role = interaction.guild.get_role(role_id)
            if role:
                role_mentions.append(role.mention)
                valid_role_data_for_save.append({"id": role.id, "name": role.name}) # Update name if it changed
            else:
                # Use the stored name for display and log it
                role_mentions.append(f"Invalid Role (`{role_name}` ID: `{role_id}`)")
                print(f"[{interaction.guild.name}] Invalid role found in config: Name: '{role_name}', ID: {role_id}")
                # We don't add invalid roles to valid_role_data_for_save; they'll be removed on save

        # If invalid roles were found, update the config to remove them
        if len(valid_role_data_for_save) < len(allowed_role_data):
            all_configs = load_config()
            all_configs[guild_id]["allowed_role_ids"] = valid_role_data_for_save
            save_config(all_configs)

        embed.add_field(name="Allowed Roles for Commands", value=", ".join(role_mentions), inline=False)
    else:
        embed.add_field(name="Allowed Roles for Commands", value="None (all users can use commands)", inline=False)
    embed.set_footer(text="Use `/setchannel` and `/setroles` to modify these settings.")

    await send_and_manage_ephemeral(interaction, embed=embed)

@checkchannel.error
async def checkchannel_error(interaction: discord.Interaction, error: app_commands.AppCommandError): # Added type hint
    """Error handler for the /checkchannel command."""
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You need `Administrator` or `Manage Channels` permissions to use this command.",
            color=discord.Color.red()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)
    else:
        print(f"An unexpected error occurred in /checkchannel: {error}") # Changed 'e' to 'error'
        embed = discord.Embed(
            title="⚠️ Error",
            description="An unexpected error occurred while checking the channel.",
            color=discord.Color.orange()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)

# New command: /clearchannel
@tree.command(name="clearchannel", description="Clear all designated channels, allowing commands in any channel.")
@app_commands.checks.has_permissions(administrator=True, manage_channels=True)
async def clearchannel(interaction: discord.Interaction):
    """
    Clears all designated channels, allowing bot commands to be used in any channel.
    Requires administrator or manage_channels permissions.
    """
    if not interaction.guild:
        await send_and_manage_ephemeral(interaction, content="This command can only be used in a server.")
        return

    guild_id = str(interaction.guild.id)
    # Moved all_configs initialization outside the if block
    all_configs = load_config()
    config = all_configs.setdefault(guild_id, {"channel_ids": [], "allowed_role_ids": []})
    current_channel_ids = config.get("channel_ids", [])

    if not current_channel_ids:
        embed = discord.Embed(
            title="ℹ️ Channels Already Clear",
            description="No designated channels are currently configured. Commands can be used in any channel.",
            color=discord.Color.blue()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)
        return

    all_configs[guild_id]["channel_ids"] = []
    save_config(all_configs)

    selected_color = random.choice(EMBED_COLORS)
    embed = discord.Embed(
        title="✅ Designated Channels Cleared!",
        description="All designated channels have been removed. Bot commands can now be used in any channel.",
        color=selected_color
    )
    embed.set_footer(text=f"Cleared by {interaction.user.display_name}")

    await send_and_manage_ephemeral(interaction, embed=embed)

@clearchannel.error
async def clearchannel_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Error handler for the /clearchannel command."""
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You need `Administrator` or `Manage Channels` permissions to use this command.",
            color=discord.Color.red()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)
    else:
        print(f"An unexpected error occurred in /clearchannel: {error}")
        embed = discord.Embed(
            title="⚠️ Error",
            description="An unexpected error occurred while clearing channels.",
            color=discord.Color.orange()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)

# New command: /clearroles
@tree.command(name="clearroles", description="Clear all allowed roles, allowing any user to use commands.")
@app_commands.checks.has_permissions(administrator=True)
async def clearroles(interaction: discord.Interaction):
    """
    Clears all allowed roles, allowing any user to use bot commands.
    Requires administrator permissions.
    """
    if not interaction.guild:
        await send_and_manage_ephemeral(interaction, content="This command can only be used in a server.")
        return

    guild_id = str(interaction.guild.id)
    config = load_config(guild_id=guild_id)
    current_allowed_role_data = config.get("allowed_role_ids", [])

    if not current_allowed_role_data:
        embed = discord.Embed(
            title="ℹ️ Roles Already Clear",
            description="No allowed roles are currently configured. All users can use commands.",
            color=discord.Color.blue()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)
        return

    all_configs = load_config()
    all_configs[guild_id]["allowed_role_ids"] = []
    save_config(all_configs)

    selected_color = random.choice(EMBED_COLORS)
    embed = discord.Embed(
        title="✅ Allowed Roles Cleared!",
        description="All allowed roles have been removed. Any user can now use bot commands.",
        color=selected_color
    )
    embed.set_footer(text=f"Cleared by {interaction.user.display_name}")

    await send_and_manage_ephemeral(interaction, embed=embed)

@clearroles.error
async def clearroles_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Error handler for the /clearroles command."""
    if isinstance(error, app_commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You need `Administrator` permissions to use this command.",
            color=discord.Color.red()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)
    else:
        print(f"An unexpected error occurred in /clearroles: {error}")
        embed = discord.Embed(
            title="⚠️ Error",
            description="An unexpected error occurred while clearing roles.",
            color=discord.Color.orange()
        )
        await send_and_manage_ephemeral(interaction, embed=embed)

##################################################################################

# Retrieve the Discord bot token from environment variables
##################################################################################
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')

if DISCORD_BOT_TOKEN:
    # Call the synchronous dependency installation
    install_dependencies_sync()
    print("✅ Libraries Installed")
    time.sleep(0.5)
    try:
        bot.run(DISCORD_BOT_TOKEN)
    finally:
        # This block will execute regardless of how bot.run() exits
        print("✅ Bot process terminated.")
else:
    print("Error: DISCORD_BOT_TOKEN environment variable not set.")
    print("Please set the DISCORD_BOT_TOKEN environment variable before running the bot.")
##################################################################################
