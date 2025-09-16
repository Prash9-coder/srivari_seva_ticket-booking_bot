import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import json
import os
import re
import difflib
import random
from collections import deque

try:
    import pyttsx3
except Exception:
    pyttsx3 = None

class TTDBookingBot:
    def __init__(self, root):
        self.root = root
        # Log buffer for API consumption (headless or GUI)
        self._log_buffer = deque(maxlen=1000)
        self._seq = 0
        self.driver = None
        self.is_running = False
        self.is_browser_open = False
        # UI timing tunables for faster dropdown interactions
        self.ui_open_delay = 0.15           # delay after opening a dropdown
        self.ui_post_select_delay = 0.12    # delay after selecting an option
        self.ui_key_delay = 0.06            # delay between key actions for dropdowns
        self.booking_data = self.load_booking_data()
        self.current_member_index = 0
        # Behavior flags (can be overridden by API/general config)
        self.respect_existing = True  # when True, do not overwrite non-empty fields
        self.aadhaar_autofill_wait_seconds = 6  # wait for site autofill after ID number
        if self.root is not None:
            # Only initialize Tk UI when a root is provided
            self.root.title("TTD Virtual Seva Booking Bot")
            self.root.geometry("900x700")
            self.root.resizable(True, True)
            self.setup_gui()
            try:
                self.root.after(300, self.open_browser)
            except Exception:
                pass

    def setup_gui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        title_label = ttk.Label(main_frame, text="TTD Virtual Seva Booking Bot",
                                font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)

        browser_frame = ttk.Frame(main_frame)
        browser_frame.grid(row=1, column=0, columnspan=2, pady=5)

        self.open_browser_button = ttk.Button(browser_frame, text="Open Browser",
                                              command=self.open_browser)
        self.open_browser_button.grid(row=0, column=0, padx=5)

        self.activate_button = ttk.Button(browser_frame, text="Activate Auto-Fill",
                                          command=self.toggle_bot, state=tk.DISABLED)
        self.activate_button.grid(row=0, column=1, padx=5)

        self.status_label = ttk.Label(main_frame, text="Status: Browser not open",
                                      foreground="red")
        self.status_label.grid(row=2, column=0, columnspan=2, pady=5)

        voice_frame = ttk.Frame(main_frame)
        voice_frame.grid(row=2, column=1, sticky=tk.E)
        self.voice_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(voice_frame, text="Voice", variable=self.voice_enabled).grid(row=0, column=0, padx=5)
        self.manual_dropdown = tk.BooleanVar(value=False)
        ttk.Checkbutton(voice_frame, text="Manual dropdown", variable=self.manual_dropdown).grid(row=0, column=1, padx=5)

        log_label = ttk.Label(main_frame, text="Activity Log:")
        log_label.grid(row=3, column=0, sticky=tk.W, pady=(10, 0))

        self.log_area = scrolledtext.ScrolledText(main_frame, width=80, height=15)
        self.log_area.grid(row=4, column=0, columnspan=2, pady=5, sticky=(tk.W, tk.E, tk.N, tk.S))

        config_label = ttk.Label(main_frame, text="Booking Configuration:",
                                 font=("Arial", 12, "bold"))
        config_label.grid(row=5, column=0, sticky=tk.W, pady=(20, 10))

        srivari_frame = ttk.LabelFrame(main_frame, text="Srivari Seva Group Settings")
        srivari_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        ttk.Label(srivari_frame, text="Group Size*").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.srivari_group_size_var = tk.StringVar()
        self.srivari_group_size_entry = ttk.Entry(srivari_frame, width=10, textvariable=self.srivari_group_size_var)
        self.srivari_group_size_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Label(srivari_frame, text="Download Folder").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.srivari_download_var = tk.StringVar()
        self.srivari_download_entry = ttk.Entry(srivari_frame, width=40, textvariable=self.srivari_download_var)
        self.srivari_download_entry.grid(row=0, column=3, padx=5, pady=2)
        btn_browse_dl = ttk.Button(srivari_frame, text="Browse", command=self._browse_download_dir)
        btn_browse_dl.grid(row=0, column=4, padx=5, pady=2)
        self.srivari_auto_date = tk.BooleanVar(value=True)
        self.srivari_auto_download = tk.BooleanVar(value=True)
        ttk.Checkbutton(srivari_frame, text="Auto select date", variable=self.srivari_auto_date).grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Checkbutton(srivari_frame, text="Auto download ticket", variable=self.srivari_auto_download).grid(row=1, column=1, sticky=tk.W, padx=5)

        try:
            cfg_path = self.get_config_path()
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    _sg = json.load(f) or {}
                _g = _sg.get("general") or {}
                if _g.get("group_size") is not None:
                    self.srivari_group_size_var.set(str(_g.get("group_size")))
                if _g.get("download_dir"):
                    self.srivari_download_var.set(_g.get("download_dir"))
                if _g.get("auto_select_date") is not None:
                    self.srivari_auto_date.set(bool(_g.get("auto_select_date")))
                if _g.get("auto_download_ticket") is not None:
                    self.srivari_auto_download.set(bool(_g.get("auto_download_ticket")))
        except Exception:
            pass

        members_label = ttk.Label(main_frame, text="Srivari Members (up to 10):", font=("Arial", 10, "bold"))
        members_label.grid(row=11, column=0, sticky=tk.W, pady=(10, 5))
        
        srivari_members_frame = ttk.LabelFrame(main_frame, text="Members")
        srivari_members_frame.grid(row=12, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        members_canvas = tk.Canvas(srivari_members_frame, height=300)
        v_scrollbar = ttk.Scrollbar(srivari_members_frame, orient="vertical", command=members_canvas.yview)
        h_scrollbar = ttk.Scrollbar(srivari_members_frame, orient="horizontal", command=members_canvas.xview)
        members_container = ttk.Frame(members_canvas)
        # Update scrollregion whenever the inner frame resizes
        members_container.bind("<Configure>", lambda e: members_canvas.configure(scrollregion=members_canvas.bbox("all")))
        members_canvas.create_window((0, 0), window=members_container, anchor="nw")
        members_canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        members_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        srivari_members_frame.columnconfigure(0, weight=1)
        srivari_members_frame.rowconfigure(0, weight=1)
        
        headers = [
            "#", "Name*", "DOB*", "Age*", "Blood Group*", "Gender*",
            "ID Type*", "ID Number*", "Mobile*", "Email*", "State", "District", "City",
            "Street", "Door No", "Pincode", "Photo*", "Nearest TTD Temple", " "
        ]
        for col, h in enumerate(headers):
            ttk.Label(members_container, text=h).grid(row=0, column=col, padx=5, pady=2, sticky=tk.W)

        self.srivari_member_widgets = []
        for i in range(10):
            row = i + 1
            ttk.Label(members_container, text=str(i + 1)).grid(row=row, column=0, padx=5, pady=2, sticky=tk.W)
            name_e = ttk.Entry(members_container, width=18); name_e.grid(row=row, column=1, padx=5, pady=2)
            dob_e = ttk.Entry(members_container, width=10); dob_e.grid(row=row, column=2, padx=5, pady=2)
            age_e = ttk.Entry(members_container, width=5); age_e.grid(row=row, column=3, padx=5, pady=2)
            bgrp_cb = ttk.Combobox(members_container, width=10, state="readonly")
            bgrp_cb['values'] = ("O+","O-","A+","A-","B+","B-","AB+","AB-")
            bgrp_cb.grid(row=row, column=4, padx=5, pady=2)
            gender_cb = ttk.Combobox(members_container, width=8, state="readonly")
            gender_cb['values'] = ('Male', 'Female', 'Other')
            gender_cb.set('Male')
            gender_cb.grid(row=row, column=5, padx=5, pady=2)
            idtype_cb = ttk.Combobox(members_container, width=12, state="readonly")
            idtype_cb['values'] = ('Aadhaar', 'PAN', 'Driving License', 'Voter ID', 'Passport')
            idtype_cb.set('Aadhaar')
            idtype_cb.grid(row=row, column=6, padx=5, pady=2)
            idnum_e = ttk.Entry(members_container, width=16); idnum_e.grid(row=row, column=7, padx=5, pady=2)
            mobile_e = ttk.Entry(members_container, width=14); mobile_e.grid(row=row, column=8, padx=5, pady=2)
            email_e = ttk.Entry(members_container, width=20); email_e.grid(row=row, column=9, padx=5, pady=2)
            state_e = ttk.Entry(members_container, width=18); state_e.grid(row=row, column=10, padx=5, pady=2)
            district_e = ttk.Entry(members_container, width=18); district_e.grid(row=row, column=11, padx=5, pady=2)
            city_e = ttk.Entry(members_container, width=18); city_e.grid(row=row, column=12, padx=5, pady=2)
            street_e = ttk.Entry(members_container, width=18); street_e.grid(row=row, column=13, padx=5, pady=2)
            doorno_e = ttk.Entry(members_container, width=12); doorno_e.grid(row=row, column=14, padx=5, pady=2)
            pincode_e = ttk.Entry(members_container, width=10); pincode_e.grid(row=row, column=15, padx=5, pady=2)
            photo_e = ttk.Entry(members_container, width=24); photo_e.grid(row=row, column=16, padx=5, pady=2)
            ttk.Button(members_container, text="Browse", command=lambda idx=i: self._browse_member_photo(idx)).grid(row=row, column=17, padx=5, pady=2)
            self.srivari_member_widgets.append({
                "name": name_e, "dob": dob_e, "age": age_e, "blood_group": bgrp_cb,
                "gender": gender_cb, "id_proof_type": idtype_cb, "id_number": idnum_e,
                "mobile": mobile_e, "email": email_e, "state": state_e, "district": district_e,
                "city": city_e, "street": street_e, "doorno": doorno_e, "pincode": pincode_e, "photo": photo_e,
            })
            
        members_btn_frame = ttk.Frame(main_frame)
        members_btn_frame.grid(row=13, column=1, sticky=tk.E, pady=(5, 0))
        ttk.Button(members_btn_frame, text="Reload Members", command=self._load_srivari_members_to_gui).grid(row=0, column=0, padx=5)
        ttk.Button(members_btn_frame, text="Save Members", command=self._save_srivari_members).grid(row=0, column=1, padx=5)
        
        self._load_srivari_members_to_gui()
        self._start_members_file_watch()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(12, weight=1)

    def _browse_download_dir(self):
        try:
            d = filedialog.askdirectory()
            if d:
                self.srivari_download_var.set(d)
        except Exception:
            pass

    def _browse_member_photo(self, idx):
        try:
            p = filedialog.askopenfilename(title="Select Photo", filetypes=(("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp"), ("All Files", "*.*")))
            if p:
                self.srivari_member_widgets[idx]["photo"].delete(0, tk.END)
                self.srivari_member_widgets[idx]["photo"].insert(0, p)
        except Exception:
            pass

    def get_config_path(self):
        try:
            p = os.environ.get("TTD_CONFIG_PATH")
            return p if p else "srivari_group_data.json"
        except Exception:
            return "srivari_group_data.json"

    def get_config_dir(self):
        try:
            p = self.get_config_path()
            return os.path.dirname(os.path.abspath(p))
        except Exception:
            return os.getcwd()

    def _load_srivari_members_to_gui(self):
        try:
            cfg_path = self.get_config_path()
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Accept both top-level array and {"members": [...]} formats
                if isinstance(data, list):
                    members = data
                elif isinstance(data, dict):
                    members = data.get("members") or data.get("data") or []
                else:
                    members = []

                def lc_map(d):
                    try:
                        return {str(k).lower(): v for k, v in (d or {}).items()}
                    except Exception:
                        return {}

                allowed_blood = ("O+","O-","A+","A-","B+","B-","AB+","AB-")
                allowed_gender = ("Male", "Female", "Other")
                allowed_id_types = ("Aadhaar", "PAN", "Driving License", "Voter ID", "Passport")

                for i in range(10):
                    m = lc_map(members[i]) if i < len(members) else {}
                    w = self.srivari_member_widgets[i]

                    # Name
                    w["name"].delete(0, tk.END); w["name"].insert(0, m.get("name", ""))

                    # DOB & Age
                    w["dob"].delete(0, tk.END); w["dob"].insert(0, m.get("dob", ""))
                    w["age"].delete(0, tk.END); w["age"].insert(0, str(m.get("age", "")).strip())

                    # Blood group (validate against allowed list)
                    b = m.get("blood_group", m.get("blood group", ""))
                    b_norm = None
                    if b:
                        for opt in allowed_blood:
                            if opt.lower() == str(b).strip().lower():
                                b_norm = opt; break
                    w["blood_group"].set(b_norm or "")

                    # Gender (normalize)
                    g = m.get("gender", "Male")
                    g_norm = None
                    for opt in allowed_gender:
                        if opt.lower() == str(g).strip().lower():
                            g_norm = opt; break
                    w["gender"].set(g_norm or "Male")

                    # ID proof type (normalize)
                    idt = m.get("id_proof_type", m.get("id_proof", m.get("idtype", "Aadhaar")))
                    idt_norm = None
                    for opt in allowed_id_types:
                        if opt.lower() == str(idt).strip().lower():
                            idt_norm = opt; break
                    w["id_proof_type"].set(idt_norm or "Aadhaar")

                    # ID number (map AADHAR/AADHAAR formats with/without dashes)
                    idnum = m.get("id_number", m.get("aadhaar", m.get("aadhar", m.get("aadhar_no", m.get("id_no", "")))))
                    idnum_str = str(idnum or "").replace("-", "").replace(" ", "").strip()
                    w["id_number"].delete(0, tk.END); w["id_number"].insert(0, idnum_str)

                    # Contact
                    w["mobile"].delete(0, tk.END); w["mobile"].insert(0, str(m.get("mobile", "")).strip())
                    w["email"].delete(0, tk.END); w["email"].insert(0, str(m.get("email", m.get("mail_id", ""))).strip())

                    # Address
                    w["state"].delete(0, tk.END); w["state"].insert(0, m.get("state", ""))
                    w["district"].delete(0, tk.END); w["district"].insert(0, m.get("district", ""))
                    w["city"].delete(0, tk.END); w["city"].insert(0, m.get("city", ""))
                    w["street"].delete(0, tk.END); w["street"].insert(0, m.get("street", ""))
                    w["doorno"].delete(0, tk.END); w["doorno"].insert(0, m.get("doorno", m.get("door_no", "")))
                    w["pincode"].delete(0, tk.END); w["pincode"].insert(0, m.get("pincode", m.get("pin_code", "")))

                    # Photo path (resolve relative names to images folder if needed)
                    photo_val = str(m.get("photo", m.get("photo_path", m.get("image", "")))).strip()
                    # If just a filename like 1.jpg, resolve relative to config dir first, then images/
                    if photo_val and not os.path.isabs(photo_val) and os.path.sep not in photo_val:
                        cfg_dir = self.get_config_dir()
                        candidate_cfg = os.path.join(cfg_dir, photo_val)
                        if os.path.exists(candidate_cfg):
                            photo_val = candidate_cfg
                        else:
                            img_dir = os.environ.get("TTD_IMAGE_DIR")
                            if img_dir:
                                candidate_env = os.path.join(img_dir, photo_val)
                                if os.path.exists(candidate_env):
                                    photo_val = candidate_env
                            else:
                                candidate = os.path.join("images", photo_val)
                                if os.path.exists(candidate):
                                    photo_val = candidate
                    w["photo"].delete(0, tk.END); w["photo"].insert(0, photo_val)
        except Exception as ex:
            self.log_message(f"Failed to load members: {ex}")

    def _save_srivari_members(self, show_message=True):
        try:
            members = []
            for i in range(10):
                w = self.srivari_member_widgets[i]
                name = w["name"].get().strip()
                if not name:
                    continue
                members.append({
                    "name": name,
                    "dob": w["dob"].get().strip(),
                    "age": w["age"].get().strip(),
                    "blood_group": w["blood_group"].get().strip(),
                    "gender": w["gender"].get().strip(),
                    "id_proof_type": w["id_proof_type"].get().strip(),
                    "id_number": w["id_number"].get().strip(),
                    "mobile": w["mobile"].get().strip(),
                    "email": w["email"].get().strip(),
                    "state": w["state"].get().strip(),
                    "district": w["district"].get().strip(),
                    "city": w["city"].get().strip(),
                    "street": w["street"].get().strip(),
                    "doorno": w["doorno"].get().strip(),
                    "pincode": w["pincode"].get().strip(),
                    "photo": w["photo"].get().strip(),
                })
            # Preserve file format: if file was a list, write a list; if dict with 'members', keep that
            payload = members
            cfg_path = self.get_config_path()
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                    if isinstance(existing, dict):
                        existing["members"] = members
                        payload = existing
                except Exception:
                    pass
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.log_message("Members saved.")
            if show_message:
                try:
                    messagebox.showinfo("Success", "Srivari members saved.")
                except Exception:
                    pass
        except Exception as ex:
            self.log_message(f"Failed to save members: {ex}")
            if show_message:
                try:
                    messagebox.showerror("Error", f"Failed to save members: {ex}")
                except Exception:
                    pass

    def log_message(self, message):
        # Append to buffer for API access, redacting sensitive numbers
        try:
            msg = str(message)
            # redact 12+ digit runs and email-like tokens
            import re
            msg = re.sub(r"\b(\d{4}[ -]?){3,}\d+\b", "[REDACTED]", msg)
            msg = re.sub(r"[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}", "[REDACTED]", msg)
            self._seq += 1
            self._log_buffer.append({
                "seq": self._seq,
                "ts": time.strftime('%H:%M:%S'),
                "msg": msg,
            })
        except Exception:
            pass
        # Thread-safe UI logging via Tk event loop (when GUI available)
        ts_msg = f"{time.strftime('%H:%M:%S')} - {message}\n"
        try:
            if self.root is not None:
                self.root.after(0, lambda: (self.log_area.insert(tk.END, ts_msg), self.log_area.see(tk.END)))
        except Exception:
            # Fallback if root is closing
            try:
                self.log_area.insert(tk.END, ts_msg)
                self.log_area.see(tk.END)
            except Exception:
                pass
        # Avoid speaking very long messages to reduce lag
        try:
            if getattr(self, 'voice_enabled', None) and self.root is not None and self.voice_enabled.get() and len(str(message)) <= 120:
                self._speak_async(message)
        except Exception:
            pass

    def _start_members_file_watch(self):
        # Simple polling watcher to auto-reload members when JSON changes
        try:
            self._members_file = self.get_config_path()
            self._members_mtime = os.path.getmtime(self._members_file) if os.path.exists(self._members_file) else 0
        except Exception:
            self._members_mtime = 0
        # Schedule periodic check
        try:
            self.root.after(1500, self._check_members_file_change)
        except Exception:
            pass

    def _check_members_file_change(self):
        try:
            path = getattr(self, "_members_file", self.get_config_path())
            if os.path.exists(path):
                mtime = os.path.getmtime(path)
                if mtime != getattr(self, "_members_mtime", 0):
                    self._members_mtime = mtime
                    self.log_message("Detected config change. Auto reloading members...")
                    self._load_srivari_members_to_gui()
        except Exception:
            pass
        finally:
            try:
                self.root.after(1500, self._check_members_file_change)
            except Exception:
                pass

    def _init_tts(self):
        if getattr(self, '_tts_engine', None) is None and pyttsx3 is not None:
            try:
                self._tts_engine = pyttsx3.init()
                try:
                    vol = self._tts_engine.getProperty('volume')
                    self._tts_engine.setProperty('volume', min(1.0, max(0.3, vol)))
                except Exception:
                    pass
            except Exception:
                self._tts_engine = None

    def _speak_async(self, text):
        if pyttsx3 is None:
            return
        self._init_tts()
        if getattr(self, '_tts_engine', None) is None:
            return
        def _worker(msg):
            try:
                self._tts_engine.say(msg)
                self._tts_engine.runAndWait()
            except Exception:
                pass
        try:
            threading.Thread(target=_worker, args=(text,), daemon=True).start()
        except Exception:
            pass

    def toggle_bot(self):
        if not self.is_running:
            self.start_bot()
        else:
            self.stop_bot()

    def open_browser(self):
        if self.is_browser_open and self.driver:
            self.log_message("Browser is already open.")
            return
        try:
            self.log_message("Opening browser...")
            options = Options()
            options.add_argument("--disable-notifications")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Cloud environment optimizations
            is_cloud = os.getenv("RENDER") or os.getenv("PORT") or os.getenv("DISPLAY")
            if is_cloud:
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-gpu")
                options.add_argument("--remote-debugging-port=9222")
                options.add_argument("--window-size=1920,1080")
                # Don't add --headless as we want visual interaction

            # Persistent Chrome profile for session reuse
            try:
                prof = os.environ.get("TTD_CHROME_PROFILE")
                if not prof:
                    # default to a local profile folder within repo
                    prof = os.path.abspath(os.path.join(os.getcwd(), "chrome_profile"))
                os.makedirs(prof, exist_ok=True)
                options.add_argument(f"--user-data-dir={prof}")
            except Exception:
                pass

            prefs = None
            try:
                cfg_path = self.get_config_path()
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        _sg = json.load(f)
                        _g = (_sg or {}).get("general") or {}
                        _dl = _g.get("download_dir")
                        if _dl and isinstance(_dl, str) and os.path.isdir(_dl):
                            prefs = {"download.default_directory": _dl, "download.prompt_for_download": False, "profile.default_content_setting_values.automatic_downloads": 1}
            except Exception:
                prefs = None
            if prefs:
                try:
                    options.add_experimental_option("prefs", prefs)
                except Exception:
                    pass
            # Use webdriver-manager to fetch a ChromeDriver matching the installed Chrome
            try:
                # Force specific version compatible with Chrome 140
                service = Service(ChromeDriverManager(version="140.0.7339.82").install())
                self.driver = webdriver.Chrome(service=service, options=options)
                self.log_message("WebDriver initialized with managed ChromeDriver v140")
            except Exception as e:
                self.log_message(f"WebDriver manager failed: {str(e)[:100]}")
                try:
                    # Try selenium-manager (Selenium 4.11+)
                    service = Service()
                    self.driver = webdriver.Chrome(service=service, options=options)
                    self.log_message("WebDriver initialized with selenium-manager")
                except Exception as e2:
                    self.log_message(f"Selenium-manager failed: {str(e2)[:100]}")
                    # Last resort fallback to default constructor
                    self.driver = webdriver.Chrome(options=options)
                    self.log_message("WebDriver initialized with default ChromeDriver (may fail)")
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception:
                pass
            self.log_message("Navigating to TTD booking page...")
            self.driver.get("https://ttdevasthanams.ap.gov.in")
            try:
                self.arrange_windows_side_by_side()
            except Exception:
                pass
            self.is_browser_open = True
            # Guard UI updates in headless mode
            try:
                self.activate_button.config(state=tk.NORMAL)
                self.open_browser_button.config(state=tk.DISABLED)
                self.status_label.config(text="Status: Browser open - Please login manually", foreground="orange")
            except Exception:
                pass
            self.log_message("Browser opened successfully. Please login manually and navigate to the Srivari Seva Team Leader page.")
        except WebDriverException as e:
            self.log_message(f"WebDriver error: {str(e)}")
            try:
                messagebox.showerror("Error", f"Failed to start Chrome driver. Is Chrome installed?\n{str(e)}")
            except Exception:
                pass
        except Exception as e:
            self.log_message(f"Error opening browser: {str(e)}")
            try:
                messagebox.showerror("Error", f"Unexpected error: {str(e)}")
            except Exception:
                pass

    def start_bot(self):
        self.is_running = True
        # Guard UI updates in headless mode
        try:
            self.activate_button.config(text="Deactivate Auto-Fill")
            self.status_label.config(text="Status: Auto-Fill Active", foreground="green")
        except Exception:
            pass
        self.log_message("Auto-fill activated. Filling details...")
        bot_thread = threading.Thread(target=self.run_bot, daemon=True)
        bot_thread.start()

    def stop_bot(self):
        self.is_running = False
        try:
            self.activate_button.config(text="Activate Auto-Fill")
            self.status_label.config(text="Status: Browser open - Auto-Fill Inactive", foreground="orange")
        except Exception:
            pass
        self.log_message("Auto-fill deactivated.")

    def load_booking_data(self):
        default_data = {
            "general": {
                "gothram": "Vasishta",
                "email": "example@email.com",
                "city": "Tirupati",
                "state": "Andhra Pradesh",
                "country": "India",
                "pincode": "517501"
            },
            "pilgrims": [
                {
                    "name": "Rama Kumar",
                    "age": "30",
                    "gender": "Male",
                    "id_proof": "Aadhaar",
                    "id_number": "123456789012"
                },
                {
                    "name": "Sita Devi",
                    "age": "28",
                    "gender": "Female",
                    "id_proof": "Aadhaar",
                    "id_number": "987654321098"
                }
            ]
        }
        try:
            if os.path.exists("booking_data.json"):
                with open("booking_data.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Failed to load booking data: {e}")
        return default_data

    def _normalize(self, text: str) -> str:
        if text is None:
            return ""
        return str(text).strip().lower()

    def _is_plausible_option_text(self, text: str) -> bool:
        # Filter out generic or unrelated texts often visible in the page
        if not text:
            return False
        t = text.strip()
        if len(t) <= 1:
            return False
        tl = t.lower()
        # Exclude obvious non-option fragments
        banned_contains = (
            "dob", "xxxxxx", "yrs", "years", "team leader", "sevak", "mobile", "email",
            "important note", "address details", "fitness", "profession", "qualification",
        )
        if any(b in tl for b in banned_contains):
            return False
        # Exclude masked numbers or pure numbers
        if t.isdigit():
            return False
        if "X" * 4 in t or "x" * 4 in tl:
            return False
        return True

    def _get_visible_dropdown_panels(self, trigger_el):
        # Try to find overlay/panel elements likely containing options, near the trigger
        panels = []
        xps = [
            "//*[@role='listbox' and not(@aria-hidden='true')]",
            "//*[@role='menu' and not(@aria-hidden='true')]",
            "//ul[contains(@class,'menu') or contains(@class,'list') or contains(@class,'options')]",
            "//div[contains(@class,'menu') or contains(@class,'listbox') or contains(@class,'options') or contains(@class,'dropdown') or contains(@class,'select')]",
        ]
        try:
            trig_rect = self.driver.execute_script("const r=arguments[0].getBoundingClientRect(); return {l:r.left,t:r.top,r:r.right,b:r.bottom};", trigger_el)
        except Exception:
            trig_rect = None
        for xp in xps:
            try:
                for el in self.driver.find_elements(By.XPATH, xp):
                    try:
                        if not el.is_displayed():
                            continue
                        if trig_rect:
                            rect = self.driver.execute_script("const r=arguments[0].getBoundingClientRect(); return {l:r.left,t:r.top,r:r.right,b:r.bottom};", el)
                            # Heuristic: panel should be visually below or overlapping the trigger vertically
                            if rect and rect.get('t', 0) + 1 < trig_rect.get('t', 0) - 2:
                                continue
                        panels.append(el)
                    except Exception:
                        continue
            except Exception:
                continue
        return panels

    def _find_visible_options_in_panels(self, panels):
        opts = []
        for p in panels:
            for xp in [".//li[normalize-space(.)]", ".//div[normalize-space(.)]", ".//span[normalize-space(.)]", ".//option[normalize-space(.)]"]:
                try:
                    for el in p.find_elements(By.XPATH, xp):
                        try:
                            if el.is_displayed():
                                txt = (el.text or '').strip()
                                if self._is_plausible_option_text(txt):
                                    opts.append((el, txt))
                        except Exception:
                            continue
                except Exception:
                    continue
        return opts

    def set_custom_dropdown_by_xpath(self, trigger_xpath, value):
        # Robust dropdown selector: handles native <select> and custom widgets
        if value in (None, "") or not trigger_xpath:
            return False
        try:
            el = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, trigger_xpath)))
            self._scroll_into_view(el)

            # If a selection already exists, leave it untouched
            try:
                placeholders = {"select", "choose", "--select--", "-- choose --"}
                tag = (el.tag_name or "").lower()
                current_txt = ""
                if tag == "select":
                    try:
                        sel = Select(el)
                        current_txt = (sel.first_selected_option.text or "").strip()
                    except Exception:
                        current_txt = ""
                else:
                    current_txt = (el.get_attribute("value") or "").strip()
                if current_txt and current_txt.strip().lower() not in placeholders:
                    self.log_message(f"Skip dropdown {trigger_xpath}: already selected '{current_txt}'")
                    return False
            except Exception:
                pass

            try:
                tag = (el.tag_name or "").lower()
            except Exception:
                tag = ""

            # Handle native <select>
            if tag == "select":
                try:
                    sel = Select(el)
                    # Try exact visible text first
                    try:
                        sel.select_by_visible_text(str(value))
                        self.log_message(f"Selected from <select>: {value}")
                        return True
                    except Exception:
                        pass
                    # Fallback: partial/ci match
                    target = self._normalize(str(value))
                    best = None
                    best_ratio = 0.0
                    for opt in sel.options:
                        txt = (opt.text or "").strip()
                        norm = self._normalize(txt)
                        if target in norm:
                            sel.select_by_visible_text(txt)
                            self.log_message(f"Selected from <select> (partial): {txt}")
                            return True
                        # fuzzy score for misspellings
                        ratio = difflib.SequenceMatcher(None, target, norm).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best = txt
                    if best and best_ratio >= 0.7:
                        sel.select_by_visible_text(best)
                        self.log_message(f"Selected from <select> (fuzzy {best_ratio:.2f}): {best}")
                        return True
                except Exception as e:
                    self.log_message(f"<select> selection failed: {e}")
                # If select path failed, continue to custom flow below

            # Custom dropdowns
            try:
                ActionChains(self.driver).move_to_element(el).pause(0).perform()
            except Exception:
                pass
            try:
                el.click()
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", el)
                except Exception:
                    pass
            time.sleep(self.ui_open_delay)

            normalized_val = self._normalize(value)
            # Prefer visible dropdown panels near the trigger to avoid scanning the whole DOM
            candidates = []
            panels = self._get_visible_dropdown_panels(el)
            option_pairs = self._find_visible_options_in_panels(panels) if panels else []
            if option_pairs:
                candidates = [el for (el, txt) in option_pairs]
            else:
                # Fallback to page-wide search (rare)
                for xp in ["//li[normalize-space(.)]", "//div[normalize-space(.)]", "//span[normalize-space(.)]", "//option[normalize-space(.)]"]:
                    try:
                        for c in self.driver.find_elements(By.XPATH, xp):
                            if c.is_displayed() and self._is_plausible_option_text((c.text or '').strip()):
                                candidates.append(c)
                    except Exception:
                        pass

            # Try exact/partial first
            for opt in candidates:
                try:
                    txt = (opt.text or "").strip()
                    norm = self._normalize(txt)
                    if normalized_val and (normalized_val == norm or normalized_val in norm):
                        opt.click(); time.sleep(self.ui_post_select_delay); self.log_message(f"Dropdown selected {txt}"); return True
                except Exception:
                    continue

            # Fuzzy match fallback (tightened threshold to reduce wrong picks and retries)
            best_el, best_txt, best_ratio = None, None, 0.0
            for opt in candidates:
                try:
                    txt = (opt.text or "").strip()
                    norm = self._normalize(txt)
                    ratio = difflib.SequenceMatcher(None, normalized_val, norm).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio; best_el = opt; best_txt = txt
                except Exception:
                    continue
            if best_el and best_ratio >= 0.8:
                try:
                    best_el.click(); time.sleep(self.ui_post_select_delay); self.log_message(f"Dropdown selected (fuzzy {best_ratio:.2f}): {best_txt}"); return True
                except Exception:
                    pass

            try:
                el.send_keys(Keys.ARROW_DOWN)
                time.sleep(self.ui_key_delay)
                el.send_keys(Keys.ENTER)
                time.sleep(self.ui_post_select_delay)
                return True
            except Exception:
                pass
            self.log_message(f"Dropdown select failed: {value}")
            return False
        except Exception as e:
            self.log_message(f"Dropdown exception {trigger_xpath}: {e}")
            return False

    def set_checkbox_by_label(self, container_xpath, label_text, desired=True):
        try:
            cont = WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.XPATH, container_xpath)))
            self._scroll_into_view(cont)
            label_norm = self._normalize(label_text)
            q = f".//*[contains(translate(normalize-space(.),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'), '{label_norm}')]"
            candidates = cont.find_elements(By.XPATH, q)
            for el in candidates:
                try:
                    cb = el.find_element(By.XPATH, "ancestor::*[@role='checkbox'][1]")
                    checked = (cb.get_attribute('aria-checked') or '').lower() =='true'
                    if desired != checked:
                        try: 
                            cb.click()
                        except Exception: 
                            self.driver.execute_script("arguments[0].click();", cb)
                    return True
                except Exception: 
                    pass
                try:
                    inp = el.find_element(By.XPATH, "ancestor::*[self::label or self::*][1]//input[@type='checkbox']")
                except Exception: 
                    inp = None
                if inp:
                    checked = inp.is_selected() or (inp.get_attribute('checked') == 'true') or bool(inp.get_attribute('checked'))
                    if desired != checked:
                        try: 
                            inp.click()
                        except Exception: 
                            self.driver.execute_script("arguments[0].click();", inp)
                    return True
                try: 
                    el.click(); 
                    return True
                except Exception:
                    try: 
                        self.driver.execute_script("arguments[0].click();", el); 
                        return True
                    except Exception: 
                        continue
            return False
        except Exception:
            return False

    def check_fitness_boxes(self, x, fitness_labels = ("mentally fit", "physically fit", "mentally and physically")):
        did_fit = False
        for label in fitness_labels:
            did_fit |= self.set_checkbox_by_label(x.get("fitness_container", ""), label, True)
        if not did_fit:
            for label in fitness_labels:
                did_fit |= self.set_checkbox_by_label("//*", label, True)
        return did_fit

    def click_xpath(self, xp):
        if not xp:
            return False
        el = None
        try:
            el = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.XPATH, xp)))
        except Exception:
            pass
        if el is None:
            # Try fallback by ID within the XPath
            try:
                m = re.search(r"@id=\"([^\"]+)\"", xp)
                if m:
                    el = WebDriverWait(self.driver, 8).until(EC.element_to_be_clickable((By.ID, m.group(1))))
            except Exception:
                el = None
        if el is None:
            self.log_message(f"Failed to resolve element for click: {xp}")
            return False
        try:
            self._scroll_into_view(el)
            try:
                el.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", el)
            time.sleep(self.ui_post_select_delay)
            return True
        except Exception as e:
            self.log_message(f"Failed to click: {xp} - {e}")
            return False

    def wait_for_blank_member_form(self, x, timeout=12):
        end = time.time() + timeout
        name_x = x.get("name_input")
        id_x = x.get("id_proof_number_input")
        while time.time() < end:
            try:
                name_el = self.driver.find_element(By.XPATH, name_x)
                id_el = self.driver.find_element(By.XPATH, id_x) if id_x else None
                name_val = (name_el.get_attribute("value") or "").strip()
                id_val = (id_el.get_attribute("value") or "").strip() if id_el else ""
                if not name_val and not id_val:
                    return True
            except Exception: 
                pass
            time.sleep(0.3)
        return False

    def clear_member_form(self, x):
        # Aggressively clear all known inputs so subsequent members can be filled reliably
        try:
            for key in [
                "name_input","id_proof_number_input","dob_input","age_input","mobile_input","email_input",
                "city_input","street_input","doorno_input","pincode_input"
            ]:
                self.clear_input_by_xpath(x.get(key))
        except Exception:
            pass
        # Close any open dropdown-like inputs
        try:
            ntt = x.get("nearest_ttd_temple_dropdown")
            if ntt:
                el = self.driver.find_element(By.XPATH, ntt)
                el.send_keys(Keys.ESCAPE)
        except Exception:
            pass

    def wait_for_continue_clickable(self, xpath, timeout=30):
        if not xpath:
            return False
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            return True
        except Exception as e:
            self.log_message(f"Continue not clickable for {xpath}: {e}")
            return False

    def clear_input_by_xpath(self, xpath):
        if not xpath:
            return False
        try:
            el = self.driver.find_element(By.XPATH, xpath)
            self._scroll_into_view(el)
            try: 
                el.clear()
            except Exception:
                self.driver.execute_script("arguments[0].value=''; arguments[0].dispatchEvent(new Event('input', {bubbles:true})); arguments[0].dispatchEvent(new Event('change', {bubbles:true}));", el)
            return True
        except Exception:
            return False

    def _scroll_into_view(self, el):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        except Exception:
            pass

    def get_input_value_by_xpath(self, xpath):
        if not xpath:
            return ""
        try:
            el = self.driver.find_element(By.XPATH, xpath)
            return (el.get_attribute("value") or "").strip()
        except Exception:
            return ""

    def _format_dob_for_site(self, value):
        # Convert various DOB inputs into DD/MM/YYYY as required by the site
        if not value:
            return value
        v = str(value).strip()
        try:
            # If already in dd/mm/yyyy
            if "/" in v:
                parts = v.split("/")
                if len(parts) == 3 and len(parts[0]) <= 2 and len(parts[1]) <= 2 and len(parts[2]) >= 4:
                    dd = parts[0].zfill(2)
                    mm = parts[1].zfill(2)
                    yyyy = parts[2][-4:]
                    return f"{dd}/{mm}/{yyyy}"
            # If yyyy-mm-dd
            if "-" in v:
                parts = v.split("-")
                if len(parts) == 3 and len(parts[0]) == 4:
                    yyyy, mm, dd = parts
                    return f"{dd.zfill(2)}/{mm.zfill(2)}/{yyyy}"
            # If digits only and 8 length, assume ddmmyyyy or yyyymmdd heuristics
            digits = ''.join(ch for ch in v if ch.isdigit())
            if len(digits) == 8:
                # Heuristic: if starts with 19/20 treat as yyyymmdd
                if digits.startswith("19") or digits.startswith("20"):
                    yyyy = digits[:4]; mm = digits[4:6]; dd = digits[6:]
                else:
                    dd = digits[:2]; mm = digits[2:4]; yyyy = digits[4:]
                return f"{dd}/{mm}/{yyyy}"
        except Exception:
            pass
        return v

    def set_text_if_empty_by_xpath(self, xpath, value, *, is_dob=False):
        if not xpath or value in (None, ""):
            return False
        try:
            current = self.get_input_value_by_xpath(xpath)
            if current and self.respect_existing:
                # Already filled (likely by Aadhaar autofill) – do not overwrite
                self.log_message(f"Skip set at {xpath}: already filled with '{current}'")
                return False
        except Exception:
            pass
        if is_dob:
            value = self._format_dob_for_site(value)
            return self._set_dob_masked_by_xpath(xpath, value)
        return self.set_text_by_xpath(xpath, value)

    def _set_dob_masked_by_xpath(self, xpath, dob_ddmmyyyy):
        # Type DOB using digits-only so input masks auto-insert slashes, then verify
        try:
            el = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, xpath)))
            self._scroll_into_view(el)
            try:
                el.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", el)
            time.sleep(self.ui_key_delay)
            # Hard clear: select all + delete + JS fallback
            try:
                el.send_keys(Keys.CONTROL, 'a'); time.sleep(self.ui_key_delay); el.send_keys(Keys.BACKSPACE)
            except Exception:
                pass
            try:
                self.driver.execute_script("arguments[0].value='';", el)
            except Exception:
                pass
            # Send digits only
            digits = ''.join(ch for ch in str(dob_ddmmyyyy) if ch.isdigit())
            if len(digits) != 8:
                # As a fallback, derive digits from formatted string
                f = self._format_dob_for_site(dob_ddmmyyyy)
                digits = ''.join(ch for ch in f if ch.isdigit())
            for ch in digits:
                el.send_keys(ch); time.sleep(self.ui_key_delay)
            # Blur to trigger validations
            el.send_keys(Keys.TAB); time.sleep(self.ui_post_select_delay)
            # Verify value
            final = (el.get_attribute('value') or '').strip()
            expected = self._format_dob_for_site(dob_ddmmyyyy)
            if final != expected:
                # Try setting via JS and dispatching events
                try:
                    self.driver.execute_script(
                        "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', {bubbles:true})); arguments[0].dispatchEvent(new Event('change', {bubbles:true}));",
                        el, expected
                    )
                    time.sleep(self.ui_post_select_delay)
                    final = (el.get_attribute('value') or '').strip()
                except Exception:
                    pass
            ok = final == expected
            self.log_message(f"DOB set to {final} (expected {expected}) -> {'OK' if ok else 'MISMATCH'}")
            return ok
        except Exception as e:
            self.log_message(f"DOB input failed {xpath}: {e}")
            return False

    def wait_for_aadhaar_autofill(self, x, timeout=12):
        # After entering Aadhaar, wait briefly to see if site auto-fills fields
        end = time.time() + timeout
        keys_to_check = [
            "name_input", "dob_input", "age_input", "mobile_input", "email_input",
            "city_input", "street_input", "doorno_input", "pincode_input"
        ]
        while time.time() < end:
            try:
                any_filled = False
                for k in keys_to_check:
                    xp = x.get(k)
                    if xp and self.get_input_value_by_xpath(xp):
                        any_filled = True; break
                if any_filled:
                    return True
            except Exception:
                pass
            time.sleep(0.3)
        return False

    def pick_random_from_dropdown(self, trigger_xpath):
        # Open dropdown and click a random option among visible candidates
        if not trigger_xpath:
            return False
        try:
            el = WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.XPATH, trigger_xpath)))
            self._scroll_into_view(el)
            try:
                el.click()
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", el)
                except Exception:
                    pass
            time.sleep(self.ui_open_delay)

            # Collect visible options commonly used by custom dropdowns
            candidates = []
            for xp in ["//li[normalize-space(.)]", "//span[normalize-space(.)]", "//div[normalize-space(.)]", "//option[normalize-space(.)]"]:
                try:
                    candidates.extend([c for c in self.driver.find_elements(By.XPATH, xp) if c.is_displayed()])
                except Exception:
                    pass
            # Filter out empty/placeholder-like and unrelated texts
            def plausible(t: str) -> bool:
                if not t:
                    return False
                s = t.strip()
                if len(s) <= 1:
                    return False
                sl = s.lower()
                if sl in ("select", "choose", "--select--", "-- choose --"):
                    return False
                if s.isdigit() or "yrs" in sl or "year" in sl or "xxxx" in sl:
                    return False
                return True
            texts = [(c, (c.text or "").strip()) for c in candidates]
            texts = [(c, t) for (c, t) in texts if plausible(t)]
            if not texts:
                return False
            el_opt, label = random.choice(texts)
            try:
                el_opt.click(); self.log_message(f"Randomly selected Nearest TTD Temple: {label}"); return True
            except Exception:
                try:
                    self.driver.execute_script("arguments[0].click();", el_opt); self.log_message(f"Randomly selected Nearest TTD Temple: {label}"); return True
                except Exception:
                    return False
        except Exception as e:
            self.log_message(f"Random dropdown select error: {e}")
            return False

    def upload_file_via_trigger(self, trigger_xpath, file_path, input_xpath=None):
        try:
            if not os.path.isfile(file_path):
                self.log_message(f"Photo file not found: {file_path}")
                return False

            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)

            if trigger_xpath:
                try:
                    trigger = WebDriverWait(self.driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, trigger_xpath))
                    )
                    self._scroll_into_view(trigger)
                    self.driver.execute_script("arguments[0].click();", trigger)
                    time.sleep(1)
                except Exception as e:
                    self.log_message(f"Upload trigger click failed: {e}")

            file_input = None
            if input_xpath:
                try:
                    file_input = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, input_xpath))
                    )
                except Exception:
                    pass
            if not file_input:
                try:
                    file_input = self.driver.find_element(By.XPATH, "//input[@type='file']")
                except Exception:
                    pass

            if file_input:
                file_input.send_keys(file_path)
                self.log_message(f"Uploaded photo: {file_path}")
                return True

            self.log_message("Could not find file input for upload.")
            return False
        except Exception as e:
            self.log_message(f"Upload error: {e}")
            return False

    def set_text_by_xpath(self, xpath, value):
        if not xpath or value in (None, ""):
            return False
        # Primary attempt: XPath
        try:
            el = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
        except Exception:
            el = None
        # Fallbacks: try ID/NAME/CSS when XPath fails or element is stale
        if el is None:
            try:
                m = re.search(r"@id=\"([^\"]+)\"", xpath)
                if m:
                    el = WebDriverWait(self.driver, 6).until(EC.presence_of_element_located((By.ID, m.group(1))))
            except Exception:
                el = None
            if el is None:
                try:
                    m = re.search(r"@name=\"([^\"]+)\"", xpath)
                    if m:
                        el = WebDriverWait(self.driver, 6).until(EC.presence_of_element_located((By.NAME, m.group(1))))
                except Exception:
                    el = None
        if el is None:
            # Try CSS by id as last resort
            try:
                m = re.search(r"@id=\"([^\"]+)\"", xpath)
                if m:
                    el = WebDriverWait(self.driver, 6).until(EC.presence_of_element_located((By.CSS_SELECTOR, f"#{m.group(1)}")))
            except Exception:
                el = None
        if el is None:
            self.log_message(f"set_text_by_xpath could not locate element: {xpath}")
            return False
        try:
            self._scroll_into_view(el)
            try:
                el.clear()
            except Exception:
                self.driver.execute_script("arguments[0].value='';", el)
            el.send_keys(str(value))
            self.log_message(f"Set text at {xpath} = {value}")
            return True
        except Exception as e:
            self.log_message(f"set_text_by_xpath failed {xpath}: {e}")
            return False

    def set_radio_by_xpath(self, xpath, desired=True):
        try:
            el = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            self._scroll_into_view(el)
            checked = el.is_selected() or (el.get_attribute('checked') == 'true') or bool(el.get_attribute('checked'))
            if desired != checked:
                try:
                    el.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            return False

    def ensure_fitness_checkboxes(self, x):
        # Try by IDs first (if provided or using common defaults), then fallback to labels
        try:
            ids = [
                x.get("mentally_checkbox_id") or "mentally",
                x.get("physically_checkbox_id") or "physically",
            ]
            for cid in ids:
                try:
                    el = self.driver.find_element(By.ID, cid)
                    self._scroll_into_view(el)
                    checked = el.is_selected() or (el.get_attribute('checked') == 'true') or bool(el.get_attribute('checked'))
                    if not checked:
                        try:
                            el.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", el)
                except Exception:
                    pass
        except Exception:
            pass
        # Try provided explicit XPaths for checkboxes if present
        try:
            phys_xp = x.get("physically_checkbox_xpath")
            if phys_xp:
                self.click_xpath(phys_xp)
        except Exception:
            pass
        try:
            ment_xp = x.get("mentally_checkbox_xpath")
            if ment_xp:
                self.click_xpath(ment_xp)
        except Exception:
            pass
        
        # Fallback to label-based checking (with container then global)
        try:
            if not self.set_checkbox_by_label(x.get("fitness_container", "//*"), "mentally", True):
                self.set_checkbox_by_label("//*", "mentally", True)
        except Exception:
            pass
        try:
            if not self.set_checkbox_by_label(x.get("fitness_container", "//*"), "physically", True):
                self.set_checkbox_by_label("//*", "physically", True)
        except Exception:
            pass

    def wait_for_dropdown_ready(self, dropdown_xpath, expected_value=None, min_options=2, timeout=12):
        # Wait until a dependent dropdown is populated or contains an expected option
        if not dropdown_xpath:
            return False
        end = time.time() + timeout
        try:
            el = WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.XPATH, dropdown_xpath)))
            self._scroll_into_view(el)
            try:
                tag = (el.tag_name or "").lower()
            except Exception:
                tag = ""
            if tag == "select":
                poll = 0.18
                while time.time() < end:
                    try:
                        sel = Select(el)
                        opts = sel.options
                        if expected_value:
                            tgt = self._normalize(str(expected_value))
                            if any(tgt in self._normalize(o.text) for o in opts):
                                return True
                        elif len(opts) >= min_options:
                            return True
                    except Exception:
                        pass
                    time.sleep(poll)
                return False
            else:
                # For custom dropdowns, a brief wait is usually enough
                time.sleep(self.ui_open_delay)
                return True
        except Exception:
            return False

    def fill_srivari_team_leader(self, details, x, include_address=True):
        def gv(*keys, default=None):
            for k in keys:
                v = details.get(k)
                if v not in (None, ""):
                    return v
            return default
            
        photo = gv("photo")
        if x.get("photo_trigger") and photo:
            self.upload_file_via_trigger(x.get("photo_trigger"), photo, x.get("photo_file_input"))
            
        # 1) Aadhaar first
        id_type = gv("id_proof_type", "id_proof", default="Aadhaar")
        id_no = gv("id_number", "aadhaar", "aadhar_no")
        self.set_custom_dropdown_by_xpath(x.get("id_proof_type_dropdown",""), id_type)
        self.set_text_by_xpath(x.get("id_proof_number_input",""), id_no)
        # Wait briefly for Aadhaar-driven autofill (if any)
        self.wait_for_aadhaar_autofill(x, timeout=self.aadhaar_autofill_wait_seconds)

        # 2) Fill only if empty (respect autofill/manual input)
        self.set_text_if_empty_by_xpath(x.get("name_input",""), gv("name"))

        if x.get("dob_input") and gv("dob"):
            self.set_text_if_empty_by_xpath(x.get("dob_input",""), gv("dob"), is_dob=True)
        if x.get("age_input") and gv("age"):
            self.set_text_if_empty_by_xpath(x.get("age_input",""), gv("age"))
            
        self.set_text_if_empty_by_xpath(x.get("mobile_input",""), gv("mobile"))
        self.set_text_if_empty_by_xpath(x.get("email_input",""), gv("email", "mail_id"))
        
        if gv("blood_group") and x.get("blood_group_dropdown"):
            self.set_custom_dropdown_by_xpath(x.get("blood_group_dropdown",""), gv("blood_group"))
            
        g = (gv("gender", default="") or "").strip().lower()
        picked = False
        if g.startswith("m") and x.get("gender_male_radio"):
            picked = self.set_radio_by_xpath(x.get("gender_male_radio"), True)
        elif g.startswith("f") and x.get("gender_female_radio"):
            picked = self.set_radio_by_xpath(x.get("gender_female_radio"), True)
            
        if not picked and x.get("gender_container"):
            try:
                cont = self.driver.find_element(By.XPATH, x.get("gender_container"))
                self._scroll_into_view(cont)
                cont.click()
            except Exception:
                pass
                
        # Ensure both fitness checkboxes are checked (mentally & physically)
        self.ensure_fitness_checkboxes(x)
        
        if include_address:
            # Country
            if self.set_custom_dropdown_by_xpath(x.get("country_dropdown",""), gv("country", default="India")):
                time.sleep(self.ui_post_select_delay)
            
            # State (wait for options if dependent on country)
            st_val = gv("state")
            if st_val:
                self.wait_for_dropdown_ready(x.get("state_dropdown"), expected_value=st_val, min_options=2, timeout=15)
                self.set_custom_dropdown_by_xpath(x.get("state_dropdown",""), st_val)
                
            # District (wait for it to populate after state)
            dt_val = gv("district")
            if dt_val:
                self.wait_for_dropdown_ready(x.get("district_dropdown"), expected_value=dt_val, min_options=2, timeout=15)
                self.set_custom_dropdown_by_xpath(x.get("district_dropdown",""), dt_val)
                
            city_val = gv("city")
            if city_val:
                # If there is an explicit dropdown, try it; otherwise treat city as a text input
                if x.get("city_dropdown"):
                    self.set_custom_dropdown_by_xpath(x.get("city_dropdown",""), city_val)
                    # Verify and fallback to direct input if value not set/mismatched
                    try:
                        city_el = self.driver.find_element(By.XPATH, x.get("city_input",""))
                        current = (city_el.get_attribute("value") or "").strip()
                    except Exception:
                        current = ""
                    if not current or self._normalize(current) != self._normalize(city_val):
                        self.set_text_if_empty_by_xpath(x.get("city_input",""), city_val)
                else:
                    self.set_text_if_empty_by_xpath(x.get("city_input",""), city_val)
                    
            # Address fields (only fill if empty)
            self.set_text_if_empty_by_xpath(x.get("street_input",""), gv("street"))
            self.set_text_if_empty_by_xpath(x.get("doorno_input",""), gv("doorno", "door_no"))
            self.set_text_if_empty_by_xpath(x.get("pincode_input",""), gv("pincode", "pin_code"))
            
            # Nearest TTD temple (robust selection) – leave as is if already chosen
            ntt = gv("nearest_ttd_temple") or gv("nearest ttd temple")
            if x.get("nearest_ttd_temple_dropdown"):
                # Try a direct value first
                if ntt and self.set_custom_dropdown_by_xpath(x.get("nearest_ttd_temple_dropdown",""), ntt):
                    pass
                else:
                    try:
                        el = WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.XPATH, x.get("nearest_ttd_temple_dropdown",""))))
                        current = (el.get_attribute("value") or "").strip()
                        if not current:
                            self._scroll_into_view(el)
                            el.click(); time.sleep(self.ui_open_delay)
                            if not self.pick_random_from_dropdown(x.get("nearest_ttd_temple_dropdown","")):
                                for _ in range(4):
                                    el.send_keys(Keys.ARROW_DOWN); time.sleep(self.ui_key_delay)
                                el.send_keys(Keys.ENTER); time.sleep(self.ui_post_select_delay)
                    except Exception:
                        self.log_message("Could not set Nearest TTD Temple.")

    def load_srivari_source(self):
        config = {"general": {}, "members": []}
        try:
            cfg_path = self.get_config_path()
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    config = json.load(f) or config
            else:
                # Fallback to legacy file in same dir as config
                legacy = os.path.join(self.get_config_dir(), "srivari_members.json")
                if os.path.exists(legacy):
                    with open(legacy, "r", encoding="utf-8") as f:
                        data = json.load(f) or {}
                        config["members"] = data.get("members", [])
        except Exception as e:
            self.log_message(f"Failed to load Srivari data: {e}")
        return config

    def run_srivari_group_flow(self):
        cfg = self.load_srivari_source()
        general = cfg.get("general", {})
        members = cfg.get("members", [])

        if not members:
            self.log_message("No members found in Srivari data.")
            return

        x = self.get_srivari_xpaths()
        if not x:
            self.log_message("Srivari XPaths not configured. Please provide XPaths.")
            return

        leader = members[0]
        leader.setdefault("country", "India")

        self.log_message("Filling Team Leader details...")
        self.fill_srivari_team_leader(leader, x, include_address=True)

        limit = None
        try:
            gs = int(general.get("group_size")) if general.get("group_size") else None
            if gs and gs > 0:
                limit = gs
        except Exception:
            pass

        # Crash-recovery: resume from last saved member index
        resume_from = 2
        try:
            meta_path = "booking_data.json"
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f) or {}
                resume_from = int(meta.get("current_member_index", 2))
        except Exception:
            resume_from = 2

        for idx, m in enumerate(members[1:], start=2):
            if limit and idx > limit:
                break
            if idx < resume_from:
                continue

            # Wait for your manual click, but detect progress by form reset (not staleness)
            self.log_message("⏸ Click 'Save and Add Sevak' when ready...")
            start = time.time()
            detected = False
            while time.time() - start < 90:  # up to 90s to detect form reset
                if self.wait_for_blank_member_form(x, timeout=3):
                    detected = True
                    break
                time.sleep(0.4)
            if detected:
                self.log_message("✅ Detected form reset. Continuing with next Sevak...")
            else:
                self.log_message("⚠️ Could not auto-detect form reset. Clearing fields and proceeding.")
                try:
                    self.clear_member_form(x)
                except Exception:
                    # Fallback minimal clear
                    self.clear_input_by_xpath(x.get("name_input"))
                    self.clear_input_by_xpath(x.get("id_proof_number_input"))

            if not self.wait_for_blank_member_form(x):
                self.log_message("Form did not reset after Save and Add. Clearing manually...")
                self.clear_input_by_xpath(x.get("name_input"))
                self.clear_input_by_xpath(x.get("id_proof_number_input"))

            self.log_message(f"Filling Member {idx} details...")
            # Aadhaar-first, and only fill empty fields for members
            self.fill_srivari_team_leader(m, x, include_address=True)

            # Save progress index for crash recovery
            try:
                with open("booking_data.json", "r", encoding="utf-8") as f:
                    meta = json.load(f) if f.readable() else {}
            except Exception:
                meta = {}
            try:
                meta["current_member_index"] = idx + 1
                with open("booking_data.json", "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=2)
            except Exception:
                pass

        # For the final member, detect save by input reset rather than staleness
        self.log_message("⏸ Click 'Save and Add Sevak' for the final member...")
        start = time.time()
        while time.time() - start < 60:
            if self.wait_for_blank_member_form(x, timeout=3):
                self.log_message("✅ Detected final form reset. Saved.")
                break
            time.sleep(0.4)
        else:
            self.log_message("⚠️ Could not confirm final save by reset. Proceeding.")

        if general.get("auto_select_date"):
            self.log_message("Attempting to continue to booking...")
            if x.get("continue_button"):
                if self.wait_for_continue_clickable(x.get("continue_button"), timeout=90):
                    if not self.click_xpath(x.get("continue_button")):
                        self.log_message("Could not click 'Continue'. Please verify XPath.")
                else:
                    self.log_message("Continue button not clickable.")
        
        if general.get("auto_download_ticket"):
            self.log_message("Auto-download enabled. Tickets should go to configured folder.")

        # Clear resume marker after successful flow
        try:
            meta_path = "booking_data.json"
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f) or {}
                if "current_member_index" in meta:
                    del meta["current_member_index"]
                    with open(meta_path, "w", encoding="utf-8") as f:
                        json.dump(meta, f, indent=2)
        except Exception:
            pass

    def get_srivari_xpaths(self):
        return {
            "photo_file_input": None,
            "photo_trigger": "//*[@id=\"__next\"]/div/main/div/div/div/div[1]/div[1]/div[1]/div[1]/img",
            "id_proof_type_dropdown": "//*[@id=\"idType\"]",
            "id_proof_number_input": "//*[@id=\"idNumber\"]",
            "name_input": "//*[@id=\"sevakName\"]",
            "dob_input": "//*[@id=\"dob\"]",
            "age_input": "//*[@id=\"age\"]",
            "mobile_input": "//*[@id=\"mobileNo\"]",
            "email_input": "//*[@id=\"email\"]",
            "blood_group_dropdown": None,
            "gender_container": "//*[@id=\"__next\"]/div/main/div/div/div/div[1]/div/div/div/div",
            "gender_male_radio": None,
            "gender_female_radio": None,
            "fitness_container": "//*[@id=\"fitness\"]",
            "physically_checkbox_xpath": "//*[@id=\"fitness\"]/div/label[2]",
            "country_dropdown": "//*[@id=\"country\"]",
            "state_dropdown": "//*[@id=\"state\"]",
            "district_dropdown": "//*[@id=\"district\"]",
            "city_input": "//*[@id=\"city\"]",
            "street_input": "//*[@id=\"street\"]",
            "doorno_input": "//*[@id=\"doorNo\"]",
            "pincode_input": "//*[@id=\"pincode\"]",
            # Nearest TTD Temple dropdown (explicit ID)
            "nearest_ttd_temple_dropdown": "//*[@id=\"nearestTtdTemple\"]",
            "member_container_template": "//*[@id=\"item-{index}\"]",
            "save_add_sevak_button": "//*[@id=\"__next\"]/div/main/div/div/div/div/button/span",
            "continue_button": "//*[@id=\"__next\"]/div/main/div/div/button"
        }

    def run_bot(self):
        try:
            if not self.driver:
                self.log_message("Browser not available.")
                self.stop_bot()
                return
            self.wait_for_srivari_page()
            self.log_message("Srivari Seva form detected. Starting group fill...")
            self.run_srivari_group_flow()
            while self.is_running and self.is_browser_open:
                try:
                    _ = self.driver.current_url
                    time.sleep(2)
                except Exception:
                    self.is_browser_open = False
                    self.log_message("Browser closed by user.")
                    break
        except Exception as e:
            self.log_message(f"Error in bot execution: {str(e)}")
        finally:
            if not self.is_running:
                try:
                    self.status_label.config(text="Status: Inactive", foreground="red")
                except Exception:
                    pass
            elif not self.is_browser_open:
                try:
                    self.status_label.config(text="Status: Browser closed", foreground="red")
                    self.open_browser_button.config(state=tk.NORMAL)
                    self.activate_button.config(state=tk.DISABLED)
                except Exception:
                    pass

    def wait_for_srivari_page(self):
        self.log_message("Waiting for Srivari Seva form...")
        try:
            x = self.get_srivari_xpaths()
            anchors = [x.get("id_proof_type_dropdown"),
                x.get("id_proof_number_input"),
                x.get("name_input"),
                x.get("mobile_input"),
                x.get("email_input"),
            ]
            anchors = [a for a in anchors if a]
            WebDriverWait(self.driver, 30).until(
                lambda d: any(d.find_elements(By.XPATH, a) for a in anchors)
            )
            self.log_message("Form detected.")
        except TimeoutException:
            self.log_message("Could not find Srivari form anchors. You may not be on the correct page.")

    def is_srivari_page(self):
        try:
            return bool(self.driver.find_elements(By.XPATH,
                "//*[self::h1 or self::h2 or self::h3 or self::legend][contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'team leader') or contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'srivari seva')]"
            ))
        except Exception:
            return False

    def arrange_windows_side_by_side(self):
        try:
            # Determine screen size without relying on Tk when running headless (root=None)
            try:
                scr_w = int(self.driver.execute_script("return (window.screen && (window.screen.availWidth||window.screen.width)) || 1920;")) if self.driver else 1920
                scr_h = int(self.driver.execute_script("return (window.screen && (window.screen.availHeight||window.screen.height)) || 1080;")) if self.driver else 1080
            except Exception:
                scr_w, scr_h = 1920, 1080

            if self.root is not None:
                # Split screen: GUI on left, browser on right
                gui_w = int(scr_w * 0.45)
                gui_h = int(scr_h * 0.95)
                try:
                    self.root.geometry(f"{gui_w}x{gui_h}+0+0")
                except Exception:
                    pass
                if self.driver:
                    try:
                        self.driver.set_window_rect(x=gui_w, y=0, width=max(800, scr_w - gui_w), height=max(600, scr_h - 80))
                    except Exception:
                        pass
            else:
                # No GUI: maximize/resize browser to near full screen
                if self.driver:
                    try:
                        self.driver.set_window_rect(x=0, y=0, width=max(1024, scr_w), height=max(700, scr_h - 80))
                    except Exception:
                        pass
        except Exception as e:
            self.log_message(f"Window arrangement failed: {e}")

    def on_closing(self):
        self.is_running = False
        if self.driver:
            self.log_message("Bot stopped. Please close the browser manually when done.")
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = TTDBookingBot(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()