# 🔫 Blueprint Discord Bot

*The offical Discord bot for [Parsed.top](https://parsed.top/)*

*lovingly crafted by*
- 🐼 **Panda**
- 📊 **Parse**.

---

## 📚 Table of Contents

* [✨ Features](#features)
* [🚀 Setup](#setup)
    * [📋 Prerequisites](#prerequisites)
    * [📦 Installation](#installation)
    * [▶️ Running the Bot](#running-the-bot)
* [🤖 Commands](#commands)
* [⚙️ Configuration](#configuration)
* [📁 File Structure](#file-structure)
* [🤝 Contributing](#contributing)
---

## ✨ Features

This bot comes packed with functionalities to enhance your blueprint management and knowledge:

* **🔍 Blueprint Lookup:** Quickly find details about any specific blueprint by its name.
* **📦 Pool Exploration:** Dive into specific blueprint "pools" and view all associated blueprints, with an option to filter by weapon type.
* **📜 Status Search:** Filter blueprints based on their release status (e.g., `RELEASED`, `UNRELEASED`, `NOTHING`, `NOTEXTURE`).
* **📖 Blueprint Pulling Guides:** Comprehensive explanations on how the blueprint pulling exploit works for different game modes like Warzone/Multiplayer and Zombies.
* **💡 Pool Pulling Explanation:** A dedicated guide explaining the nuances of blueprint pulling specifically within the context of weapon pools.
* **🌐 Website Link:** Get a direct link to the full Blueprint Database website for a more extensive browsing experience.
* **❓ Help Command:** Access an organized list of all available bot commands and their usage.
* **⏱️ Smart Rate Limiting:** Prevents command spam by implementing a cooldown mechanism for embeds.
* **🧹 Ephemeral Message Management:** Automatically cleans up previous ephemeral messages to maintain a tidy chat interface.
* **🎨 Themed Logging:** Enjoy a cleaner and more visually appealing console output with custom-themed log messages.

---

## 🚀 Setup

Follow these steps to get your Blueprint Discord Bot up and running.

### 📋 Prerequisites

Ensure you have the following installed on your system:

* **Python 3.8 or higher**:
    ```bash
    python --version
    ```
* **pip** (Python package installer):
    ```bash
    pip --version
    ```

### 📦 Installation

1.  **Clone the Repository (or download the script):**

    If you're using Git, clone the repository:
    ```bash
    git clone [https://github.com/your-username/blueprint-discord-bot.git](https://github.com/your-username/blueprint-discord-bot.git)
    cd blueprint-discord-bot
    ```
    If you've only downloaded the `testbot.py` file, navigate to the directory where you saved it.

2.  **Create a `requirements.txt` file:**

    In the same directory as `testbot.py`, create a file named `requirements.txt` and add the following lines:
    ```
    discord.py
    python-dotenv
    ```

3.  **Install Required Python Libraries:**

    Open your terminal or command prompt in the bot's directory and run:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Prepare `blueprints.json`:**

    The bot relies on a `blueprints.json` file for all blueprint data. This file should be placed in the **same directory** as `testbot.py`. The structure of this JSON file should be an array of "Weapons", where each weapon object contains a "Category" and an array of "Blueprints". Each blueprint object should have "Name", "Pool", and optionally "status" fields.

    **Example `blueprints.json` structure:**
    ```json
    {
      "Weapons": [
        {
          "Name": "M4",
          "Category": "1",
          "Blueprints": [
            {
              "Name": "Storm Rage",
              "Pool": "1",
              "status": "RELEASED"
            },
            {
              "Name": "Blue Streak",
              "Pool": "2",
              "status": "UNRELEASED"
            }
          ]
        },
        {
          "Name": "MP5",
          "Category": "2",
          "Blueprints": [
            {
              "Name": "The Fixer",
              "Pool": "1",
              "status": "RELEASED"
            }
          ]
        }
      ]
    }
    ```

5.  **Create an `assets` directory and `logo.png`:**

    The bot expects an `assets` folder at the root level, containing a `logo.png` file for embeds. Additionally, blueprint images are expected within `assets/blueprints/images/`.

    Create the following directory structure:
    ```
    .
    ├── testbot.py              # The main bot script
    ├── blueprints.json         # JSON database of blueprints
    ├── .env                    # Environment variables (e.g., DISCORD_BOT_TOKEN)
    └── assets/                 # Directory for bot assets
        ├── logo.png            # Bot's logo for embeds
        └── blueprints/         # Blueprint-related assets
            └── images/         # Blueprint image files
                ├── WeaponName1/
                │   └── BlueprintNameA.jpg
                │   └── BlueprintNameB.jpg
                ├── WeaponName2/
                │   └── BlueprintNameC.jpg
                └── ...
    ```

### ▶️ Running the Bot

Once everything is set up, you can run the bot:

```bash
python testbot.py
```

You should see output similar to this, indicating the bot has successfully logged in and synced commands:

```
✅ Logged in using static token
✅ Shard ID 0 has connected to Gateway (Session ID: [your-session-id])
✅ Logged in as YourBotName#1234
✅ Slash commands synced.
✅ Bot status set to 'Playing with Blueprints'.
```

---

## 🤖 Commands

The Blueprint Discord Bot uses slash commands for easy interaction.

* **`/blueprint <nameid>`**
    * **Description:** Look up a specific blueprint by its full name.
    * **Parameter:**
        * `nameid` (string, required): The exact name of the blueprint (e.g., `STORM RAGE`, `The Fixer`). Case-insensitive.
    * **Example:**
        ```bash
        /blueprint STORM RAGE
        ```
    * **Output:** An embed showing the blueprint's name, weapon, pool, status, and an image if available.

* **`/pool <number> [weapontype]`**
    * **Description:** View all blueprints within a specified pool. Optionally filter by weapon type.
    * **Parameters:**
        * `number` (integer, required): The pool number (e.g., `1`, `15`).
        * `weapontype` (string, optional): Filter by weapon category (e.g., `smgs`, `assault rifles`, `snipers`, `all`). Autocomplete is available.
    * **Example:**
        ```bash
        /pool 1 smgs
        /pool 15
        ```
    * **Output:** A paginated embed listing blueprints in the pool, with buttons to navigate pages and a dropdown to select a blueprint for detailed viewing.

* **`/search_status <status>`**
    * **Description:** Find blueprints based on their release status.
    * **Parameter:**
        * `status` (choice, required): Select from `RELEASED`, `UNRELEASED`, `NOTHING`, or `NOTEXTURE`.
    * **Example:**
        ```bash
        /search_status UNRELEASED
        ```
    * **Output:** A paginated embed listing all blueprints matching the selected status.

* **`/howto <gamemode>`**
    * **Description:** Learn how blueprint pulling works for specific game modes.
    * **Parameter:**
        * `gamemode` (choice, required): Choose between `Warzone / Multiplayer` (`wz`) or `Zombies` (`zombies`).
    * **Example:**
        ```bash
        /howto wz
        ```bash
        /howto zombies
        ```
    * **Output:** A detailed ephemeral embed explaining the pulling method for the chosen game mode.

* **`/pool-explain`**
    * **Description:** Get a specific explanation on how blueprint pulling interacts with weapon pools.
    * **Example:**
        ```bash
        /pool-explain
        ```
    * **Output:** An ephemeral embed detailing the pool pulling concept with an example.

* **`/website`**
    * **Description:** Provides a link to the full Blueprint Database website.
    * **Example:**
        ```bash
        /website
        ```
    * **Output:** An ephemeral embed with a clickable link to the website.

* **`/help`**
    * **Description:** Displays a comprehensive list of all available bot commands and their brief descriptions.
    * **Example:**
        ```bash
        /help
        ```
    * **Output:** An ephemeral embed listing all commands.

---

## ⚙️ Configuration

* **`DISCORD_BOT_TOKEN`**: This environment variable, loaded from the `.env` file, is crucial for the bot to authenticate with Discord.
* **`blueprints.json`**: This file serves as the bot's database. Ensure its structure matches the example provided in the [Installation](#installation) section for proper functionality.
* **`assets/` directory**: Contains `logo.png` for embeds and `assets/blueprints/images/` for blueprint image previews.

---

## 📁 File Structure

The recommended file structure for the bot is as follows:

```
blueprint-discord-bot/
├── testbot.py              # The main bot script
├── blueprints.json         # JSON database of blueprints
├── .env                    # Environment variables (e.g., DISCORD_BOT_TOKEN)
└── assets/                 # Directory for bot assets
    ├── logo.png            # Bot's logo for embeds
    └── blueprints/         # Blueprint-related assets
        └── images/         # Blueprint image files
            ├── WeaponName1/
            │   └── BlueprintNameA.jpg
            │   └── BlueprintNameB.jpg
            ├── WeaponName2/
            │   └── BlueprintNameC.jpg
            └── .
```

---

## 🤝 Contributing

Contributions are welcome! If you have suggestions for improvements, bug fixes, or new features, please feel free to:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add new feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.

---
