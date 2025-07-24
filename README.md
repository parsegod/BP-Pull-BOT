# 🔫 Blueprint Discord Bot
created by Panda and Parse

A powerful and intuitive Discord bot designed to help Call of Duty players navigate the vast world of weapon blueprints. Easily look up blueprints, explore weapon pools, search by status, and understand the mechanics of blueprint pulling across different game modes.

## 📚 Table of Contents

* [✨ Features](https://www.google.com/search?q=%23-features)

* [🚀 Setup](https://www.google.com/search?q=%23-setup)

  * [📋 Prerequisites](https://www.google.com/search?q=%23-prerequisites)

  * [📦 Installation](https://www.google.com/search?q=%23-installation)

  * [▶️](https://www.google.com/search?q=%23%25EF%25B8%258F-running-the-bot) Running the Bot

* [🤖 Commands](https://www.google.com/search?q=%23-commands)

* [⚙️ Configuration](https://www.google.com/search?q=%23%25EF%25B8%258F-configuration)

* [📁 File Structure](https://www.google.com/search?q=%23-file-structure)

* [🤝 Contributing](https://www.google.com/search?q=%23-contributing)

* [©️ License](https://www.google.com/search?q=%23%25EF%25B8%258F-license)

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

## 🚀 Setup

Follow these steps to get your Blueprint Discord Bot up and running.

### 📋 Prerequisites

Ensure you have the following installed on your system:

* **Python 3.8 or higher**:

  ```
  python --version
  
  ```

* **pip** (Python package installer):

  ```
  pip --version
  
  ```

### 📦 Installation

1. **Clone the Repository (or download the script):**

   If you're using Git, clone the repository:

   ```
   git clone [https://github.com/your-username/blueprint-discord-bot.git](https://github.com/your-username/blueprint-discord-bot.git)
   cd blueprint-discord-bot
   
   ```

   If you've only downloaded the `testbot.py` file, navigate to the directory where you saved it.

2. **Create a `requirements.txt` file:**

   In the same directory as `testbot.py`, create a file named `requirements.txt` and add the following lines:

   ```
   discord.py
   python-dotenv
   
   ```

3. **Install Required Python Libraries:**

   Open your terminal or command prompt in the bot's directory and run:

   ```
   pip install -r requirements.txt
   
   ```

4. **Prepare `blueprints.json`:**

   The bot relies on a `blueprints.json` file for all blueprint data. This file should be placed in the **same directory** as `testbot.py`. The structure of this JSON file should be an array of "Weapons", where each weapon object contains a "Category" and an array of "Blueprints". Each blueprint object should have "Name", "Pool", and optionally "status" fields.

   **Example `blueprints.json` structure:**

   ```
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

5. **Create an `assets` directory and `logo.png`:**

   The bot expects an `assets` folder at the root level, containing a `logo.png` file for embeds. Additionally, blueprint images are expected within `assets/blueprints/images/`.

   Create the following directory structure:

   ```
   .
   ├── testbot.py              # The main bot script
   ├── blueprints.
   
   
