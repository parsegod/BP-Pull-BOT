import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
import threading
import concurrent.futures # For thread pooling
import base64 # For encoding/decoding file content
import os # For file path operations
import time # For timestamps

# --- Basic Obfuscation (NOT secure encryption) ---
# WARNING: This is a simple XOR cipher for obfuscation, NOT cryptographic security.
# Do NOT use this for highly sensitive data in production environments.
# A hardcoded key is inherently insecure.
ENCRYPTION_KEY = "my_secret_key_123!@#" # Replace with a strong, randomly generated key for better obfuscation

def _xor_encrypt_decrypt(data, key):
    """
    Performs a simple XOR encryption/decryption on a string.
    This is for obfuscation, not security.
    """
    if not data:
        return ""
    if not key:
        return data # No key, no obfuscation

    result = bytearray()
    key_bytes = key.encode('utf-8')
    data_bytes = data.encode('utf-8')
    key_len = len(key_bytes)

    for i in range(len(data_bytes)):
        result.append(data_bytes[i] ^ key_bytes[i % key_len])
    return base64.urlsafe_b64encode(result).decode('utf-8')

def _xor_decrypt_decode(encrypted_data, key):
    """
    Decrypts/decodes data encrypted with _xor_encrypt_decrypt.
    """
    if not encrypted_data:
        return ""
    if not key:
        return encrypted_data # No key, no obfuscation

    try:
        decoded_bytes = base64.urlsafe_b64decode(encrypted_data.encode('utf-8'))
        key_bytes = key.encode('utf-8')
        key_len = len(key_bytes)
        result = bytearray()
        for i in range(len(decoded_bytes)):
            result.append(decoded_bytes[i] ^ key_bytes[i % key_len])
        return result.decode('utf-8')
    except Exception:
        return "" # Return empty string on decryption error (e.g., corrupted data)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Update Center")
        self.root.geometry("1100x700")
        self.root.resizable(True, True)

        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.github_token = None
        self.current_gist_id = None
        self.current_file_name = None
        self.current_gist_data = None # Store the full gist data

        self.jsonbin_master_key = None
        self.current_jsonbin_id = None
        self.current_jsonbin_record_data = None # Store only the 'record' part of the JSONBin

        # Variables for GitHub Repo Editor
        self.current_repo_owner = None
        self.current_repo_name = None
        self.current_repo_branch = None
        self.current_repo_file_path = None
        self.current_repo_file_sha = None # To store the SHA of the file for updates
        self.all_user_repos = {} # Stores repo_full_name: {owner: ..., name: ...}
        self.repo_branches = [] # Stores list of branch names
        self.repo_json_files = [] # Stores list of JSON file paths

        # Variables for Bot Editor (Local File)
        self.bot_config_local_file_path_var = tk.StringVar(value="bot_config.json")
        self.bot_pfp_url_var = tk.StringVar()
        self.bot_status_var = tk.StringVar(value="online")
        self.bot_activity_type_var = tk.StringVar(value="playing")
        self.bot_activity_name_var = tk.StringVar()
        self.bot_rp_details_var = tk.StringVar()
        self.bot_rp_state_var = tk.StringVar()
        self.bot_rp_large_image_url_var = tk.StringVar()
        self.bot_rp_large_image_text_var = tk.StringVar()
        self.bot_rp_small_image_url_var = tk.StringVar()
        self.bot_rp_small_image_text_var = tk.StringVar()
        self.bot_rp_start_timestamp_var = tk.StringVar()
        self.bot_rp_end_timestamp_var = tk.StringVar()

        # New variables for Bot Editor settings
        self.bot_command_prefix_var = tk.StringVar(value="/")
        self.bot_log_channel_id_var = tk.StringVar()
        self.bot_welcome_enabled_var = tk.BooleanVar(value=False)
        self.bot_welcome_channel_id_var = tk.StringVar()
        self.bot_welcome_message_var = tk.StringVar(value="")
        self.bot_max_embeds_var = tk.StringVar(value="4")
        self.bot_period_seconds_var = tk.StringVar(value="35")


        self.current_bot_config_data = {} # Stores the parsed bot config JSON

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)

        # Credential saving variables
        self.credentials_file = "credentials.json"
        self.remember_github_pat_var = tk.BooleanVar(value=False)
        self.remember_jsonbin_creds_var = tk.BooleanVar(value=False)

        self._apply_custom_styles()
        self._create_navigation_frame()
        self._create_jsonbin_tester_section()
        self._create_github_gist_editor_section()
        self._create_jsonbin_editor_section()
        self._create_github_repo_editor_section() # New GitHub Repo Editor section
        self._create_bot_editor_section() # New Bot Editor section

        self.show_section("jsonbin_tester") # Initially show the JSONBin Tester section

        self.scroll_canvas.bind('<Configure>', self._on_canvas_configure)
        self.scroll_canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.scroll_canvas.bind_all("<Button-4>", self._on_mouse_wheel)
        self.scroll_canvas.bind_all("<Button-5>", self._on_mouse_wheel)

        self.root.update_idletasks()
        self._on_frame_configure(None)

        self._load_credentials() # Load credentials on startup


    def _apply_custom_styles(self):
        """Applies custom ttk styles for a modern and visually appealing look."""
        self.root.style = ttk.Style()
        self.root.style.theme_use('clam')

        self.colors = {
            "primary": "#0078D7",
            "primary_dark": "#005BA1",
            "secondary_bg": "#F0F0F0",
            "card_bg": "white",
            "text": "#202020",
            "heading": "#1A1A1A",
            "accent": "#00CC66",
            "error": "#D92121",
            "success": "#28A745",
            "info": "#0078D7",
            "border": "#E0E0E0",
            "hover_light": "#E6E6E6",
            "active_light": "#D0D0D0",
            "close_hover": "#E81123",
            "close_active": "#C40C1D",
            "title_bar_bg": "#F8F8F8",
            "title_bar_text": "#202020",
            "nav_inactive_bg": "#EAEAEA",
            "nav_inactive_text": "#505050",
            "warning_bg": "#FFFBEB",
            "warning_text": "#F5A623"
        }

        self.root.style.configure('.', font=("Segoe UI", 10, "normal"), background=self.colors["secondary_bg"], foreground=self.colors["text"])
        self.root.style.configure('TFrame', background=self.colors["secondary_bg"], borderwidth=0, relief='flat')
        self.root.style.configure('Card.TFrame', background=self.colors["card_bg"], borderwidth=1, relief='solid',
                                  bordercolor=self.colors["border"], padding=20)
        self.root.style.configure('TLabel', background=self.colors["secondary_bg"], foreground=self.colors["text"])
        self.root.style.configure('Heading.TLabel', font=("Segoe UI", 20, "bold"), foreground=self.colors["heading"], background=self.colors["card_bg"])
        self.root.style.configure('Subheading.TLabel', font=("Segoe UI", 14, "bold"), foreground=self.colors["heading"], background=self.colors["card_bg"])
        self.root.style.configure('Error.TLabel', foreground=self.colors["error"], background=self.colors["warning_bg"], borderwidth=1, relief="solid", padding=8, wraplength=700)
        self.root.style.configure('Success.TLabel', foreground=self.colors["success"], background="#e6ffe6", borderwidth=1, relief="solid", padding=8, wraplength=700)
        self.root.style.configure('Info.TLabel', foreground=self.colors["info"], background="#e6f7ff", borderwidth=1, relief="solid", padding=8, wraplength=700)
        self.root.style.configure('Loading.TLabel', foreground=self.colors["primary"], font=("Segoe UI", 10, "italic"))
        self.root.style.configure('Warning.TLabel', foreground=self.colors["warning_text"], background=self.colors["warning_bg"], borderwidth=1, relief="solid", padding=8, wraplength=700)
        self.root.style.configure('TButton',
                                  background=self.colors["primary"],
                                  foreground='white',
                                  font=("Segoe UI", 10, "bold"),
                                  borderwidth=0,
                                  relief='flat',
                                  padding=[10, 5])
        self.root.style.map('TButton',
                            background=[('active', self.colors["primary_dark"]), ('pressed', self.colors["primary_dark"])],
                            foreground=[('active', 'white'), ('pressed', 'white')],
                            relief=[('pressed', 'flat')])
        self.root.style.configure('Nav.TButton',
                                  background=self.colors["nav_inactive_bg"],
                                  foreground=self.colors["nav_inactive_text"],
                                  font=("Segoe UI", 10, "bold"),
                                  borderwidth=0,
                                  relief='flat',
                                  padding=[15, 8])
        self.root.style.map('Nav.TButton',
                            background=[('active', self.colors["hover_light"]), ('pressed', self.colors["active_light"])],
                            foreground=[('active', self.colors["text"]), ('pressed', self.colors["text"])])
        self.root.style.configure('Active.Nav.TButton',
                                  background=self.colors["primary"],
                                  foreground='white',
                                  font=("Segoe UI", 10, "bold"),
                                  borderwidth=0,
                                  relief='flat',
                                  padding=[15, 8])
        self.root.style.map('Active.Nav.TButton',
                            background=[('active', self.colors["primary_dark"]), ('pressed', self.colors["primary_dark"])],
                            foreground=[('active', 'white'), ('pressed', 'white')])
        self.root.style.configure('TEntry', fieldbackground=self.colors["card_bg"], borderwidth=1, relief='solid',
                                  bordercolor=self.colors["border"], padding=8)
        self.root.style.map('TEntry', fieldbackground=[('focus', '#E6F7FF')])
        self.root.style.configure('TCombobox', fieldbackground=self.colors["card_bg"], borderwidth=1, relief='solid',
                                  bordercolor=self.colors["border"], padding=8)
        self.root.style.map('TCombobox', fieldbackground=[('focus', '#E6F7FF')])
        self.root.option_add('*Scrolledtext*background', self.colors["card_bg"])
        self.root.option_add('*Scrolledtext*foreground', self.colors["text"])
        self.root.option_add('*Scrolledtext*borderwidth', 1)
        self.root.option_add('*Scrolledtext*relief', 'solid')
        self.root.option_add('*Scrolledtext*highlightbackground', self.colors["border"])
        self.root.option_add('*Scrolledtext*highlightthickness', 1)
        self.root.style.configure('TNotebook', background=self.colors["card_bg"], borderwidth=0)
        self.root.style.configure('TNotebook.Tab', background=self.colors["secondary_bg"], foreground=self.colors["text"],
                                  padding=[10, 5], font=("Segoe UI", 10, "bold"))
        self.root.style.map('TNotebook.Tab', background=[('selected', self.colors["primary"])],
                            foreground=[('selected', 'white')])


    def _create_navigation_frame(self):
        """Creates the frame for navigation buttons and the scrollable content area."""
        nav_frame = ttk.Frame(self.root, padding="10", style='TFrame')
        nav_frame.grid(row=0, column=0, pady=0, sticky="ew", columnspan=1)
        nav_frame.grid_columnconfigure(0, weight=1)
        nav_frame.grid_columnconfigure(1, weight=1)
        nav_frame.grid_columnconfigure(2, weight=1)
        nav_frame.grid_columnconfigure(3, weight=1)
        nav_frame.grid_columnconfigure(4, weight=1) # For the new Bot Editor button

        self.jsonbin_tester_btn = ttk.Button(nav_frame, text="Signal Tester", style='Nav.TButton',
                                      command=lambda: self.show_section("jsonbin_tester"))
        self.jsonbin_tester_btn.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.github_btn = ttk.Button(nav_frame, text="GitHub Gist Editor", style='Nav.TButton',
                                     command=lambda: self.show_section("github_gist_editor"))
        self.github_btn.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.jsonbin_editor_btn = ttk.Button(nav_frame, text="JSONBin Editor", style='Nav.TButton',
                                             command=lambda: self.show_section("jsonbin_editor"))
        self.jsonbin_editor_btn.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.github_repo_btn = ttk.Button(nav_frame, text="GitHub Repo Editor", style='Nav.TButton',
                                          command=lambda: self.show_section("github_repo_editor"))
        self.github_repo_btn.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        self.bot_editor_btn = ttk.Button(nav_frame, text="Bot Editor", style='Nav.TButton',
                                         command=lambda: self.show_section("bot_editor"))
        self.bot_editor_btn.grid(row=0, column=4, padx=5, pady=5, sticky="ew")


        self.scroll_canvas = tk.Canvas(self.root, background=self.colors["secondary_bg"], highlightthickness=0)
        self.scroll_canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.scroll_canvas.yview)
        self.scrollbar.grid(row=1, column=1, sticky="ns")

        self.scroll_canvas.configure(yscrollcommand=self.scrollbar.set)

        self.content_frame = ttk.Frame(self.scroll_canvas, style='TFrame', padding=0)
        self.content_frame_id = self.scroll_canvas.create_window((0, 0), window=self.content_frame, anchor="nw")

        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(1, weight=0)
        self.content_frame.grid_columnconfigure(2, weight=1)

        self.content_frame.bind('<Configure>', self._on_frame_configure)

    def _on_frame_configure(self, event):
        """Update the scrollregion of the canvas when the content frame's size changes."""
        self.scroll_canvas.configure(scrollregion=self.scroll_canvas.bbox("all"))
        canvas_width = self.scroll_canvas.winfo_width()
        content_width = self.content_frame.winfo_reqwidth()
        x_offset = (canvas_width - content_width) / 2
        if x_offset < 0:
            x_offset = 0
        self.scroll_canvas.coords(self.content_frame_id, x_offset, 0)


    def _on_canvas_configure(self, event):
        """Update the canvas's width and re-center the internal frame when it's resized."""
        canvas_width = event.width
        self.scroll_canvas.itemconfig(self.content_frame_id, width=canvas_width)
        self._on_frame_configure(None)


    def _on_mouse_wheel(self, event):
        """Handles mouse wheel scrolling."""
        if self.scroll_canvas.winfo_exists():
            if event.delta:
                self.scroll_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            else:
                if event.num == 4:
                    self.scroll_canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    self.scroll_canvas.yview_scroll(1, "units")


    def _create_jsonbin_tester_section(self):
        """Creates the UI elements for the JSONBin Tester."""
        self.jsonbin_tester_frame = ttk.Frame(self.content_frame, padding="20", style='Card.TFrame')
        self.jsonbin_tester_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self.jsonbin_tester_frame, text="JSONBin Credential Tester",
                  style='Heading.TLabel').pack(pady=10)

        ttk.Label(self.jsonbin_tester_frame, text="Enter a URL that serves raw JSON content (e.g., a raw GitHub Gist). "
                                           "The JSON should contain a key named `JSONBIN_BIN_ID`.",
                  wraplength=600, style='TLabel').pack(pady=5)

        ttk.Label(self.jsonbin_tester_frame, text="Credentials URL:", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.creds_url_entry = ttk.Entry(self.jsonbin_tester_frame, width=80, style='TEntry')
        self.creds_url_entry.insert(0, "https://gist.githubusercontent.com/parsegod/b68b820bb7de3fdfbc89c5b6ab4de534/raw/jsonbin.json")
        self.creds_url_entry.pack(fill="x", pady=5)
        ttk.Label(self.jsonbin_tester_frame, text="Example: https://gist.githubusercontent.com/yourusername/yourgistid/raw/yourfile.json",
                  font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).pack(anchor="w")

        self.test_button = ttk.Button(self.jsonbin_tester_frame, text="Test Fetch Credentials",
                                      command=self.start_jsonbin_test, style='TButton')
        self.test_button.pack(pady=15, fill="x", ipady=5)

        self.jsonbin_tester_result_label = ttk.Label(self.jsonbin_tester_frame, text="Results will appear here...",
                                              wraplength=700, justify="left", style='TLabel')
        self.jsonbin_tester_result_label.pack(pady=10, fill="both", expand=True)

        self.jsonbin_tester_loading_label = ttk.Label(self.jsonbin_tester_frame, text="Fetching...", style='Loading.TLabel')
        self.jsonbin_tester_loading_label.pack(pady=5)
        self.jsonbin_tester_loading_label.pack_forget()


    def _create_github_gist_editor_section(self):
        """Creates the UI elements for the GitHub Gist Editor."""
        self.github_frame = ttk.Frame(self.content_frame, padding="20", style='Card.TFrame')
        self.github_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self.github_frame, text="GitHub Gist Editor",
                  style='Heading.TLabel').pack(pady=10)

        ttk.Label(self.github_frame, text="Security Warning: Directly using Personal Access Tokens (PATs) in client-side code is not secure for production. Use this for testing only. Ensure your PAT has `gist` scope and revoke it after use.",
                  wraplength=600, style='Warning.TLabel').pack(pady=10)

        ttk.Label(self.github_frame, text="GitHub Personal Access Token (PAT):", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.github_pat_entry = ttk.Entry(self.github_frame, show="*", width=80, style='TEntry')
        self.github_pat_entry.pack(fill="x", pady=5)

        # Remember PAT checkbox
        self.remember_github_pat_check = ttk.Checkbutton(self.github_frame, text="Remember GitHub PAT (Obfuscated)",
                                                         variable=self.remember_github_pat_var, style='TCheckbutton')
        self.remember_github_pat_check.pack(anchor="w", pady=(0, 10))
        ttk.Label(self.github_frame, text="How to create a PAT: (Refer to GitHub Docs)",
                  font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).pack(anchor="w")

        self.login_github_button = ttk.Button(self.github_frame, text="Login to GitHub",
                                              command=self.start_github_login, style='TButton')
        self.login_github_button.pack(pady=15, fill="x", ipady=5)

        self.github_status_label = ttk.Label(self.github_frame, text="", wraplength=700, justify="left", style='TLabel')
        self.github_status_label.pack(pady=5)

        self.gist_content_frame = ttk.Frame(self.github_frame, padding="10", style='TFrame')
        self.gist_content_frame.pack(fill="both", expand=True, pady=10)
        self.gist_content_frame.pack_forget()
        self.gist_content_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self.gist_content_frame, text="Your Gists", style='Subheading.TLabel').pack(anchor="w", pady=(0, 5))
        self.gist_select = ttk.Combobox(self.gist_content_frame, state="readonly", style='TCombobox')
        self.gist_select.pack(fill="x", pady=5)
        self.gist_select.bind("<<ComboboxSelected>>", self.on_gist_selected)
        # Prevent mouse wheel from changing selection
        self.gist_select.bind("<MouseWheel>", lambda event: "break")
        self.gist_select.bind("<Button-4>", lambda event: "break") # For Linux
        self.gist_select.bind("<Button-5>", lambda event: "break") # For Linux


        self.file_select_container = ttk.Frame(self.gist_content_frame, style='TFrame')
        self.file_select_container.pack(fill="x", pady=5)
        self.file_select_container.pack_forget()
        self.file_select_container.grid_columnconfigure(0, weight=1)

        ttk.Label(self.file_select_container, text="Select File in Gist:", style='TLabel').pack(anchor="w", pady=(0, 5))
        self.file_select = ttk.Combobox(self.file_select_container, state="readonly", style='TCombobox')
        self.file_select.pack(fill="x", pady=5)
        self.file_select.bind("<<ComboboxSelected>>", self.on_file_selected)
        # Prevent mouse wheel from changing selection
        self.file_select.bind("<MouseWheel>", lambda event: "break")
        self.file_select.bind("<Button-4>", lambda event: "break") # For Linux
        self.file_select.bind("<Button-5>", lambda event: "break") # For Linux


        self.gist_editor_container = ttk.Frame(self.gist_content_frame, style='TFrame')
        self.gist_editor_container.pack(fill="both", expand=True, pady=5)
        self.gist_editor_container.pack_forget()
        self.gist_editor_container.grid_columnconfigure(0, weight=1)
        self.gist_editor_container.grid_rowconfigure(1, weight=1)

        ttk.Label(self.gist_editor_container, text="File Content:", style='TLabel').pack(anchor="w", pady=(0, 5))
        self.gist_file_content_text = scrolledtext.ScrolledText(self.gist_editor_container, wrap=tk.WORD, height=15)
        self.gist_file_content_text.pack(fill="both", expand=True, pady=5)

        self.save_gist_button = ttk.Button(self.gist_editor_container, text="Save Gist Changes",
                                           command=self.start_save_gist, style='TButton')
        self.save_gist_button.pack(pady=10, fill="x", ipady=5)

        self.gist_save_status_label = ttk.Label(self.gist_editor_container, text="", wraplength=700, justify="left", style='TLabel')
        self.gist_save_status_label.pack(pady=5)

        self.github_loading_label = ttk.Label(self.github_frame, text="Loading...", style='Loading.TLabel')
        self.github_loading_label.pack(pady=5)
        self.github_loading_label.pack_forget()


    def _create_jsonbin_editor_section(self):
        """Creates the UI elements for the JSONBin Editor."""
        self.jsonbin_editor_frame = ttk.Frame(self.content_frame, padding="20", style='Card.TFrame')
        self.jsonbin_editor_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self.jsonbin_editor_frame, text="JSONBin Editor",
                  style='Heading.TLabel').pack(pady=10)

        ttk.Label(self.jsonbin_editor_frame, text="Enter your JSONBin ID and Master Key to fetch and edit bin content.",
                  wraplength=600, style='TLabel').pack(pady=5)

        ttk.Label(self.jsonbin_editor_frame, text="JSONBin ID:", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.jsonbin_id_entry = ttk.Entry(self.jsonbin_editor_frame, width=80, style='TEntry')
        self.jsonbin_id_entry.pack(fill="x", pady=5)

        ttk.Label(self.jsonbin_editor_frame, text="JSONBin Master Key (X-Master-Key):", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.jsonbin_master_key_entry = ttk.Entry(self.jsonbin_editor_frame, show="*", width=80, style='TEntry')
        self.jsonbin_master_key_entry.pack(fill="x", pady=5)

        # Remember JSONBin credentials checkbox
        self.remember_jsonbin_creds_check = ttk.Checkbutton(self.jsonbin_editor_frame, text="Remember JSONBin ID and Master Key (Obfuscated)",
                                                            variable=self.remember_jsonbin_creds_var, style='TCheckbutton')
        self.remember_jsonbin_creds_check.pack(anchor="w", pady=(0, 10))
        ttk.Label(self.jsonbin_editor_frame, text="This key is required for write access to your bin.",
                  font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).pack(anchor="w")

        self.fetch_jsonbin_button = ttk.Button(self.jsonbin_editor_frame, text="Fetch JSONBin Content",
                                               command=self.start_fetch_jsonbin_bin, style='TButton')
        self.fetch_jsonbin_button.pack(pady=15, fill="x", ipady=5)

        self.jsonbin_editor_status_label = ttk.Label(self.jsonbin_editor_frame, text="", wraplength=700, justify="left", style='TLabel')
        self.jsonbin_editor_status_label.pack(pady=5)

        self.jsonbin_content_container = ttk.Frame(self.jsonbin_editor_frame, style='TFrame')
        self.jsonbin_content_container.pack(fill="both", expand=True, pady=10)
        self.jsonbin_content_container.pack_forget()
        self.jsonbin_content_container.grid_columnconfigure(0, weight=1)
        self.jsonbin_content_container.grid_rowconfigure(1, weight=1)

        ttk.Label(self.jsonbin_content_container, text="Bin Content (JSON):", style='TLabel').pack(anchor="w", pady=(0, 5))
        self.jsonbin_content_text = scrolledtext.ScrolledText(self.jsonbin_content_container, wrap=tk.WORD, height=15)
        self.jsonbin_content_text.pack(fill="both", expand=True, pady=5)

        self.save_jsonbin_button = ttk.Button(self.jsonbin_content_container, text="Save JSONBin Changes",
                                              command=self.start_save_jsonbin_bin, style='TButton')
        self.save_jsonbin_button.pack(pady=10, fill="x", ipady=5)

        self.jsonbin_save_status_label = ttk.Label(self.jsonbin_content_container, text="", wraplength=700, justify="left", style='TLabel')
        self.jsonbin_save_status_label.pack(pady=5)

        self.jsonbin_editor_loading_label = ttk.Label(self.jsonbin_editor_frame, text="Loading...", style='Loading.TLabel')
        self.jsonbin_editor_loading_label.pack(pady=5)
        self.jsonbin_editor_loading_label.pack_forget()

    def _create_github_repo_editor_section(self):
        """Creates the UI elements for the GitHub Repo JSON Editor."""
        self.github_repo_editor_frame = ttk.Frame(self.content_frame, padding="20", style='Card.TFrame')
        self.github_repo_editor_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self.github_repo_editor_frame, text="GitHub Repository JSON Editor",
                  style='Heading.TLabel').pack(pady=10)

        ttk.Label(self.github_repo_editor_frame, text="Security Warning: Directly using Personal Access Tokens (PATs) in client-side code is not secure for production. Use this for testing only. Ensure your PAT has `repo` scope and revoke it after use.",
                  wraplength=600, style='Warning.TLabel').pack(pady=10)

        # Reusing the PAT entry from Gist editor for consistency, but linking to repo-specific PAT input
        ttk.Label(self.github_repo_editor_frame, text="GitHub Personal Access Token (PAT):", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.github_repo_pat_entry = ttk.Entry(self.github_repo_editor_frame, show="*", width=80, style='TEntry')
        self.github_repo_pat_entry.pack(fill="x", pady=5)

        # Reusing the remember PAT checkbox from Gist editor for consistency
        self.remember_github_repo_pat_check = ttk.Checkbutton(self.github_repo_editor_frame, text="Remember GitHub PAT (Obfuscated)",
                                                              variable=self.remember_github_pat_var, style='TCheckbutton')
        self.remember_github_repo_pat_check.pack(anchor="w", pady=(0, 10))
        ttk.Label(self.github_repo_editor_frame, text="Ensure PAT has 'repo' scope for repository access.",
                  font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).pack(anchor="w")

        self.load_repos_button = ttk.Button(self.github_repo_editor_frame, text="Load My Repositories",
                                            command=self.start_load_repos, style='TButton')
        self.load_repos_button.pack(pady=15, fill="x", ipady=5)

        ttk.Label(self.github_repo_editor_frame, text="Select Repository:", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.repo_select = ttk.Combobox(self.github_repo_editor_frame, state="readonly", style='TCombobox')
        self.repo_select.pack(fill="x", pady=5)
        self.repo_select.bind("<<ComboboxSelected>>", self.on_repo_selected)
        # Prevent mouse wheel from changing selection
        self.repo_select.bind("<MouseWheel>", lambda event: "break")
        self.repo_select.bind("<Button-4>", lambda event: "break") # For Linux
        self.repo_select.bind("<Button-5>", lambda event: "break") # For Linux


        ttk.Label(self.github_repo_editor_frame, text="Select Branch:", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.branch_select = ttk.Combobox(self.github_repo_editor_frame, state="readonly", style='TCombobox')
        self.branch_select.pack(fill="x", pady=5)
        self.branch_select.bind("<<ComboboxSelected>>", self.on_branch_selected)
        # Prevent mouse wheel from changing selection
        self.branch_select.bind("<MouseWheel>", lambda event: "break")
        self.branch_select.bind("<Button-4>", lambda event: "break") # For Linux
        self.branch_select.bind("<Button-5>", lambda event: "break") # For Linux


        ttk.Label(self.github_repo_editor_frame, text="Select JSON File Path:", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.file_select_repo = ttk.Combobox(self.github_repo_editor_frame, state="readonly", style='TCombobox')
        self.file_select_repo.pack(fill="x", pady=5)
        self.file_select_repo.bind("<<ComboboxSelected>>", self.on_repo_file_selected)
        # Prevent mouse wheel from changing selection
        self.file_select_repo.bind("<MouseWheel>", lambda event: "break")
        self.file_select_repo.bind("<Button-4>", lambda event: "break") # For Linux
        self.file_select_repo.bind("<Button-5>", lambda event: "break") # For Linux


        self.fetch_repo_file_button = ttk.Button(self.github_repo_editor_frame, text="Fetch Selected JSON File",
                                                 command=self.start_fetch_repo_json_file, style='TButton')
        self.fetch_repo_file_button.pack(pady=15, fill="x", ipady=5)
        self.fetch_repo_file_button.config(state=tk.DISABLED) # Disable until repo/branch/file selected

        self.repo_editor_status_label = ttk.Label(self.github_repo_editor_frame, text="", wraplength=700, justify="left", style='TLabel')
        self.repo_editor_status_label.pack(pady=5)

        # Repo content editor (initially hidden)
        self.repo_content_container = ttk.Frame(self.github_repo_editor_frame, style='TFrame')
        self.repo_content_container.pack(fill="both", expand=True, pady=10)
        self.repo_content_container.pack_forget()
        self.repo_content_container.grid_columnconfigure(0, weight=1)
        self.repo_content_container.grid_rowconfigure(1, weight=1)

        ttk.Label(self.repo_content_container, text="Repo File Content (JSON):", style='TLabel').pack(anchor="w", pady=(0, 5))
        self.repo_file_content_text = scrolledtext.ScrolledText(self.repo_content_container, wrap=tk.WORD, height=15)
        self.repo_file_content_text.pack(fill="both", expand=True, pady=5)

        ttk.Label(self.repo_content_container, text="Commit Message:", style='TLabel').pack(anchor="w", pady=(10, 0))
        self.repo_commit_message_entry = ttk.Entry(self.repo_content_container, width=80, style='TEntry')
        self.repo_commit_message_entry.insert(0, "Update JSON file via Tkinter editor")
        self.repo_commit_message_entry.pack(fill="x", pady=5)

        self.save_repo_file_button = ttk.Button(self.repo_content_container, text="Save Repo File Changes",
                                                command=self.start_save_repo_json_file, style='TButton')
        self.save_repo_file_button.pack(pady=10, fill="x", ipady=5)
        self.save_repo_file_button.config(state=tk.DISABLED) # Disable until file loaded

        self.repo_save_status_label = ttk.Label(self.repo_content_container, text="", wraplength=700, justify="left", style='TLabel')
        self.repo_save_status_label.pack(pady=5)

        self.repo_editor_loading_label = ttk.Label(self.github_repo_editor_frame, text="Loading...", style='Loading.TLabel')
        self.repo_editor_loading_label.pack(pady=5)
        self.repo_editor_loading_label.pack_forget()

    def _create_bot_editor_section(self):
        """Creates the UI elements for the Bot Editor."""
        self.bot_editor_frame = ttk.Frame(self.content_frame, padding="20", style='Card.TFrame')
        self.bot_editor_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(self.bot_editor_frame, text="Bot Editor", style='Heading.TLabel').pack(pady=10)

        # --- Bot File Linkage Section ---
        file_link_frame = ttk.Frame(self.bot_editor_frame, padding="10", style='TFrame')
        file_link_frame.pack(fill="x", pady=10)
        file_link_frame.grid_columnconfigure(0, weight=1)
        file_link_frame.grid_columnconfigure(1, weight=0)

        ttk.Label(file_link_frame, text="Local Bot Config JSON File Path:", style='TLabel').grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.bot_config_path_entry = ttk.Entry(file_link_frame, textvariable=self.bot_config_local_file_path_var, width=60, style='TEntry')
        self.bot_config_path_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=5)

        load_save_buttons_frame = ttk.Frame(file_link_frame, style='TFrame')
        load_save_buttons_frame.grid(row=1, column=1, sticky="e")

        self.load_bot_config_button = ttk.Button(load_save_buttons_frame, text="Load Bot Config",
                                                 command=self.start_load_bot_config_local, style='TButton')
        self.load_bot_config_button.pack(side="left", padx=(0, 5))

        self.save_bot_config_button = ttk.Button(load_save_buttons_frame, text="Save Bot Config",
                                                 command=self.start_save_bot_config_local, style='TButton')
        self.save_bot_config_button.pack(side="left")

        self.bot_config_status_label = ttk.Label(file_link_frame, text="", wraplength=700, justify="left", style='TLabel')
        self.bot_config_status_label.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

        # --- Bot Settings Notebook ---
        self.bot_settings_notebook = ttk.Notebook(self.bot_editor_frame)
        self.bot_settings_notebook.pack(fill="both", expand=True, pady=10)

        # --- Basic Presence Tab ---
        basic_presence_frame = ttk.Frame(self.bot_settings_notebook, padding="15", style='TFrame')
        self.bot_settings_notebook.add(basic_presence_frame, text="Basic Presence")
        basic_presence_frame.grid_columnconfigure(0, weight=1)
        basic_presence_frame.grid_columnconfigure(1, weight=1)

        # PFP
        ttk.Label(basic_presence_frame, text="Bot Profile Picture URL:", style='TLabel').grid(row=0, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(basic_presence_frame, textvariable=self.bot_pfp_url_var, width=50, style='TEntry').grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(basic_presence_frame, text="Note: PFP change requires bot restart to take effect.", font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).grid(row=2, column=0, columnspan=2, sticky="w")


        # Online Status
        ttk.Label(basic_presence_frame, text="Online Status:", style='TLabel').grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.status_combobox = ttk.Combobox(basic_presence_frame, textvariable=self.bot_status_var,
                                            values=["online", "idle", "dnd", "invisible"], state="readonly", style='TCombobox')
        self.status_combobox.grid(row=4, column=0, sticky="ew", pady=5, padx=(0, 10))
        self.status_combobox.set("online") # Default value
        self.status_combobox.bind("<MouseWheel>", lambda event: "break")
        self.status_combobox.bind("<Button-4>", lambda event: "break")
        self.status_combobox.bind("<Button-5>", lambda event: "break")

        # Activity Type
        ttk.Label(basic_presence_frame, text="Activity Type:", style='TLabel').grid(row=3, column=1, sticky="w", pady=(10, 0))
        self.activity_type_combobox = ttk.Combobox(basic_presence_frame, textvariable=self.bot_activity_type_var,
                                                   values=["playing", "streaming", "listening", "watching", "competing"], state="readonly", style='TCombobox')
        self.activity_type_combobox.grid(row=4, column=1, sticky="ew", pady=5)
        self.activity_type_combobox.set("playing") # Default value
        self.activity_type_combobox.bind("<MouseWheel>", lambda event: "break")
        self.activity_type_combobox.bind("<Button-4>", lambda event: "break")
        self.activity_type_combobox.bind("<Button-5>", lambda event: "break")

        # Activity Name
        ttk.Label(basic_presence_frame, text="Activity Name:", style='TLabel').grid(row=5, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(basic_presence_frame, textvariable=self.bot_activity_name_var, width=50, style='TEntry').grid(row=6, column=0, columnspan=2, sticky="ew", pady=5)

        # --- Rich Presence Tab ---
        rich_presence_frame = ttk.Frame(self.bot_settings_notebook, padding="15", style='TFrame')
        self.bot_settings_notebook.add(rich_presence_frame, text="Rich Presence (Advanced)")
        rich_presence_frame.grid_columnconfigure(0, weight=1)
        rich_presence_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(rich_presence_frame, text="Details:", style='TLabel').grid(row=0, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(rich_presence_frame, textvariable=self.bot_rp_details_var, width=50, style='TEntry').grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(rich_presence_frame, text="State:", style='TLabel').grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(rich_presence_frame, textvariable=self.bot_rp_state_var, width=50, style='TEntry').grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(rich_presence_frame, text="Large Image URL:", style='TLabel').grid(row=4, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(rich_presence_frame, textvariable=self.bot_rp_large_image_url_var, width=50, style='TEntry').grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(rich_presence_frame, text="Large Image Text:", style='TLabel').grid(row=6, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(rich_presence_frame, textvariable=self.bot_rp_large_image_text_var, width=50, style='TEntry').grid(row=7, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(rich_presence_frame, text="Small Image URL:", style='TLabel').grid(row=8, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(rich_presence_frame, textvariable=self.bot_rp_small_image_url_var, width=50, style='TEntry').grid(row=9, column=0, columnspan=2, sticky="ew", pady=5)

        ttk.Label(rich_presence_frame, text="Small Image Text:", style='TLabel').grid(row=10, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(rich_presence_frame, textvariable=self.bot_rp_small_image_text_var, width=50, style='TEntry').grid(row=11, column=0, columnspan=2, sticky="ew", pady=5)

        # Timestamps
        timestamp_label_frame = ttk.Frame(rich_presence_frame, style='TFrame')
        timestamp_label_frame.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        timestamp_label_frame.grid_columnconfigure(0, weight=1)
        timestamp_label_frame.grid_columnconfigure(1, weight=1)
        ttk.Label(timestamp_label_frame, text="Start Timestamp (Unix):", style='TLabel').grid(row=0, column=0, sticky="w")
        ttk.Label(timestamp_label_frame, text="End Timestamp (Unix):", style='TLabel').grid(row=0, column=1, sticky="w")

        timestamp_input_frame = ttk.Frame(rich_presence_frame, style='TFrame')
        timestamp_input_frame.grid(row=13, column=0, columnspan=2, sticky="ew", pady=5)
        timestamp_input_frame.grid_columnconfigure(0, weight=1)
        timestamp_input_frame.grid_columnconfigure(1, weight=0)
        timestamp_input_frame.grid_columnconfigure(2, weight=1)
        timestamp_input_frame.grid_columnconfigure(3, weight=0)

        ttk.Entry(timestamp_input_frame, textvariable=self.bot_rp_start_timestamp_var, width=20, style='TEntry').grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(timestamp_input_frame, text="Set Now", command=lambda: self._set_timestamp(self.bot_rp_start_timestamp_var), style='TButton').grid(row=0, column=1, sticky="w")

        ttk.Entry(timestamp_input_frame, textvariable=self.bot_rp_end_timestamp_var, width=20, style='TEntry').grid(row=0, column=2, sticky="ew", padx=(10, 5))
        ttk.Button(timestamp_input_frame, text="Set Now", command=lambda: self._set_timestamp(self.bot_rp_end_timestamp_var), style='TButton').grid(row=0, column=3, sticky="w")

        # --- General Settings Tab ---
        general_settings_frame = ttk.Frame(self.bot_settings_notebook, padding="15", style='TFrame')
        self.bot_settings_notebook.add(general_settings_frame, text="General Settings")
        general_settings_frame.grid_columnconfigure(0, weight=1)
        general_settings_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(general_settings_frame, text="Command Prefix:", style='TLabel').grid(row=0, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(general_settings_frame, textvariable=self.bot_command_prefix_var, width=20, style='TEntry').grid(row=1, column=0, sticky="ew", pady=5, padx=(0, 10))
        ttk.Label(general_settings_frame, text="Note: Primarily for text commands, slash commands are preferred.", font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Label(general_settings_frame, text="Log Channel ID:", style='TLabel').grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(general_settings_frame, textvariable=self.bot_log_channel_id_var, width=50, style='TEntry').grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(general_settings_frame, text="Bot will send important messages/errors to this channel.", font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).grid(row=5, column=0, columnspan=2, sticky="w")

        # --- Welcome Message Tab ---
        welcome_message_frame = ttk.Frame(self.bot_settings_notebook, padding="15", style='TFrame')
        self.bot_settings_notebook.add(welcome_message_frame, text="Welcome Message")
        welcome_message_frame.grid_columnconfigure(0, weight=1)
        welcome_message_frame.grid_columnconfigure(1, weight=1)

        ttk.Checkbutton(welcome_message_frame, text="Enable Welcome Message", variable=self.bot_welcome_enabled_var, style='TCheckbutton').grid(row=0, column=0, columnspan=2, sticky="w", pady=(10, 5))

        ttk.Label(welcome_message_frame, text="Welcome Channel ID:", style='TLabel').grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(welcome_message_frame, textvariable=self.bot_welcome_channel_id_var, width=50, style='TEntry').grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(welcome_message_frame, text="The channel where welcome messages will be sent.", font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).grid(row=3, column=0, columnspan=2, sticky="w")

        ttk.Label(welcome_message_frame, text="Welcome Message Content:", style='TLabel').grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.welcome_message_text = scrolledtext.ScrolledText(welcome_message_frame, wrap=tk.WORD, height=5)
        self.welcome_message_text.grid(row=5, column=0, columnspan=2, sticky="ew", pady=5)
        ttk.Label(welcome_message_frame, text="Use {member} to mention the new user.", font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).grid(row=6, column=0, columnspan=2, sticky="w")

        # --- Rate Limit Tab ---
        rate_limit_frame = ttk.Frame(self.bot_settings_notebook, padding="15", style='TFrame')
        self.bot_settings_notebook.add(rate_limit_frame, text="Rate Limits")
        rate_limit_frame.grid_columnconfigure(0, weight=1)
        rate_limit_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(rate_limit_frame, text="Max Embeds per Period:", style='TLabel').grid(row=0, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(rate_limit_frame, textvariable=self.bot_max_embeds_var, width=10, style='TEntry').grid(row=1, column=0, sticky="ew", pady=5, padx=(0, 10))
        ttk.Label(rate_limit_frame, text="Maximum number of embeds the bot can send.", font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).grid(row=2, column=0, columnspan=2, sticky="w")

        ttk.Label(rate_limit_frame, text="Period Seconds:", style='TLabel').grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(rate_limit_frame, textvariable=self.bot_period_seconds_var, width=10, style='TEntry').grid(row=4, column=0, sticky="ew", pady=5, padx=(0, 10))
        ttk.Label(rate_limit_frame, text="Time period (in seconds) for the rate limit.", font=("Segoe UI", 9, "italic"), foreground=self.colors["text"]).grid(row=5, column=0, columnspan=2, sticky="w")


        self.bot_editor_loading_label = ttk.Label(self.bot_editor_frame, text="Loading...", style='Loading.TLabel')
        self.bot_editor_loading_label.pack(pady=5)
        self.bot_editor_loading_label.pack_forget()


    def show_section(self, section_name):
        """Hides all sections and shows the specified one."""
        for frame in [self.jsonbin_tester_frame, self.github_frame, self.jsonbin_editor_frame, self.github_repo_editor_frame, self.bot_editor_frame]:
            frame.grid_forget()

        self.jsonbin_tester_btn.config(style='Nav.TButton')
        self.github_btn.config(style='Nav.TButton')
        self.jsonbin_editor_btn.config(style='Nav.TButton')
        self.github_repo_btn.config(style='Nav.TButton')
        self.bot_editor_btn.config(style='Nav.TButton')

        if section_name == "jsonbin_tester":
            self.jsonbin_tester_frame.grid(row=0, column=1, sticky="")
            self.jsonbin_tester_btn.config(style='Active.Nav.TButton')
        elif section_name == "github_gist_editor":
            self.github_frame.grid(row=0, column=1, sticky="")
            self.github_btn.config(style='Active.Nav.TButton')
        elif section_name == "jsonbin_editor":
            self.jsonbin_editor_frame.grid(row=0, column=1, sticky="")
            self.jsonbin_editor_btn.config(style='Active.TButton')
        elif section_name == "github_repo_editor":
            self.github_repo_editor_frame.grid(row=0, column=1, sticky="")
            self.github_repo_btn.config(style='Active.Nav.TButton')
        elif section_name == "bot_editor":
            self.bot_editor_frame.grid(row=0, column=1, sticky="")
            self.bot_editor_btn.config(style='Active.Nav.TButton')
            # Automatically try to load bot config when switching to this tab
            self.start_load_bot_config_local()


        self.root.update_idletasks()
        self._on_frame_configure(None)


    # --- Credential Management ---
    def _load_credentials(self):
        """Loads obfuscated credentials from a local file."""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    creds = json.load(f)

                # Load GitHub PAT
                if creds.get("remember_github_pat"):
                    encrypted_pat = creds.get("github_pat", "")
                    decrypted_pat = _xor_decrypt_decode(encrypted_pat, ENCRYPTION_KEY)
                    if decrypted_pat:
                        self.github_pat_entry.delete(0, tk.END)
                        self.github_pat_entry.insert(0, decrypted_pat)
                        self.github_repo_pat_entry.delete(0, tk.END) # Also update repo PAT entry
                        self.github_repo_pat_entry.insert(0, decrypted_pat)
                        self.remember_github_pat_var.set(True)
                else:
                    self.remember_github_pat_var.set(False)

                # Load JSONBin credentials
                if creds.get("remember_jsonbin_creds"):
                    encrypted_id = creds.get("jsonbin_id", "")
                    encrypted_key = creds.get("jsonbin_master_key", "")
                    decrypted_id = _xor_decrypt_decode(encrypted_id, ENCRYPTION_KEY)
                    decrypted_key = _xor_decrypt_decode(encrypted_key, ENCRYPTION_KEY)
                    if decrypted_id:
                        self.jsonbin_id_entry.delete(0, tk.END)
                        self.jsonbin_id_entry.insert(0, decrypted_id)
                    if decrypted_key:
                        self.jsonbin_master_key_entry.delete(0, tk.END)
                        self.jsonbin_master_key_entry.insert(0, decrypted_key)
                    if decrypted_id or decrypted_key: # Set checkbox if any JSONBin creds were loaded
                        self.remember_jsonbin_creds_var.set(True)
                else:
                    self.remember_jsonbin_creds_var.set(False)

            except (json.JSONDecodeError, IOError, Exception) as e:
                print(f"Error loading credentials: {e}")
                messagebox.showwarning("Credential Load Error", f"Could not load saved credentials. File might be corrupted or missing. Error: {e}")
                # Reset checkboxes if load fails
                self.remember_github_pat_var.set(False)
                self.remember_jsonbin_creds_var.set(False)

    def _save_credentials(self):
        """Saves obfuscated credentials to a local file based on 'remember' checkboxes."""
        creds_to_save = {}

        # GitHub PAT
        if self.remember_github_pat_var.get():
            pat = self.github_pat_entry.get().strip()
            if pat:
                creds_to_save["github_pat"] = _xor_encrypt_decrypt(pat, ENCRYPTION_KEY)
                creds_to_save["remember_github_pat"] = True
            else:
                creds_to_save["remember_github_pat"] = False # Don't save if PAT is empty
        else:
            creds_to_save["remember_github_pat"] = False

        # JSONBin credentials
        if self.remember_jsonbin_creds_var.get():
            jsonbin_id = self.jsonbin_id_entry.get().strip()
            jsonbin_key = self.jsonbin_master_key_entry.get().strip()
            if jsonbin_id or jsonbin_key: # Save if at least one is present
                creds_to_save["jsonbin_id"] = _xor_encrypt_decrypt(jsonbin_id, ENCRYPTION_KEY)
                creds_to_save["jsonbin_master_key"] = _xor_encrypt_decrypt(jsonbin_key, ENCRYPTION_KEY)
                creds_to_save["remember_jsonbin_creds"] = True
            else:
                creds_to_save["remember_jsonbin_creds"] = False # Don't save if both are empty
        else:
            creds_to_save["remember_jsonbin_creds"] = False

        try:
            with open(self.credentials_file, 'w') as f:
                json.dump(creds_to_save, f, indent=4)
        except IOError as e:
            print(f"Error saving credentials: {e}")
            messagebox.showerror("Credential Save Error", f"Could not save credentials to file. Error: {e}")


    # --- JSONBin Tester Logic ---
    def start_jsonbin_test(self):
        """Starts the JSONBin test in a separate thread."""
        self.jsonbin_tester_loading_label.pack()
        self.jsonbin_tester_result_label.config(text="Fetching...", style='Loading.TLabel')
        self.test_button.config(state=tk.DISABLED)

        future = self.executor.submit(self._fetch_jsonbin_credentials_threaded)
        future.add_done_callback(self._update_jsonbin_result)

    def _fetch_jsonbin_credentials_threaded(self):
        """Performs the JSONBin credential fetch (runs in a separate thread)."""
        original_url = self.creds_url_entry.get()
        PROXY_URL = f"https://api.allorigins.win/raw?url={requests.utils.quote(original_url)}"
        timeout_duration = 15

        try:
            response = requests.get(PROXY_URL, timeout=timeout_duration)
            response.raise_for_status()

            creds_data = response.json()

            if 'JSONBIN_BIN_ID' in creds_data:
                bin_id = creds_data['JSONBIN_BIN_ID']
                return {
                    "success": True,
                    "message": "Successfully fetched JSONBIN_BIN_ID via proxy.",
                    "binId": bin_id
                }
            else:
                return {
                    "success": False,
                    "message": f"Error: 'JSONBIN_BIN_ID' not found in the response from {original_url}. Response content: {json.dumps(creds_data, indent=2)}",
                    "binId": None
                }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "message": f"Error: Request to {original_url} timed out after {timeout_duration} seconds. Check network or URL. (Via proxy)",
                "binId": None
            }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "message": f"Error fetching JSONBin BIN_ID from {original_url}: {e}. Ensure URL is correct and server is reachable. (Via proxy)",
                "binId": None
            }
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "message": f"Error decoding JSON response from {original_url}: {e}. Ensure the file is valid JSON. (Via proxy). Raw response: {response.text if 'response' in locals() else 'N/A'}",
                "binId": None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"An unexpected error occurred during credential fetch from {original_url}: {e} (Via proxy)",
                "binId": None
            }

    def _update_jsonbin_result(self, future):
        """Updates the GUI with JSONBin test results (runs in main thread)."""
        result = future.result()
        self.jsonbin_tester_loading_label.pack_forget()
        self.test_button.config(state=tk.NORMAL)

        if result["success"]:
            self.jsonbin_tester_result_label.config(text=f"✅ Success!\nMessage: {result['message']}\nJSONBIN_BIN_ID: {result['binId']}",
                                            style='Success.TLabel')
        else:
            self.jsonbin_tester_result_label.config(text=f"❌ Error!\nMessage: {result['message']}",
                                            style='Error.TLabel')

    # --- GitHub Gist Editor Logic ---
    def start_github_login(self):
        """Starts the GitHub login process in a separate thread."""
        self.github_token = self.github_pat_entry.get().strip()
        if not self.github_token:
            self.github_status_label.config(text="Please enter a GitHub Personal Access Token.", style='Error.TLabel')
            return

        # Save credentials if "Remember" is checked
        self._save_credentials()

        self.github_loading_label.pack()
        self.github_status_label.config(text="Logging in and fetching gists...", style='Loading.TLabel')
        self.login_github_button.config(state=tk.DISABLED)
        self.gist_content_frame.pack_forget()
        self.gist_select.set('')
        self.gist_select['values'] = []
        self.file_select_container.pack_forget()
        self.gist_editor_container.pack_forget()
        self.gist_file_content_text.delete(1.0, tk.END)
        self.gist_save_status_label.config(text="")

        future = self.executor.submit(self._fetch_github_gists_threaded)
        future.add_done_callback(self._update_github_login_status)

    def _fetch_github_gists_threaded(self):
        """Fetches user's gists from GitHub (runs in a separate thread)."""
        headers = {'Authorization': f'token {self.github_token}'}
        try:
            response = requests.get('https://api.github.com/gists', headers=headers, timeout=10)
            response.raise_for_status()
            gists = response.json()
            return {"success": True, "gists": gists}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error fetching gists: {e}"}

    def _update_github_login_status(self, future):
        """Updates GUI after GitHub login attempt (runs in main thread)."""
        result = future.result()
        self.github_loading_label.pack_forget()
        self.login_github_button.config(state=tk.NORMAL)

        if result["success"]:
            self.github_status_label.config(text="✅ Successfully logged in and fetched gists.", style='Success.TLabel')
            gist_names = []
            self.gists_map = {} # Store gist_id -> full_gist_data
            for gist in result["gists"]:
                gist_id = gist['id']
                description = gist.get('description', 'No description')
                # Prioritize a .json file name if available, otherwise use description
                file_names = list(gist['files'].keys())
                json_files = [f for f in file_names if f.endswith('.json')]
                display_name = description
                if json_files:
                    display_name = f"{json_files[0]} ({description})" if description else json_files[0]
                elif file_names:
                    display_name = f"{file_names[0]} ({description})" if description else file_names[0]

                gist_names.append(display_name)
                self.gists_map[display_name] = gist # Map display name back to full gist data

            self.gist_select['values'] = gist_names
            if gist_names:
                self.gist_content_frame.pack(fill="both", expand=True)
            else:
                self.github_status_label.config(text="No gists found for this account.", style='Info.TLabel')
        else:
            self.github_status_label.config(text=f"❌ Login failed: {result['message']}", style='Error.TLabel')

    def on_gist_selected(self, event):
        """Handles gist selection, populating file dropdown."""
        selected_display_name = self.gist_select.get()
        self.current_gist_data = self.gists_map.get(selected_display_name)
        self.current_gist_id = self.current_gist_data['id'] if self.current_gist_data else None

        self.file_select.set('')
        self.file_select['values'] = []
        self.file_select_container.pack_forget()
        self.gist_editor_container.pack_forget()
        self.gist_file_content_text.delete(1.0, tk.END)
        self.gist_save_status_label.config(text="")

        if self.current_gist_data:
            file_names = list(self.current_gist_data['files'].keys())
            self.file_select['values'] = file_names
            if file_names:
                self.file_select_container.pack(fill="x")
                # Automatically select the first file if there's only one
                if len(file_names) == 1:
                    self.file_select.set(file_names[0])
                    self.on_file_selected(None) # Manually trigger selection

    def on_file_selected(self, event):
        """Handles file selection within a gist, fetching its content."""
        self.current_file_name = self.file_select.get()
        self.gist_editor_container.pack_forget()
        self.gist_file_content_text.delete(1.0, tk.END)
        self.gist_save_status_label.config(text="")

        if self.current_gist_data and self.current_file_name:
            file_info = self.current_gist_data['files'].get(self.current_file_name)
            if file_info and 'raw_url' in file_info:
                self.github_loading_label.pack()
                self.gist_save_status_label.config(text="Fetching file content...", style='Loading.TLabel')
                self.save_gist_button.config(state=tk.DISABLED)

                future = self.executor.submit(self._fetch_gist_file_content_threaded, file_info['raw_url'])
                future.add_done_callback(self._update_gist_file_content)
            else:
                self.gist_save_status_label.config(text="Selected file has no content URL.", style='Error.TLabel')

    def _fetch_gist_file_content_threaded(self, raw_url):
        """Fetches the raw content of a gist file (runs in a separate thread)."""
        headers = {'Authorization': f'token {self.github_token}'}
        try:
            response = requests.get(raw_url, headers=headers, timeout=10)
            response.raise_for_status()
            return {"success": True, "content": response.text}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error fetching file content: {e}"}

    def _update_gist_file_content(self, future):
        """Updates GUI with gist file content (runs in main thread)."""
        result = future.result()
        self.github_loading_label.pack_forget()
        self.save_gist_button.config(state=tk.NORMAL)

        if result["success"]:
            self.gist_file_content_text.delete(1.0, tk.END)
            self.gist_file_content_text.insert(1.0, result["content"])
            self.gist_editor_container.pack(fill="both", expand=True)
            self.gist_save_status_label.config(text="File content loaded. You can now edit and save.", style='Info.TLabel')
        else:
            self.gist_save_status_label.config(text=f"❌ Error loading file content: {result['message']}", style='Error.TLabel')

    def start_save_gist(self):
        """Starts saving gist changes in a separate thread."""
        if not self.current_gist_id or not self.current_file_name:
            self.gist_save_status_label.config(text="No gist or file selected for saving.", style='Error.TLabel')
            return

        new_content = self.gist_file_content_text.get(1.0, tk.END).strip()
        if not new_content:
            self.gist_save_status_label.config(text="File content cannot be empty.", style='Error.TLabel')
            return

        self.github_loading_label.pack()
        self.gist_save_status_label.config(text="Saving gist changes...", style='Loading.TLabel')
        self.save_gist_button.config(state=tk.DISABLED)

        future = self.executor.submit(self._save_gist_threaded, new_content)
        future.add_done_callback(self._update_save_gist_status)

    def _save_gist_threaded(self, new_content):
        """Saves changes to the current gist file (runs in a separate thread)."""
        headers = {'Authorization': f'token {self.github_token}'}
        gist_url = f'https://api.github.com/gists/{self.current_gist_id}'
        payload = {
            "files": {
                self.current_file_name: {
                    "content": new_content
                }
            }
        }
        try:
            response = requests.patch(gist_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            return {"success": True, "message": "Gist updated successfully."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error saving gist: {e}"}

    def _update_save_gist_status(self, future):
        """Updates GUI after gist save attempt (runs in main thread)."""
        result = future.result()
        self.github_loading_label.pack_forget()
        self.save_gist_button.config(state=tk.NORMAL)

        if result["success"]:
            self.gist_save_status_label.config(text=f"✅ {result['message']}", style='Success.TLabel')
            # Refresh gist data after saving to get updated content/info
            self.start_github_login()
        else:
            self.gist_save_status_label.config(text=f"❌ {result['message']}", style='Error.TLabel')

    # --- JSONBin Editor Logic ---
    def start_fetch_jsonbin_bin(self):
        """Starts fetching JSONBin content in a separate thread."""
        self.current_jsonbin_id = self.jsonbin_id_entry.get().strip()
        self.jsonbin_master_key = self.jsonbin_master_key_entry.get().strip()

        if not self.current_jsonbin_id:
            self.jsonbin_editor_status_label.config(text="Please enter a JSONBin ID.", style='Error.TLabel')
            return

        # Master key is optional for public bins, but required for private/write
        # if not self.jsonbin_master_key:
        #     self.jsonbin_editor_status_label.config(text="Please enter a JSONBin Master Key.", style='Error.TLabel')
        #     return

        # Save credentials if "Remember" is checked
        self._save_credentials()

        self.jsonbin_editor_loading_label.pack()
        self.jsonbin_editor_status_label.config(text="Fetching JSONBin content...", style='Loading.TLabel')
        self.fetch_jsonbin_button.config(state=tk.DISABLED)
        self.jsonbin_content_container.pack_forget()
        self.jsonbin_content_text.delete(1.0, tk.END)
        self.jsonbin_save_status_label.config(text="")

        future = self.executor.submit(self._fetch_jsonbin_bin_threaded)
        future.add_done_callback(self._update_fetch_jsonbin_bin_status)

    def _fetch_jsonbin_bin_threaded(self):
        """Fetches content from JSONBin (runs in a separate thread)."""
        headers = {'X-Master-Key': self.jsonbin_master_key} if self.jsonbin_master_key else {}
        jsonbin_url = f'https://api.jsonbin.io/v3/b/{self.current_jsonbin_id}/latest'
        try:
            response = requests.get(jsonbin_url, headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            # JSONBin API returns {"record": ..., "metadata": ...}
            if "record" in data:
                return {"success": True, "record": data["record"]}
            else:
                return {"success": False, "message": f"Invalid JSONBin response structure: 'record' key missing. Full response: {json.dumps(data, indent=2)}"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error fetching JSONBin: {e}. Check ID and Master Key."}
        except json.JSONDecodeError as e:
            return {"success": False, "message": f"Error decoding JSONBin response: {e}. Raw response: {response.text if 'response' in locals() else 'N/A'}"}

    def _update_fetch_jsonbin_bin_status(self, future):
        """Updates GUI after JSONBin fetch attempt (runs in main thread)."""
        result = future.result()
        self.jsonbin_editor_loading_label.pack_forget()
        self.fetch_jsonbin_button.config(state=tk.NORMAL)

        if result["success"]:
            self.jsonbin_editor_status_label.config(text="✅ JSONBin content fetched successfully.", style='Success.TLabel')
            self.current_jsonbin_record_data = result["record"]
            try:
                formatted_json = json.dumps(self.current_jsonbin_record_data, indent=4)
                self.jsonbin_content_text.delete(1.0, tk.END)
                self.jsonbin_content_text.insert(1.0, formatted_json)
                self.jsonbin_content_container.pack(fill="both", expand=True)
                self.save_jsonbin_button.config(state=tk.NORMAL)
                self.jsonbin_save_status_label.config(text="Content loaded. You can now edit and save.", style='Info.TLabel')
            except Exception as e:
                self.jsonbin_editor_status_label.config(text=f"❌ Error formatting JSON: {e}", style='Error.TLabel')
                self.jsonbin_content_container.pack_forget()
                self.save_jsonbin_button.config(state=tk.DISABLED)
        else:
            self.jsonbin_editor_status_label.config(text=f"❌ Error fetching JSONBin: {result['message']}", style='Error.TLabel')
            self.jsonbin_content_container.pack_forget()
            self.save_jsonbin_button.config(state=tk.DISABLED)

    def start_save_jsonbin_bin(self):
        """Starts saving JSONBin content in a separate thread."""
        if not self.current_jsonbin_id or not self.jsonbin_master_key:
            self.jsonbin_save_status_label.config(text="JSONBin ID and Master Key are required to save.", style='Error.TLabel')
            return

        new_content_str = self.jsonbin_content_text.get(1.0, tk.END).strip()
        if not new_content_str:
            self.jsonbin_save_status_label.config(text="Content cannot be empty.", style='Error.TLabel')
            return

        try:
            new_content_json = json.loads(new_content_str)
        except json.JSONDecodeError as e:
            self.jsonbin_save_status_label.config(text=f"Invalid JSON format: {e}", style='Error.TLabel')
            return

        self.jsonbin_editor_loading_label.pack()
        self.jsonbin_save_status_label.config(text="Saving JSONBin changes...", style='Loading.TLabel')
        self.save_jsonbin_button.config(state=tk.DISABLED)

        future = self.executor.submit(self._save_jsonbin_bin_threaded, new_content_json)
        future.add_done_callback(self._update_save_jsonbin_bin_status)

    def _save_jsonbin_bin_threaded(self, new_content):
        """Saves content to JSONBin (runs in a separate thread)."""
        headers = {
            'Content-Type': 'application/json',
            'X-Master-Key': self.jsonbin_master_key
        }
        jsonbin_url = f'https://api.jsonbin.io/v3/b/{self.current_jsonbin_id}'
        try:
            response = requests.put(jsonbin_url, headers=headers, json=new_content, timeout=10)
            response.raise_for_status()
            return {"success": True, "message": "JSONBin updated successfully."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error saving JSONBin: {e}. Check ID, Master Key, and permissions."}
        except Exception as e:
            return {"success": False, "message": f"An unexpected error occurred during save: {e}"}

    def _update_save_jsonbin_bin_status(self, future):
        """Updates GUI after JSONBin save attempt (runs in main thread)."""
        result = future.result()
        self.jsonbin_editor_loading_label.pack_forget()
        self.save_jsonbin_button.config(state=tk.NORMAL)

        if result["success"]:
            self.jsonbin_save_status_label.config(text=f"✅ {result['message']}", style='Success.TLabel')
            # Optionally re-fetch to confirm save
            self.start_fetch_jsonbin_bin()
        else:
            self.jsonbin_save_status_label.config(text=f"❌ {result['message']}", style='Error.TLabel')

    # --- GitHub Repo Editor Logic ---
    def start_load_repos(self):
        """Starts loading user repositories in a separate thread."""
        self.github_token = self.github_repo_pat_entry.get().strip()
        if not self.github_token:
            self.repo_editor_status_label.config(text="Please enter a GitHub Personal Access Token.", style='Error.TLabel')
            return

        self._save_credentials() # Save PAT

        self.repo_editor_loading_label.pack()
        self.repo_editor_status_label.config(text="Loading repositories...", style='Loading.TLabel')
        self.load_repos_button.config(state=tk.DISABLED)
        self.repo_select.set('')
        self.repo_select['values'] = []
        self.branch_select.set('')
        self.branch_select['values'] = []
        self.file_select_repo.set('')
        self.file_select_repo['values'] = []
        self.fetch_repo_file_button.config(state=tk.DISABLED)
        self.repo_content_container.pack_forget()
        self.repo_file_content_text.delete(1.0, tk.END)
        self.save_repo_file_button.config(state=tk.DISABLED)
        self.repo_save_status_label.config(text="")

        future = self.executor.submit(self._fetch_user_repos_threaded)
        future.add_done_callback(self._update_load_repos_status)

    def _fetch_user_repos_threaded(self):
        """Fetches user's repositories from GitHub (runs in a separate thread)."""
        headers = {'Authorization': f'token {self.github_token}'}
        try:
            response = requests.get('https://api.github.com/user/repos?type=owner', headers=headers, timeout=10)
            response.raise_for_status()
            repos = response.json()
            return {"success": True, "repos": repos}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error fetching repositories: {e}"}

    def _update_load_repos_status(self, future):
        """Updates GUI after loading repositories (runs in main thread)."""
        result = future.result()
        self.repo_editor_loading_label.pack_forget()
        self.load_repos_button.config(state=tk.NORMAL)

        if result["success"]:
            self.repo_editor_status_label.config(text="✅ Repositories loaded.", style='Success.TLabel')
            repo_names = []
            self.all_user_repos = {}
            for repo in result["repos"]:
                full_name = repo['full_name']
                repo_names.append(full_name)
                self.all_user_repos[full_name] = {'owner': repo['owner']['login'], 'name': repo['name']}
            self.repo_select['values'] = repo_names
            if not repo_names:
                self.repo_editor_status_label.config(text="No repositories found for this account.", style='Info.TLabel')
        else:
            self.repo_editor_status_label.config(text=f"❌ Failed to load repositories: {result['message']}", style='Error.TLabel')

    def on_repo_selected(self, event):
        """Handles repository selection, fetching its branches."""
        selected_repo_full_name = self.repo_select.get()
        repo_info = self.all_user_repos.get(selected_repo_full_name)
        if repo_info:
            self.current_repo_owner = repo_info['owner']
            self.current_repo_name = repo_info['name']
            self.branch_select.set('')
            self.branch_select['values'] = []
            self.file_select_repo.set('')
            self.file_select_repo['values'] = []
            self.fetch_repo_file_button.config(state=tk.DISABLED)
            self.repo_content_container.pack_forget()
            self.repo_file_content_text.delete(1.0, tk.END)
            self.save_repo_file_button.config(state=tk.DISABLED)
            self.repo_save_status_label.config(text="")

            self.repo_editor_loading_label.pack()
            self.repo_editor_status_label.config(text=f"Loading branches for {selected_repo_full_name}...", style='Loading.TLabel')
            self.load_repos_button.config(state=tk.DISABLED) # Disable main load button during this operation

            future = self.executor.submit(self._fetch_repo_branches_threaded, self.current_repo_owner, self.current_repo_name)
            future.add_done_callback(self._update_repo_branches_status)

    def _fetch_repo_branches_threaded(self, owner, repo_name):
        """Fetches branches for a selected repository (runs in a separate thread)."""
        headers = {'Authorization': f'token {self.github_token}'}
        branches_url = f'https://api.github.com/repos/{owner}/{repo_name}/branches'
        try:
            response = requests.get(branches_url, headers=headers, timeout=10)
            response.raise_for_status()
            branches = response.json()
            return {"success": True, "branches": [b['name'] for b in branches]}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error fetching branches: {e}"}

    def _update_repo_branches_status(self, future):
        """Updates GUI after fetching branches (runs in main thread)."""
        result = future.result()
        self.repo_editor_loading_label.pack_forget()
        self.load_repos_button.config(state=tk.NORMAL) # Re-enable main load button

        if result["success"]:
            self.repo_editor_status_label.config(text="✅ Branches loaded.", style='Success.TLabel')
            self.repo_branches = result["branches"]
            self.branch_select['values'] = self.repo_branches
            if self.repo_branches:
                self.branch_select.set(self.repo_branches[0]) # Select first branch by default
                self.on_branch_selected(None) # Trigger file loading for default branch
            else:
                self.repo_editor_status_label.config(text="No branches found for this repository.", style='Info.TLabel')
        else:
            self.repo_editor_status_label.config(text=f"❌ Failed to load branches: {result['message']}", style='Error.TLabel')

    def on_branch_selected(self, event):
        """Handles branch selection, fetching JSON files in that branch."""
        self.current_repo_branch = self.branch_select.get()
        self.file_select_repo.set('')
        self.file_select_repo['values'] = []
        self.fetch_repo_file_button.config(state=tk.DISABLED)
        self.repo_content_container.pack_forget()
        self.repo_file_content_text.delete(1.0, tk.END)
        self.save_repo_file_button.config(state=tk.DISABLED)
        self.repo_save_status_label.config(text="")

        if self.current_repo_owner and self.current_repo_name and self.current_repo_branch:
            self.repo_editor_loading_label.pack()
            self.repo_editor_status_label.config(text=f"Loading JSON files in branch '{self.current_repo_branch}'...", style='Loading.TLabel')
            self.load_repos_button.config(state=tk.DISABLED)

            future = self.executor.submit(self._fetch_repo_json_files_threaded, self.current_repo_owner, self.current_repo_name, self.current_repo_branch)
            future.add_done_callback(self._update_repo_json_files_status)

    def _fetch_repo_json_files_threaded(self, owner, repo_name, branch):
        """Recursively fetches all JSON files in a repository branch (runs in a separate thread)."""
        headers = {'Authorization': f'token {self.github_token}'}
        tree_url = f'https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}?recursive=1'
        try:
            response = requests.get(tree_url, headers=headers, timeout=15)
            response.raise_for_status()
            tree_data = response.json()
            json_files = []
            if 'tree' in tree_data:
                for item in tree_data['tree']:
                    if item['type'] == 'blob' and item['path'].endswith('.json'):
                        json_files.append(item['path'])
            return {"success": True, "files": json_files}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error fetching repository tree: {e}"}

    def _update_repo_json_files_status(self, future):
        """Updates GUI after fetching JSON files (runs in main thread)."""
        result = future.result()
        self.repo_editor_loading_label.pack_forget()
        self.load_repos_button.config(state=tk.NORMAL)

        if result["success"]:
            self.repo_editor_status_label.config(text="✅ JSON files listed.", style='Success.TLabel')
            self.repo_json_files = result["files"]
            self.file_select_repo['values'] = self.repo_json_files
            if self.repo_json_files:
                self.fetch_repo_file_button.config(state=tk.NORMAL)
                self.file_select_repo.set(self.repo_json_files[0]) # Select first file by default
                # No automatic fetch here, user must click "Fetch Selected JSON File"
            else:
                self.repo_editor_status_label.config(text="No JSON files found in this branch.", style='Info.TLabel')
        else:
            self.repo_editor_status_label.config(text=f"❌ Failed to list JSON files: {result['message']}", style='Error.TLabel')

    def on_repo_file_selected(self, event):
        """Sets the current selected file path for the repository."""
        self.current_repo_file_path = self.file_select_repo.get()
        self.repo_content_container.pack_forget()
        self.repo_file_content_text.delete(1.0, tk.END)
        self.save_repo_file_button.config(state=tk.DISABLED)
        self.repo_save_status_label.config(text="File selected. Click 'Fetch Selected JSON File' to load content.", style='Info.TLabel')

    def start_fetch_repo_json_file(self):
        """Starts fetching the content of the selected repository JSON file."""
        if not self.current_repo_owner or not self.current_repo_name or not self.current_repo_branch or not self.current_repo_file_path:
            self.repo_editor_status_label.config(text="Please select a repository, branch, and file.", style='Error.TLabel')
            return

        self.repo_editor_loading_label.pack()
        self.repo_editor_status_label.config(text="Fetching file content...", style='Loading.TLabel')
        self.fetch_repo_file_button.config(state=tk.DISABLED)
        self.save_repo_file_button.config(state=tk.DISABLED)
        self.repo_content_container.pack_forget()
        self.repo_file_content_text.delete(1.0, tk.END)
        self.repo_save_status_label.config(text="")

        future = self.executor.submit(self._fetch_repo_file_content_threaded,
                                      self.current_repo_owner,
                                      self.current_repo_name,
                                      self.current_repo_file_path,
                                      self.current_repo_branch)
        future.add_done_callback(self._update_fetch_repo_file_content_status)

    def _fetch_repo_file_content_threaded(self, owner, repo_name, file_path, branch):
        """Fetches the content and SHA of a file from a GitHub repository (runs in a separate thread)."""
        headers = {'Authorization': f'token {self.github_token}', 'Accept': 'application/vnd.github.v3.raw'}
        content_url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}?ref={branch}'
        try:
            response = requests.get(content_url, headers=headers, timeout=10)
            response.raise_for_status()
            # For raw content, the response.text is the content itself
            content = response.text

            # To get the SHA, we need to make another request or parse the original content API response
            # Let's get the SHA from the full content API response (not raw)
            headers_sha = {'Authorization': f'token {self.github_token}'}
            sha_url = f'https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}?ref={branch}'
            sha_response = requests.get(sha_url, headers=headers_sha, timeout=10)
            sha_response.raise_for_status()
            sha_data = sha_response.json()
            file_sha = sha_data.get('sha')

            if file_sha:
                return {"success": True, "content": content, "sha": file_sha}
            else:
                return {"success": False, "message": "File SHA not found in response."}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"Error fetching file content or SHA: {e}"}

    def _update_fetch_repo_file_content_status(self, future):
        """Updates GUI after fetching repository file content (runs in main thread)."""
        result = future.result()
        self.repo_editor_loading_label.pack_forget()
        self.fetch_repo_file_button.config(state=tk.NORMAL)

        if result["success"]:
            self.repo_editor_status_label.config(text="✅ File content loaded.", style='Success.TLabel')
            self.repo_file_content_text.delete(1.0, tk.END)
            self.repo_file_content_text.insert(1.0, result["content"])
            self.current_repo_file_sha = result["sha"] # Store SHA for updates
            self.repo_content_container.pack(fill="both", expand=True)
            self.save_repo_file_button.config(state=tk.NORMAL)
            self.repo_save_status_label.config(text="Content loaded. You can now edit and save.", style='Info.TLabel')
        else:
            self.repo_editor_status_label.config(text=f"❌ Error loading file content: {result['message']}", style='Error.TLabel')
            self.repo_content_container.pack_forget()
            self.save_repo_file_button.config(state=tk.DISABLED)

    def start_save_repo_json_file(self):
        """Starts saving repository JSON file changes in a separate thread."""
        if not self.current_repo_owner or not self.current_repo_name or not self.current_repo_file_path or not self.current_repo_branch or not self.current_repo_file_sha:
            self.repo_save_status_label.config(text="Missing repository, branch, file, or SHA information.", style='Error.TLabel')
            return

        new_content = self.repo_file_content_text.get(1.0, tk.END).strip()
        if not new_content:
            self.repo_save_status_label.config(text="File content cannot be empty.", style='Error.TLabel')
            return

        commit_message = self.repo_commit_message_entry.get().strip()
        if not commit_message:
            self.repo_save_status_label.config(text="Commit message cannot be empty.", style='Error.TLabel')
            return

        # Encode content to base64 as required by GitHub API
        encoded_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')

        self.repo_editor_loading_label.pack()
        self.repo_save_status_label.config(text="Saving repository file changes...", style='Loading.TLabel')
        self.save_repo_file_button.config(state=tk.DISABLED)

        future = self.executor.submit(self._save_repo_file_threaded,
                                      encoded_content,
                                      commit_message)
        future.add_done_callback(self._update_save_repo_file_status)

    def _save_repo_file_threaded(self, encoded_content, commit_message):
        """Saves changes to a file in a GitHub repository (runs in a separate thread)."""
        headers = {'Authorization': f'token {self.github_token}', 'Content-Type': 'application/json'}
        update_url = f'https://api.github.com/repos/{self.current_repo_owner}/{self.current_repo_name}/contents/{self.current_repo_file_path}'
        payload = {
            "message": commit_message,
            "content": encoded_content,
            "sha": self.current_repo_file_sha,
            "branch": self.current_repo_branch
        }
        try:
            response = requests.put(update_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            # GitHub returns the updated file info, including new SHA
            updated_data = response.json()
            new_sha = updated_data['content']['sha']
            return {"success": True, "message": "Repository file updated successfully.", "new_sha": new_sha}
        except requests.exceptions.RequestException as e:
            error_message = f"Error saving repository file: {e}"
            try:
                error_response = response.json()
                if "message" in error_response:
                    error_message += f" - API Message: {error_response['message']}"
                if "errors" in error_response:
                    for err in error_response["errors"]:
                        error_message += f"\n  {err.get('field', 'N/A')}: {err.get('code', 'N/A')}"
            except json.JSONDecodeError:
                pass # Not a JSON error response
            return {"success": False, "message": error_message}

    def _update_save_repo_file_status(self, future):
        """Updates GUI after repository file save attempt (runs in main thread)."""
        result = future.result()
        self.repo_editor_loading_label.pack_forget()
        self.save_repo_file_button.config(state=tk.NORMAL)

        if result["success"]:
            self.repo_save_status_label.config(text=f"✅ {result['message']}", style='Success.TLabel')
            self.current_repo_file_sha = result["new_sha"] # Update SHA for subsequent saves
        else:
            self.repo_save_status_label.config(text=f"❌ {result['message']}", style='Error.TLabel')

    # --- Bot Editor Logic ---
    def start_load_bot_config_local(self):
        """Starts loading bot config from a local JSON file in a separate thread."""
        file_path = self.bot_config_local_file_path_var.get().strip()
        if not file_path:
            self.bot_config_status_label.config(text="Please enter a file path for the bot config.", style='Error.TLabel')
            return

        self.bot_editor_loading_label.pack()
        self.bot_config_status_label.config(text="Loading bot config...", style='Loading.TLabel')
        self.load_bot_config_button.config(state=tk.DISABLED)
        self.save_bot_config_button.config(state=tk.DISABLED)

        future = self.executor.submit(self._load_bot_config_local_threaded, file_path)
        future.add_done_callback(self._update_load_bot_config_status)

    def _load_bot_config_local_threaded(self, file_path):
        """Loads bot config from a local JSON file (runs in a separate thread)."""
        try:
            if not os.path.exists(file_path):
                return {"success": False, "message": f"File not found: {file_path}. Please ensure the file exists."}

            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            return {"success": True, "config": config_data}
        except json.JSONDecodeError as e:
            return {"success": False, "message": f"Error decoding JSON from {file_path}: {e}. Please check file format."}
        except Exception as e:
            return {"success": False, "message": f"Error loading bot config from {file_path}: {e}"}

    def _update_load_bot_config_status(self, future):
        """Updates GUI after bot config load attempt (runs in main thread)."""
        result = future.result()
        self.bot_editor_loading_label.pack_forget()
        self.load_bot_config_button.config(state=tk.NORMAL)
        self.save_bot_config_button.config(state=tk.NORMAL)

        if result["success"]:
            self.bot_config_status_label.config(text=f"✅ Bot config loaded from {self.bot_config_local_file_path_var.get()}.", style='Success.TLabel')
            self.current_bot_config_data = result["config"]
            self._update_bot_config_gui()
        else:
            self.bot_config_status_label.config(text=f"❌ {result['message']}", style='Error.TLabel')
            self.current_bot_config_data = {} # Clear data if load fails
            self._update_bot_config_gui() # Clear GUI fields

    def _update_bot_config_gui(self):
        """Populates the GUI fields with the current bot configuration data."""
        config = self.current_bot_config_data

        # Basic Presence
        self.bot_pfp_url_var.set(config.get("pfp_url", ""))
        self.bot_status_var.set(config.get("status", "online"))
        self.bot_activity_type_var.set(config.get("activity_type", "playing"))
        self.bot_activity_name_var.set(config.get("activity_name", ""))

        # Rich Presence
        rp_config = config.get("rich_presence", {})
        self.bot_rp_details_var.set(rp_config.get("details", ""))
        self.bot_rp_state_var.set(rp_config.get("state", ""))
        self.bot_rp_large_image_url_var.set(rp_config.get("large_image_url", ""))
        self.bot_rp_large_image_text_var.set(rp_config.get("large_image_text", ""))
        self.bot_rp_small_image_url_var.set(rp_config.get("small_image_url", ""))
        self.bot_rp_small_image_text_var.set(rp_config.get("small_image_text", ""))
        self.bot_rp_start_timestamp_var.set(str(rp_config.get("start_timestamp", "")) if rp_config.get("start_timestamp") is not None else "")
        self.bot_rp_end_timestamp_var.set(str(rp_config.get("end_timestamp", "")) if rp_config.get("end_timestamp") is not None else "")

        # General Settings
        self.bot_command_prefix_var.set(config.get("command_prefix", "/"))
        self.bot_log_channel_id_var.set(str(config.get("log_channel_id", "")) if config.get("log_channel_id") is not None else "")

        # Welcome Message
        self.bot_welcome_enabled_var.set(config.get("welcome_message", {}).get("enabled", False))
        self.bot_welcome_channel_id_var.set(str(config.get("welcome_message", {}).get("channel_id", "")) if config.get("welcome_message", {}).get("channel_id") is not None else "")
        self.welcome_message_text.delete(1.0, tk.END)
        self.welcome_message_text.insert(1.0, config.get("welcome_message", {}).get("content", ""))

        # Rate Limits
        self.bot_max_embeds_var.set(str(config.get("rate_limit", {}).get("max_embeds_per_period", "4")))
        self.bot_period_seconds_var.set(str(config.get("rate_limit", {}).get("period_seconds", "35")))


    def _get_bot_config_from_gui(self):
        """Extracts bot configuration data from the GUI fields."""
        config_to_save = {}

        # Basic Presence
        config_to_save["pfp_url"] = self.bot_pfp_url_var.get().strip() or None
        config_to_save["status"] = self.bot_status_var.get().strip() or "online"
        config_to_save["activity_type"] = self.bot_activity_type_var.get().strip() or "playing"
        config_to_save["activity_name"] = self.bot_activity_name_var.get().strip() or "with Blueprints"

        # Rich Presence
        rp_details = self.bot_rp_details_var.get().strip()
        rp_state = self.bot_rp_state_var.get().strip()
        rp_large_image_url = self.bot_rp_large_image_url_var.get().strip()
        rp_large_image_text = self.bot_rp_large_image_text_var.get().strip()
        rp_small_image_url = self.bot_rp_small_image_url_var.get().strip()
        rp_small_image_text = self.bot_rp_small_image_text_var.get().strip()

        rp_start_timestamp_str = self.bot_rp_start_timestamp_var.get().strip()
        rp_end_timestamp_str = self.bot_rp_end_timestamp_var.get().strip()

        rp_start_timestamp = None
        if rp_start_timestamp_str:
            try:
                rp_start_timestamp = int(rp_start_timestamp_str)
            except ValueError:
                messagebox.showwarning("Input Error", "Start Timestamp must be a valid integer (Unix timestamp).")
                return None

        rp_end_timestamp = None
        if rp_end_timestamp_str:
            try:
                rp_end_timestamp = int(rp_end_timestamp_str)
            except ValueError:
                messagebox.showwarning("Input Error", "End Timestamp must be a valid integer (Unix timestamp).")
                return None

        config_to_save["rich_presence"] = {
            "details": rp_details or None,
            "state": rp_state or None,
            "large_image_url": rp_large_image_url or None,
            "large_image_text": rp_large_image_text or None,
            "small_image_url": rp_small_image_url or None,
            "small_image_text": rp_small_image_text or None,
            "start_timestamp": rp_start_timestamp,
            "end_timestamp": rp_end_timestamp
        }

        # General Settings
        config_to_save["command_prefix"] = self.bot_command_prefix_var.get().strip() or "/"
        log_channel_id_str = self.bot_log_channel_id_var.get().strip()
        if log_channel_id_str:
            try:
                config_to_save["log_channel_id"] = int(log_channel_id_str)
            except ValueError:
                messagebox.showwarning("Input Error", "Log Channel ID must be a valid integer.")
                return None
        else:
            config_to_save["log_channel_id"] = None

        # Welcome Message
        welcome_enabled = self.bot_welcome_enabled_var.get()
        welcome_channel_id_str = self.bot_welcome_channel_id_var.get().strip()
        welcome_content = self.welcome_message_text.get(1.0, tk.END).strip()

        welcome_channel_id = None
        if welcome_channel_id_str:
            try:
                welcome_channel_id = int(welcome_channel_id_str)
            except ValueError:
                messagebox.showwarning("Input Error", "Welcome Channel ID must be a valid integer.")
                return None

        config_to_save["welcome_message"] = {
            "enabled": welcome_enabled,
            "channel_id": welcome_channel_id,
            "content": welcome_content or ""
        }

        # Rate Limits
        max_embeds_str = self.bot_max_embeds_var.get().strip()
        period_seconds_str = self.bot_period_seconds_var.get().strip()

        max_embeds = 4
        if max_embeds_str:
            try:
                max_embeds = int(max_embeds_str)
            except ValueError:
                messagebox.showwarning("Input Error", "Max Embeds per Period must be a valid integer.")
                return None

        period_seconds = 35
        if period_seconds_str:
            try:
                period_seconds = int(period_seconds_str)
            except ValueError:
                messagebox.showwarning("Input Error", "Period Seconds must be a valid integer.")
                return None

        config_to_save["rate_limit"] = {
            "max_embeds_per_period": max_embeds,
            "period_seconds": period_seconds
        }

        return config_to_save

    def _set_timestamp(self, var_to_set):
        """Sets the given StringVar to the current Unix timestamp."""
        current_unix_timestamp = int(time.time())
        var_to_set.set(str(current_unix_timestamp))


    def start_save_bot_config_local(self):
        """Starts saving bot config to a local JSON file in a separate thread."""
        file_path = self.bot_config_local_file_path_var.get().strip()
        if not file_path:
            self.bot_config_status_label.config(text="Please enter a file path to save the bot config.", style='Error.TLabel')
            return

        config_to_save = self._get_bot_config_from_gui()
        if config_to_save is None: # Validation failed in _get_bot_config_from_gui
            return

        self.bot_editor_loading_label.pack()
        self.bot_config_status_label.config(text="Saving bot config...", style='Loading.TLabel')
        self.load_bot_config_button.config(state=tk.DISABLED)
        self.save_bot_config_button.config(state=tk.DISABLED)

        future = self.executor.submit(self._save_bot_config_local_threaded, file_path, config_to_save)
        future.add_done_callback(self._update_save_bot_config_status)

    def _save_bot_config_local_threaded(self, file_path, config_data):
        """Saves bot config to a local JSON file (runs in a separate thread)."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            return {"success": True, "message": f"Bot config saved to {file_path}. Bot may need to be restarted to apply changes."}
        except Exception as e:
            return {"success": False, "message": f"Error saving bot config to {file_path}: {e}"}

    def _update_save_bot_config_status(self, future):
        """Updates GUI after bot config save attempt (runs in main thread)."""
        result = future.result()
        self.bot_editor_loading_label.pack_forget()
        self.load_bot_config_button.config(state=tk.NORMAL)
        self.save_bot_config_button.config(state=tk.NORMAL)

        if result["success"]:
            self.bot_config_status_label.config(text=f"✅ {result['message']}", style='Success.TLabel')
        else:
            self.bot_config_status_label.config(text=f"❌ {result['message']}", style='Error.TLabel')


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

