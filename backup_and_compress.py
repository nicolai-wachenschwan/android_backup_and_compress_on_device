import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import os
import subprocess
import threading
import sys
import logging
import time
import re
from datetime import datetime, timezone # NEU: timezone importiert
import json
from pathlib import Path

# --- Pillow-Import ---
try:
    # NEU: ExifTags hinzugefügt, um Metadaten besser lesen zu können
    from PIL import Image, UnidentifiedImageError, ExifTags
except ImportError:
    print("Warnung: 'Pillow' nicht gefunden. Bildkomprimierung wird deaktiviert.")
    print("Installieren mit: pip install Pillow")
    Image = None

# --- NEU: Optionaler Windows-Import für das Setzen des Erstellungsdatums ---
pywin32_available = False
if sys.platform == "win32":
    try:
        import win32file
        import pywintypes
        pywin32_available = True
    except ImportError:
        print("Hinweis: 'pywin32' nicht gefunden. Das Erstellungsdatum von Dateien wird nicht gesetzt.")
        print("Für diese Funktion unter Windows, führen Sie aus: pip install pywin32")


class AndroidBackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Android Backup & Replace Tool V2.3 (Updated)") # Version erhöht
        self.root.geometry("950x980") # Höhe angepasst für neue Sektion
        self.setup_file_logging()

        main_frame = tk.Frame(root, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- PROCESS CONTROL ---
        process_frame = ttk.LabelFrame(main_frame, text="Prozess-Steuerung", padding=(10, 5))
        process_frame.pack(fill=tk.X, pady=5)
        self.process_button = tk.Button(process_frame, text="Start Process", command=self.start_process_thread,
                                        bg="#4CAF50", fg="white", font=('Helvetica', 12, 'bold'), height=2)
        self.process_button.pack(fill=tk.X, pady=5)

        # --- STEP 1: BACKUP SECTION ---
        backup_frame = ttk.LabelFrame(main_frame, text="1. Android Backup", padding=(10, 5))
        backup_frame.pack(fill=tk.X, pady=5)
        tk.Label(backup_frame, text="Android Pfad:").grid(row=0, column=0, sticky="w", pady=2)
        self.android_path_entry = tk.Entry(backup_frame)
        self.android_path_entry.insert(0, "/sdcard/DCIM/Camera")
        self.android_path_entry.grid(row=0, column=1, sticky="ew", padx=5)
        tk.Button(backup_frame, text="Test Connection", command=self.test_adb_connection).grid(row=0, column=2)
        tk.Label(backup_frame, text="Backup nach:").grid(row=1, column=0, sticky="w", pady=2)
        self.backup_dir_entry = tk.Entry(backup_frame)
        self.backup_dir_entry.grid(row=1, column=1, sticky="ew", padx=5)
        tk.Button(backup_frame, text="...", command=self.select_backup_dir).grid(row=1, column=2)
        tk.Label(backup_frame, text="Dateiname-Filter (Regex):").grid(row=2, column=0, sticky="w", pady=2)
        self.regex_filter_var = tk.StringVar()
        self.regex_filter_entry = tk.Entry(backup_frame, textvariable=self.regex_filter_var)
        self.regex_filter_entry.insert(0, ".*2025.*") 
        self.regex_filter_entry.grid(row=2, column=1, sticky="ew", padx=5)
        backup_frame.columnconfigure(1, weight=1)

        # --- STEP 2: COMPRESSION SECTION ---
        compress_frame = ttk.LabelFrame(main_frame, text="2. Komprimierung (Optional)", padding=(10, 5))
        compress_frame.pack(fill=tk.X, pady=5)
        self.enable_compression_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(compress_frame, text="Komprimierung nach dem Backup aktivieren",
                        variable=self.enable_compression_var, command=self.toggle_ui_states).pack(anchor="w")
        self.compression_settings_frame = ttk.Frame(compress_frame)
        self.compression_settings_frame.pack(fill=tk.X, pady=5)
        tk.Label(self.compression_settings_frame, text="Kompr. Zielordner:", width=15).grid(row=0, column=0, sticky="w")
        self.compress_dest_entry = tk.Entry(self.compression_settings_frame)
        self.compress_dest_entry.grid(row=0, column=1, sticky="ew", padx=5)
        self.compress_dest_button = tk.Button(self.compression_settings_frame, text="...", command=self.select_compress_dest)
        self.compress_dest_button.grid(row=0, column=2)
        self.compression_settings_frame.columnconfigure(1, weight=1)
        settings_container = ttk.Frame(self.compression_settings_frame)
        settings_container.grid(row=1, column=0, columnspan=3, sticky="ew", pady=5)
        settings_container.columnconfigure(0, weight=1)
        settings_container.columnconfigure(1, weight=1)
        video_frame = ttk.LabelFrame(settings_container, text="Video-Einstellungen", padding=(5, 3))
        video_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        tk.Label(video_frame, text="CRF:").grid(row=0, column=0, sticky="w")
        self.crf_value = tk.IntVar(value=28)
        self.crf_scale = ttk.Scale(video_frame, from_=18, to=40, variable=self.crf_value, command=self.update_crf_label)
        self.crf_scale.grid(row=0, column=1, sticky="ew", padx=5)
        self.crf_label = ttk.Label(video_frame, text="")
        self.crf_label.grid(row=0, column=2)
        tk.Label(video_frame, text="Auflösung:").grid(row=1, column=0, sticky="w")
        self.resolution_var = tk.StringVar(value="720")
        self.resolution_combo = ttk.Combobox(video_frame, textvariable=self.resolution_var,
                                             values=["Original", "1080", "720", "480"], state="readonly")
        self.resolution_combo.grid(row=1, column=1, columnspan=2, sticky="ew", padx=5)
        video_frame.columnconfigure(1, weight=1)
        image_frame = ttk.LabelFrame(settings_container, text="Bild-Einstellungen", padding=(5, 3))
        image_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.process_images_var = tk.BooleanVar(value=True)
        self.img_check = ttk.Checkbutton(image_frame, text="Bilder komprimieren", variable=self.process_images_var)
        self.img_check.pack(anchor="w")
        img_settings = ttk.Frame(image_frame)
        img_settings.pack(fill=tk.X)
        tk.Label(img_settings, text="Min. Größe (MB):").grid(row=0, column=0, sticky="w")
        self.min_img_size_var = tk.DoubleVar(value=1.0)
        self.min_size_entry = ttk.Entry(img_settings, textvariable=self.min_img_size_var, width=6)
        self.min_size_entry.grid(row=0, column=1, sticky="w", padx=5)
        tk.Label(img_settings, text="Max. Auflösung (px):").grid(row=1, column=0, sticky="w")
        self.img_resolution_var = tk.IntVar(value=1600)
        self.max_res_entry = ttk.Entry(img_settings, textvariable=self.img_resolution_var, width=6)
        self.max_res_entry.grid(row=1, column=1, sticky="w", padx=5)
        tk.Label(img_settings, text="Qualität (%):").grid(row=2, column=0, sticky="w")
        self.img_quality_var = tk.IntVar(value=90)
        self.quality_entry = ttk.Entry(img_settings, textvariable=self.img_quality_var, width=6)
        self.quality_entry.grid(row=2, column=1, sticky="w", padx=5)

        # --- NEU: geteiltes Layout ab hier ---
        split_pane = ttk.Panedwindow(main_frame, orient=tk.HORIZONTAL)
        split_pane.pack(fill=tk.BOTH, expand=True, pady=5)
        # Linke Seite: Replace + Fortschritt
        left_frame = ttk.Frame(split_pane, padding=5)
        split_pane.add(left_frame, weight=1)

        # Rechte Seite: Log
        right_frame = ttk.Frame(split_pane, padding=5)
        split_pane.add(right_frame, weight=1)        
                # --- NEU: TIMESTAMP/METADATEN SEKTION ---
        timestamp_frame = ttk.LabelFrame(left_frame, text="Metadaten & Timestamps", padding=(10, 5))
        timestamp_frame.pack(fill=tk.X, pady=5)
        self.use_earliest_date_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(timestamp_frame,
                        text="Frühestes Datum (aus Metadaten & Datei) als Erstellungsdatum verwenden",
                        variable=self.use_earliest_date_var).pack(anchor="w")


        # --- STEP 3: REPLACE ON ANDROID ---
        replace_frame = ttk.LabelFrame(left_frame, text="3. Originale auf Gerät ersetzen (Optional & Riskant)", padding=(10, 5))
        replace_frame.pack(fill=tk.X, pady=5)
        self.enable_replace_var = tk.BooleanVar(value=False)
        self.replace_check = ttk.Checkbutton(replace_frame, text="Ersetzen nach Komprimierung aktivieren",
                                             variable=self.enable_replace_var, command=self.toggle_ui_states)
        self.replace_check.pack(anchor="w")
        warning_label = tk.Label(replace_frame,
                                 text=("ACHTUNG: \nDieser Schritt überschreibt\n die Originaldateien auf dem Handy.\n "
                                       "Nur aktivieren, \nwenn das Backup verifiziert wurde!"),
                                 fg="red", wraplength=400, justify=tk.LEFT)
        warning_label.pack(anchor="w", pady=5)
        self.force_replace_var = tk.BooleanVar(value=False)
        self.force_replace_check = ttk.Checkbutton(replace_frame, text="Ersetzen erzwingen (auch wenn Größen ähnlich sind)",
                                                  variable=self.force_replace_var)
        self.force_replace_check.pack(anchor="w")

        # --- PROGRESS (Fortschritt) ---
        progress_frame = ttk.LabelFrame(left_frame, text="Fortschritt", padding=(10, 5))
        progress_frame.pack(fill=tk.X, pady=10)
        self.progress_label = tk.Label(progress_frame, text="Bereit.")
        self.progress_label.pack(fill=tk.X)
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # --- LOG auf rechter Seite ---
        log_frame = ttk.LabelFrame(right_frame, text="Log", padding=10)
        log_frame.pack(expand=True, fill=tk.BOTH, pady=5)
        self.log_text_widget = scrolledtext.ScrolledText(log_frame, state='disabled', wrap=tk.WORD, height=10)
        self.log_text_widget.pack(expand=True, fill=tk.BOTH)


        self.video_extensions = ('.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.mpeg', '.mpg', '.m4v', '.3gp')
        self.image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.heic', '.dng', '.webp')
        self.compressible_image_formats = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.bmp': 'BMP'}

        self.toggle_ui_states()
        self.update_crf_label()

    def setup_file_logging(self):
        log_dir = os.path.dirname(os.path.abspath(__file__))
        log_filename = f"android_backup_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
        log_filepath = os.path.join(log_dir, log_filename)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                            handlers=[logging.FileHandler(log_filepath, encoding='utf-8')])

    def log_to_gui(self, message, level="INFO"):
        logging.info(message)
        self.root.after(0, lambda: self._append_log_message(message))

    def _append_log_message(self, message):
        self.log_text_widget.configure(state='normal')
        self.log_text_widget.insert(tk.END, message + '\n')
        self.log_text_widget.configure(state='disabled')
        self.log_text_widget.see(tk.END)

    def update_progress(self, text=None, value=None, maximum=None):
        self.root.after(0, lambda: self._update_progress_ui(text, value, maximum))

    def _update_progress_ui(self, text, value, maximum):
        if text: self.progress_label.config(text=text)
        if maximum is not None: self.progress_bar.config(maximum=maximum)
        if value is not None: self.progress_bar.config(value=value)

    def toggle_ui_states(self):
        compress_state = 'normal' if self.enable_compression_var.get() else 'disabled'
        for widget in [self.compress_dest_entry, self.compress_dest_button, self.crf_scale,
                       self.resolution_combo, self.img_check, self.min_size_entry,
                       self.max_res_entry, self.quality_entry]:
            widget.configure(state=compress_state)
        replace_state = 'normal' if self.enable_compression_var.get() else 'disabled'
        self.replace_check.configure(state=replace_state)
        if not self.enable_compression_var.get(): self.enable_replace_var.set(False)

    def update_crf_label(self, event=None):
        value = self.crf_value.get()
        desc = "(Hohe Qualität)" if value <= 22 else "(Ausgewogen)" if value <= 28 else "(Hohe Komprimierung)"
        self.crf_label.config(text=f"{value} {desc}")

    def select_backup_dir(self):
        directory = filedialog.askdirectory(title="Select Backup Directory")
        if directory:
            self.backup_dir_entry.delete(0, tk.END)
            self.backup_dir_entry.insert(0, directory)

    def select_compress_dest(self):
        directory = filedialog.askdirectory(title="Select Compression Target Directory")
        if directory:
            self.compress_dest_entry.delete(0, tk.END)
            self.compress_dest_entry.insert(0, directory)

    def check_adb(self):
        return self.run_command_with_retries(['adb', 'version'], timeout=5, retries=1) is not None

    def test_adb_connection(self):
        try:
            self.check_adb()
        except Exception as e:
            messagebox.showerror(f"ADB Fehler: {e}", "ADB nicht gefunden oder nicht im Systempfad (PATH)!")
            return
        print("ADB found.")
        result = self.run_command_with_retries(['adb', 'devices'], retries=1)
        if result is None:
            messagebox.showerror("ADB Fehler", "Der Befehl 'adb devices' konnte nicht ausgeführt werden.")
            return
        lines = result.stdout.strip().split('\n')[1:]
        devices = [line.split()[0] for line in lines if line.strip() and 'unauthorized' not in line]
        if not devices:
            messagebox.showwarning("Kein Gerät", "Kein autorisiertes Android-Gerät gefunden!")
        else:
            messagebox.showinfo("Erfolg", f"Gerät verbunden: {devices[0]}")

    def start_process_thread(self):
        # Validation checks
        if not self.backup_dir_entry.get():
            messagebox.showerror("Fehler", "Bitte wähle ein Backup-Verzeichnis!")
            return
        if self.enable_compression_var.get():
            if not self.compress_dest_entry.get():
                messagebox.showerror("Fehler", "Bitte wähle ein Zielverzeichnis für die Komprimierung!")
                return
            if self.backup_dir_entry.get() == self.compress_dest_entry.get():
                messagebox.showerror("Fehler", "Backup- und Komprimierungsverzeichnis dürfen nicht identisch sein!")
                return
        if self.enable_replace_var.get() and not messagebox.askyesno("Sicherheitsabfrage", "ACHTUNG!\n\nDu bist im Begriff, Originaldateien auf deinem Handy unwiderruflich zu überschreiben.\n\nBist du absolut sicher, dass du fortfahren willst?"):
            return
        if not self.check_adb():
            messagebox.showerror("Fehler", "ADB ist nicht verfügbar!")
            return

        self.process_button.config(state=tk.DISABLED)
        threading.Thread(target=self.run_full_process, daemon=True).start()

    def run_command_with_retries(self, command, retries=3, delay=5, timeout=120, capture_output=True):
        for attempt in range(retries):
            try:
                startupinfo = None
                if sys.platform == "win32":
                    startupinfo = subprocess.STARTUPINFO()
                    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                result = subprocess.run(command, check=True, capture_output=capture_output, text=True,
                                        timeout=timeout, startupinfo=startupinfo, encoding='utf-8', errors='ignore')
                return result
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
                stderr = e.stderr if hasattr(e, 'stderr') and e.stderr else '(Kein stderr)'
                self.log_to_gui(f"WARNUNG: Befehl fehlgeschlagen (Versuch {attempt + 1}/{retries}). Kommando:{command} Fehler: {stderr.strip()}", "WARN")
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    self.log_to_gui(f"FEHLER: Befehl nach {retries} Versuchen endgültig fehlgeschlagen.", "ERROR")
                    return None
        return None

    def _get_android_file_size(self, remote_path):
        """Ermittelt die Dateigröße einer Datei auf dem Android-Gerät in Bytes."""
        # 'stat -c %s' ist zuverlässiger als 'ls -l' zum Parsen
        res = self.run_command_with_retries(['adb', 'shell', 'stat', '-c', '%s', remote_path], retries=2, timeout=10)
        if res and res.returncode == 0 and res.stdout.strip().isdigit():
            return int(res.stdout.strip())
        return None
    
    def _set_android_file_timestamp(self, remote_path, dt_object):
        """Sets the modification time of a file on the Android device using 'touch'."""
        if not dt_object:
            self.log_to_gui(f"  WARNUNG: Kein Datum zum Setzen für {Path(remote_path).name} vorhanden.", "WARN")
            return

        # Format für 'touch -t' ist YYYYMMDDHHMM.SS
        timestamp_str = dt_object.strftime('%Y%m%d%H%M.%S')
        
        # Der Pfad muss für die Shell korrekt behandelt werden, falls er Leerzeichen enthält
        # In der Regel reicht es, ihn am Ende anzugeben.
        command = ['adb', 'shell', 'touch', '-m', '-t', timestamp_str, remote_path]
        
        self.log_to_gui(f"  -> Setze Datum auf Gerät: {dt_object.strftime('%Y-%m-%d %H:%M:%S')}")
        result = self.run_command_with_retries(command, retries=2)
        if not result:
            self.log_to_gui(f"  FEHLER beim Setzen des Datums für {Path(remote_path).name}", "ERROR")
        return result is not None    
    
    def get_media_creation_date(self, filepath):
        """Tries to extract the internal 'creation date' from video or image metadata."""
        ext = os.path.splitext(filepath)[1].lower()
        try:
            if ext in self.video_extensions:
                command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', filepath]
                result = self.run_command_with_retries(command, capture_output=True, retries=2)
                if result:
                    metadata = json.loads(result.stdout)
                    date_str = metadata.get('format', {}).get('tags', {}).get('creation_time')
                    if date_str:
                        date_str = date_str.split('.')[0] # remove fractional seconds
                        # Handle both Z and timezone offsets
                        if 'Z' in date_str:
                             return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        else:
                             return datetime.fromisoformat(date_str)

            elif ext in self.image_extensions and Image:
                with Image.open(filepath) as img:
                    exif_data = img.getexif()
                    if exif_data:
                        # 36867: DateTimeOriginal, 306: DateTime
                        date_str = exif_data.get(36867) or exif_data.get(306)
                        if date_str:
                            return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
        except Exception as e:
            self.log_to_gui(f"WARNUNG: Metadaten-Datum von '{os.path.basename(filepath)}' konnte nicht gelesen werden: {e}", "WARN")
        return None
    def get_media_creation_date_advanced(self, local_filepath, remote_filepath=None):
        """
        Ermittelt das Erstellungsdatum einer Mediendatei aus mehreren Quellen und gibt das älteste zurück.

        Die Funktion prüft in dieser Reihenfolge und sammelt alle gefundenen Daten:
        1.  Eingebettete Metadaten (EXIF für Bilder, Creation-Time für Videos).
        2.  Das Änderungsdatum der Datei direkt vom Android-Gerät via ADB.
        3.  Ein Datum, das aus dem Dateinamen geparst wird (z.B. YYYYMMDD_HHMMSS).

        Args:
            self: Die Instanz der App-Klasse.
            local_filepath (str): Der lokale Pfad zur (Backup-)Datei, die analysiert wird.
            remote_filepath (str): Der ursprüngliche Pfad der Datei auf dem Android-Gerät.

        Returns:
            datetime: Das älteste gefundene Datum als timezone-aware datetime-Objekt (UTC)
                    oder None, wenn kein Datum ermittelt werden konnte.
        """
        candidate_dates = []
        filename = Path(local_filepath).name

        # --- Quelle 1: Eingebettete Metadaten (aus der lokalen Datei) ---
        try:
            ext = os.path.splitext(local_filepath)[1].lower()
            if ext in self.video_extensions:
                command = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', local_filepath]
                result = self.run_command_with_retries(command, capture_output=True, retries=2)
                if result:
                    metadata = json.loads(result.stdout)
                    date_str = metadata.get('format', {}).get('tags', {}).get('creation_time')
                    if date_str:
                        date_str = date_str.split('.')[0]
                        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        candidate_dates.append(dt)
                        self.log_to_gui(f"  -> Datum aus Video-Metadaten: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

            elif ext in self.image_extensions and Image:
                with Image.open(local_filepath) as img:
                    exif_data = img.getexif()
                    if exif_data:
                        date_str = exif_data.get(36867) or exif_data.get(306) # DateTimeOriginal or DateTime
                        if date_str:
                            dt = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
                            candidate_dates.append(dt)
                            self.log_to_gui(f"  -> Datum aus Bild-Metadaten: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            self.log_to_gui(f"WARNUNG: Metadaten-Analyse für '{filename}' fehlgeschlagen: {e}", "WARN")
        
        skip_other_sources = False
        if len(candidate_dates) > 0:
            skip_other_sources = True
        # --- Quelle 2: Zeitstempel vom Android-Gerät ---
        if not skip_other_sources:
            try:
                if remote_filepath is not None:# Führt 'adb shell stat -c %Y <filepath>' aus, um das Änderungsdatum als Unix-Timestamp zu erhalten
                    cmd = ['adb', 'shell', 'stat', '-c', '%Y', remote_filepath]
                    result = self.run_command_with_retries(cmd, retries=2)
                    if result and result.stdout.strip().isdigit():
                        timestamp = int(result.stdout.strip())
                        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        candidate_dates.append(dt)
                        self.log_to_gui(f"  -> Datum vom Gerät (mtime): {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except Exception as e:
                self.log_to_gui(f"WARNUNG: Zeitstempel vom Gerät für '{filename}' konnte nicht gelesen werden: {e}", "WARN")

            # --- Quelle 3: Datum aus Dateinamen parsen ---
            try:
                # Sucht nach Mustern wie '20251019_213005' oder '20251019-213005' oder '20251019213005'
                match = re.search(r'(\d{8})[_.-]?(\d{6})', filename)
                if match:
                    date_str = f"{match.group(1)}{match.group(2)}"
                    dt = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                    candidate_dates.append(dt)
                    self.log_to_gui(f"  -> Datum aus Dateiname erkannt: {dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except ValueError:
                self.log_to_gui(f"INFO: Zahlen im Dateinamen '{filename}' konnten nicht als Datum interpretiert werden.", "INFO")
            except Exception as e:
                self.log_to_gui(f"WARNUNG: Fehler beim Parsen des Dateinamens '{filename}': {e}", "WARN")

        # --- Finale Auswertung: Finde das älteste Datum ---
        if not candidate_dates:
            self.log_to_gui(f"FEHLER: Konnte für '{filename}' kein gültiges Datum aus irgendeiner Quelle ermitteln.", "ERROR")
            return None

        # Stelle sicher, dass alle datetime-Objekte eine Zeitzone haben, um Vergleiche zu ermöglichen
        aware_dates = []
        for dt in candidate_dates:
            if dt.tzinfo is None:
                # Annahme: naive Zeitstempel sind in der lokalen Systemzeit. Konvertiere sie zu UTC.
                # Für Konsistenz behandeln wir alle als UTC.
                aware_dates.append(dt.astimezone(timezone.utc))
            else:
                aware_dates.append(dt)

        oldest_date = min(aware_dates)
        self.log_to_gui(f"  -> Ältestes Datum für '{filename}' gewählt: {oldest_date.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        return oldest_date

    # --- NEUE FUNKTION (aus video_compressor.py übernommen) ---
    def copy_file_timestamps(self, source, dest):
        """Copies timestamps (mtime, atime) and optionally ctime on Windows using the selected logic."""
        try:
            stat = os.stat(source)
            # Make dates timezone-aware (UTC) for correct comparison
            fs_creation_dt = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc)
            fs_modification_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
            fs_access_dt = datetime.fromtimestamp(stat.st_atime, tz=timezone.utc)

            final_creation_dt = fs_creation_dt
            final_modification_dt = fs_modification_dt
            final_access_dt = fs_access_dt

            if self.use_earliest_date_var.get():
                candidate_dates = [fs_creation_dt, fs_modification_dt] # access_dt is usually not relevant
                media_creation_dt = self.get_media_creation_date(source)

                if media_creation_dt:
                    # Make media date timezone-aware if it's naive
                    if media_creation_dt.tzinfo is None:
                        media_creation_dt = media_creation_dt.replace(tzinfo=timezone.utc)
                    candidate_dates.append(media_creation_dt)

                # Filter out potential None values before finding the minimum
                valid_dates = [d for d in candidate_dates if d]
                if valid_dates:
                    final_creation_dt = min(valid_dates)
                    self.log_to_gui(f"  -> Ältestes Datum gefunden: {final_creation_dt.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    self.log_to_gui(f"  -> WARNUNG: Konnte kein gültiges Datum für {Path(source).name} finden.")

            os.utime(dest, (final_access_dt.timestamp(), final_modification_dt.timestamp()))

            if pywin32_available:
                try:
                    win_creation_time = pywintypes.Time(final_creation_dt)
                    win_access_time = pywintypes.Time(final_access_dt)
                    win_modification_time = pywintypes.Time(final_modification_dt)

                    handle = win32file.CreateFile(dest, win32file.GENERIC_WRITE, 0, None, win32file.OPEN_EXISTING, 0, None)
                    win32file.SetFileTime(handle, win_creation_time, win_access_time, win_modification_time)
                    win32file.CloseHandle(handle)
                except Exception as e:
                    self.log_to_gui(f"  WARNUNG: Konnte Erstellungsdatum nicht setzen: {e}", "WARN")

        except Exception as e:
            self.log_to_gui(f"  WARNUNG: Konnte Timestamps nicht kopieren: {e}", "WARN")

    def run_full_process(self):
        try:
            # Step 1: Backup
            self.log_to_gui("\n" + "="*80 + "\nSCHRITT 1: BACKUP VOM ANDROID GERÄT\n" + "="*80)
            backup_map = self._execute_backup_step()
            if backup_map is None: return

            # Step 2: Compression
            compression_map = None
            if self.enable_compression_var.get():
                self.log_to_gui("\n" + "="*80 + "\nSCHRITT 2: DATEIEN KOMPRIMIEREN\n" + "="*80)
                compression_map = self._execute_compression_step(backup_map)
                if compression_map is None: return

            # Step 3: Replace
            if self.enable_replace_var.get() and compression_map:
                self.log_to_gui("\n" + "="*80 + "\nSCHRITT 3: ORIGINALE AUF GERÄT ERSETZEN\n" + "="*80)
                self._execute_replace_step(compression_map)

            self.log_to_gui("\n" + "="*80 + "\nALLE OPERATIONEN ABGESCHLOSSEN!\n" + "="*80)
        except Exception as e:
            self.log_to_gui(f"FATALER FEHLER: Ein unerwarteter Fehler ist aufgetreten: {e}", "ERROR")
            logging.exception("Fatal error in run_full_process")
        finally:
            self.root.after(0, lambda: self.process_button.config(state=tk.NORMAL))
            self.update_progress("Bereit.", value=0)

    def _execute_backup_step(self):
        android_path = self.android_path_entry.get()
        backup_path = self.backup_dir_entry.get()
        regex_pattern = self.regex_filter_var.get()

        self.update_progress(f"Suche nach Dateien in {android_path}...")
        cmd = ['adb', 'shell', 'find', android_path, '-type', 'f']
        result = self.run_command_with_retries(cmd)
        if not result: return None

        all_files = [line.strip() for line in result.stdout.split('\n') if line.strip()]

        filtered_files = []
        if regex_pattern:
            try:
                prog = re.compile(regex_pattern, re.IGNORECASE)
                filtered_files = [f for f in all_files if prog.search(Path(f).name)]
                self.log_to_gui(f"{len(all_files)} Dateien gefunden, {len(filtered_files)} entsprechen dem Filter '{regex_pattern}'.")
            except re.error as e:
                messagebox.showerror("Regex Fehler", f"Ungültiger Regulärer Ausdruck:\n{e}")
                return None
        else:
            filtered_files = all_files
            self.log_to_gui(f"{len(filtered_files)} Dateien gefunden (kein Filter).")

        if not filtered_files: return {}

        self.update_progress(f"{len(filtered_files)} Dateien zu sichern...", 0, len(filtered_files))

        backup_map = {}
        for i, file_path in enumerate(filtered_files):
            rel_path = os.path.relpath(file_path, android_path)
            local_file = Path(backup_path) / rel_path
            self.update_progress(f"Sichere: {Path(file_path).name}", i + 1)

            if local_file.exists():
                self.log_to_gui(f"Übersprungen (existiert lokal): {rel_path}")
                backup_map[file_path] = str(local_file) # Wichtig: Auch existierende Dateien zur Map hinzufügen
            else:
                local_file.parent.mkdir(parents=True, exist_ok=True)
                if not self.run_command_with_retries(['adb', 'pull', file_path, str(local_file)]):
                    self.log_to_gui(f"FEHLER beim Backup von {file_path}", "ERROR")
                    continue
                backup_map[file_path] = str(local_file)

        self.log_to_gui(f"\nBackup abgeschlossen: {len(backup_map)}/{len(filtered_files)} Dateien erfolgreich gesichert.")
        return backup_map

    def _execute_compression_step(self, backup_map):
        dest_dir, compression_map = self.compress_dest_entry.get(), {}
        files_to_process = list(backup_map.items())
        if not files_to_process: return {}

        self.update_progress(f"Komprimiere {len(files_to_process)} Dateien...", 0, len(files_to_process))
        for i, (android_path, local_path) in enumerate(files_to_process):
            self.update_progress(f"Komprimiere: {Path(local_path).name}", i + 1)
            rel_path = os.path.relpath(local_path, self.backup_dir_entry.get())
            dest_path = os.path.join(dest_dir, rel_path)

            if os.path.exists(dest_path):
                self.log_to_gui(f"Übersprungen (komprimierte Datei existiert): {Path(dest_path).name}")
                compression_map[android_path] = dest_path
                continue

            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            ext = os.path.splitext(local_path)[1].lower()
            compressed_path = None
            if ext in self.video_extensions:
                compressed_path = self._compress_video(local_path, dest_path)
            elif Image and self.process_images_var.get() and ext in self.compressible_image_formats:
                if os.path.getsize(local_path) > self.min_img_size_var.get() * 1024 * 1024:
                    compressed_path = self._compress_image(local_path, dest_path)

            if compressed_path:
                # NEU: Prüfe, ob Metadaten-Datum gefunden wurde
                has_metadata_date = self.get_media_creation_date(local_path) is not None
                
                if not has_metadata_date and self.use_earliest_date_var.get():
                    self.log_to_gui(f"  -> WARNUNG: Keine Metadaten gefunden für {Path(local_path).name} - wird NICHT auf Gerät ersetzt!")
                    # NICHT zur compression_map hinzufügen!
                else:
                    compression_map[android_path] = compressed_path
                    self.log_to_gui(f"  -> Übertrage Timestamps für {Path(compressed_path).name}")
                    self.copy_file_timestamps(local_path, compressed_path)

        self.log_to_gui(f"\nKomprimierung abgeschlossen: {len(compression_map)} Dateien verarbeitet.")
        return compression_map

    def _compress_video(self, source_path, dest_path):
        # ANPASSUNG: `-map 0` hinzugefügt, um ALLE Spuren (Video, Audio, Daten, etc.) zu kopieren
        command = ['ffmpeg', '-i', source_path, '-y', '-map', '0', '-vcodec', 'libx264', '-crf', str(self.crf_value.get()),
                   '-preset', 'medium', '-c:a', 'copy', '-c:s', 'copy'] # c:s copy für Untertitel
        if self.resolution_var.get() != "Original":
            command.extend(['-vf', f'scale=-2:{self.resolution_var.get()}'])
        command.append(dest_path)
        
        # Log command for debugging
        logging.info(f"FFmpeg command: {' '.join(command)}")
        
        result = self.run_command_with_retries(command, timeout=600)
        if result:
            return dest_path
        else:
            # Bei Fehler, die fehlerhafte Zieldatei löschen
            if os.path.exists(dest_path):
                try:
                    os.remove(dest_path)
                except OSError as e:
                    self.log_to_gui(f"Konnte fehlerhafte Zieldatei nicht löschen: {e}", "WARN")
            return None


    def _compress_image(self, source_path, dest_path):
        ext = os.path.splitext(source_path)[1].lower()
        save_format = self.compressible_image_formats.get(ext)
        if not save_format: return None

        try:
            with Image.open(source_path) as img:
                # ANPASSUNG: Alle Metadaten (EXIF, XMP, etc.) versuchen zu erhalten
                params = {'quality': self.img_quality_var.get(), 'optimize': True}
                if 'exif' in img.info:
                    params['exif'] = img.info['exif']
                if 'icc_profile' in img.info:
                    params['icc_profile'] = img.info['icc_profile']

                if save_format == 'JPEG' and img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                
                img.thumbnail((self.img_resolution_var.get(), self.img_resolution_var.get()), Image.Resampling.LANCZOS)
                img.save(dest_path, format=save_format, **params)
                return dest_path
        except (UnidentifiedImageError, OSError, ValueError) as e:
            self.log_to_gui(f"FEHLER bei Bildkomprimierung von {Path(source_path).name}: {e}", "ERROR")
            return None

    def _execute_replace_step(self, compression_map):
        if not compression_map: return
        self.update_progress("Ersetze Dateien auf dem Gerät...", 0, len(compression_map))
        success_count = 0

        for i, (android_path, local_compressed_path) in enumerate(compression_map.items()):
            self.update_progress(f"Prüfe: {Path(android_path).name}", i + 1)

            local_size = os.path.getsize(local_compressed_path)
            remote_size = self._get_android_file_size(android_path)

            if remote_size is not None:
                if remote_size > 0 and abs(local_size - remote_size) / remote_size <= 0.01:
                    self.log_to_gui(f"Übersprungen (bereits auf Gerät komprimiert): {Path(android_path).name}")
                    if not self.force_replace_var.get():
                        success_count += 1
                        continue

                self.log_to_gui(f"Ersetze: {Path(android_path).name} ({remote_size or '?'} B -> {local_size} B)")
                if self.run_command_with_retries(['adb', 'push', str(local_compressed_path), str(android_path)]):
                    success_count += 1
                if not self._set_android_file_timestamp(android_path, self.get_media_creation_date_advanced(local_compressed_path,android_path)):
                    self.log_to_gui(f"  WARNUNG: Konnte Datum nicht setzen für {Path(android_path).name}", "WARN") 
            else:
                self.log_to_gui(f"FEHLER beim Ersetzen von {Path(android_path).name}", "ERROR")


        self.log_to_gui(f"\nErsetzung abgeschlossen: {success_count}/{len(compression_map)} Dateien auf Gerät verarbeitet.")

if __name__ == "__main__":
    if Image is None:
        print("\nFATAL: Pillow library not installed. Image processing is disabled.")
        print("Please run: pip install Pillow")

    # Check for ffmpeg/ffprobe
    try:
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True, startupinfo=startupinfo)
        subprocess.run(["ffprobe", "-version"], check=True, capture_output=True, startupinfo=startupinfo)
    except (subprocess.CalledProcessError, FileNotFoundError):
        messagebox.showerror("Fehlende Abhängigkeit", "FFmpeg und FFprobe wurden nicht gefunden oder sind nicht im Systempfad (PATH).\n\nBitte installieren Sie FFmpeg und stellen Sie sicher, dass es systemweit verfügbar ist.")
        sys.exit(1)
    try: 
        startupinfo = None
        if sys.platform == "win32":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(["adb", "--version"], check=True, capture_output=True, startupinfo=startupinfo)
    except (subprocess.CalledProcessError, FileNotFoundError):
        messagebox.showerror("Fehlende Abhängigkeit", "ADB wurde nicht gefunden oder ist nicht im Systempfad (PATH).\n\nBitte installieren Sie ADB und stellen Sie sicher, dass es systemweit verfügbar ist.")
        sys.exit(1)



    root = tk.Tk()
    app = AndroidBackupApp(root)
    root.mainloop()
