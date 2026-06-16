import os
import gc
import json
import uuid
import struct
import shutil
import hmac
import hashlib
import tempfile
import zipfile
import threading
import queue
import ctypes
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import math


# ==========================================
# CONSTANTS
# ==========================================
MAGIC = b"CFv1"
VERSION = 1
CHANNEL_COLORS = 3
BLOCK_SIZE = 1024


# ==========================================
# 1. HARDWARE AUTHENTICATION MODULE
# ==========================================
class HardwareAuth:
    @staticmethod
    def get_machine_fingerprint():
        mac_address = str(uuid.getnode())
        import platform
        os_info = platform.node() + platform.machine()
        raw_hardware_id = f"{mac_address}-{os_info}"
        return hashlib.sha256(raw_hardware_id.encode('utf-8')).hexdigest()


# ==========================================
# 2. UTILITY: SECURE MEMORY WIPE
# ==========================================
def secure_zero_memory(buf):
    num_bytes = len(buf)
    try:
        arr = (ctypes.c_uint8 * num_bytes).from_buffer(buf)
        for i in range(num_bytes):
            arr[i] = 0
    except Exception:
        for i in range(num_bytes):
            buf[i] = 0


def secure_zero_array(arr):
    if arr is None:
        return
    try:
        arr[:] = 0
        secure_zero_memory(arr)
    except Exception:
        pass
    del arr
    gc.collect()


# ==========================================
# 3. KEY DERIVATION MODULE
# ==========================================
class KeyDerivation:
    @staticmethod
    def derive(master_secret: str, context: str = "captain-fractal-v1") -> int:
        h = hmac.new(master_secret.encode("utf-8"), context.encode("utf-8"), hashlib.sha256)
        return int(h.hexdigest()[:8], 16)


# ==========================================
# 4. VECTORIZED STEGANOGRAPHY ENGINE
# ==========================================
class FastStegoEngine:
    def __init__(self, key_2_path="key_2_dictionary.json"):
        self.key_2_path = key_2_path
        self.lut = np.zeros((256, 3), dtype=np.uint8)
        self._cancel = threading.Event()

    def cancel(self):
        self._cancel.set()

    def clear_cancel(self):
        self._cancel.clear()

    def _should_cancel(self):
        return self._cancel.is_set()
        
    def generate_dictionary(self, seed_string):
        """Generates the Master Color Dictionary."""
        import random
        random.seed(seed_string)
        used_colors = set()
        char_to_color, color_to_char = {}, {}
        
        for byte in range(256):
            while True:
                color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                if color not in used_colors:
                    used_colors.add(color)
                    color_str = f"{color[0]},{color[1]},{color[2]}"
                    char_to_color[str(byte)] = color_str
                    color_to_char[color_str] = byte
                    break
        
        with open(self.key_2_path, 'w') as f:
            json.dump({"char_to_color": char_to_color, "color_to_char": color_to_char}, f)
        self._build_look_up_table()
        return self.key_2_path


    def _build_look_up_table(self):
        if not os.path.exists(self.key_2_path):
            return False
        with open(self.key_2_path, 'r') as f:
            data = json.load(f)["char_to_color"]
        for byte_str, color_str in data.items():
            r, g, b = map(int, color_str.split(','))
            self.lut[int(byte_str)] = [r, g, b]
        return True


    def _canvas_dimensions(self, payload_bytes):
        pixels_needed = len(payload_bytes)
        ratio = BLOCK_SIZE / math.sqrt(pixels_needed)
        width = BLOCK_SIZE
        height = BLOCK_SIZE
        if ratio < 1:
            width = max(BLOCK_SIZE, int(math.ceil(math.sqrt(pixels_needed))))
            height = max(BLOCK_SIZE, int(math.ceil(pixels_needed / width)))
        return width, height


    def generate_canvas(self, output_path, width=None, height=None, progress_callback=None):
        """Generates the chaotic Julia Set fractal canvas."""
        width = width or BLOCK_SIZE
        height = height or BLOCK_SIZE
        if self._should_cancel():
            raise RuntimeError("cancelled")
        x, y = np.meshgrid(np.linspace(-1.5, 1.5, width), np.linspace(-1.5, 1.5, height))
        c = complex(-0.8, 0.156)
        z = x + 1j * y
        img_array = np.zeros(z.shape, dtype=int)
        
        for i in range(256):
            if self._should_cancel():
                raise RuntimeError("cancelled")
            if progress_callback:
                progress_callback(i / 255.0)
            mask = np.abs(z) <= 2
            z[mask] = z[mask] ** 2 + c
            img_array[mask] = i
            
        img_normalized = np.uint8(255 * img_array / np.max(img_array))
        if progress_callback:
            progress_callback(1.0)
        Image.fromarray(img_normalized).convert('RGB').save(output_path)


    def _get_vectorized_seed(self, hardware_seed_string):
        seed_hash = hashlib.sha256(hardware_seed_string.encode('utf-8')).hexdigest()
        return int(seed_hash[:8], 16)


    def encrypt_and_package(self, input_filepath, hardware_seed, output_path=None, progress_callback=None):
        """Encrypts data, applies memory wipes, and packages into a secure Zip."""
        self.clear_cancel()
        self._build_look_up_table()
        if output_path is None:
            output_path = input_filepath + ".captain.zip"
        
        temp_dir = tempfile.mkdtemp()
        canvas_path = os.path.join(temp_dir, "canvas.png")
        payload_png = os.path.join(temp_dir, "encrypted_payload.png")
        zip_output = output_path
        header_override = None
        payload_override = None
        flat_canvas_override = None
        
        try:
            with open(input_filepath, 'rb') as f:
                file_bytes = f.read()
            data_length = len(file_bytes)
            header = struct.pack('>I', data_length)
            full_payload = np.array(list(header + file_bytes), dtype=np.uint8)
            
            canvas_w, canvas_h = self._canvas_dimensions(full_payload)
            if progress_callback:
                progress_callback(0.1)
            
            self.generate_canvas(canvas_path, width=canvas_w, height=canvas_h, progress_callback=lambda p: progress_callback(0.1 + 0.4 * p) if progress_callback else None)
            
            img_array = np.array(Image.open(canvas_path))
            h, w, _ = img_array.shape
            flat_canvas = img_array.reshape(-1, 3) 
            
            if len(full_payload) > h * w:
                raise ValueError("File is too large for the current canvas size.")

            rng = np.random.RandomState(seed=self._get_vectorized_seed(hardware_seed))
            chaotic_path = rng.permutation(h * w)
            target_indices = chaotic_path[:len(full_payload)]
            
            embedded_colors = self.lut[full_payload]
            flat_canvas[target_indices] = embedded_colors
            
            final_image = flat_canvas.reshape((h, w, 3))
            Image.fromarray(final_image).save(payload_png)
            
            if progress_callback:
                progress_callback(0.9)

            with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(payload_png, arcname="encrypted_payload.png")

            if progress_callback:
                progress_callback(1.0)

            header_override = full_payload
            flat_canvas_override = flat_canvas

            return zip_output


        finally:
            if header_override is not None:
                secure_zero_array(header_override)
            if flat_canvas_override is not None:
                secure_zero_array(flat_canvas_override)
            if payload_override is not None:
                secure_zero_array(payload_override)
            shutil.rmtree(temp_dir, ignore_errors=True)


    def decrypt_and_extract(self, zip_filepath, hardware_seed, output_path=None, progress_callback=None):
        """Extracts the Zip, decrypts the fractal, wipes memory, and restores the file."""
        self.clear_cancel()
        temp_dir = tempfile.mkdtemp()
        if output_path is None:
            output_path = zip_filepath.replace(".captain.zip", "_RESTORED")
        extracted_bytes_holder = None
        flat_canvas_holder = None
        expanded_lut_holder = None
        expanded_colors_holder = None
        
        try:
            with zipfile.ZipFile(zip_filepath, 'r') as zipf:
                zipf.extractall(temp_dir)
                
            payload_png = os.path.join(temp_dir, "encrypted_payload.png")
            key_path = os.path.join(temp_dir, "key_2_dictionary.json")
            self.key_2_path = key_path
            self._build_look_up_table()
            
            img_array = np.array(Image.open(payload_png))
            h, w, _ = img_array.shape
            flat_canvas = img_array.reshape(-1, 3)
            flat_canvas_holder = flat_canvas
            
            rng = np.random.RandomState(seed=self._get_vectorized_seed(hardware_seed))
            chaotic_path = rng.permutation(h * w)
            
            header_colors = flat_canvas[chaotic_path[:4]]
            header_bytes = bytearray()
            for color in header_colors:
                match = int(np.where((self.lut == color).all(axis=1))[0][0])
                header_bytes.append(match)
                
            target_length = struct.unpack('>I', header_bytes)[0]
            
            payload_indices = chaotic_path[4 : 4 + target_length]
            payload_colors = flat_canvas[payload_indices]
            
            expanded_lut = np.expand_dims(self.lut, axis=0)
            expanded_colors = np.expand_dims(payload_colors, axis=1)
            
            expanded_lut_holder = expanded_lut
            expanded_colors_holder = expanded_colors
            
            extracted_bytes = np.argmax(np.all(expanded_colors == expanded_lut, axis=2), axis=1).astype(np.uint8)
            
            with open(output_path, 'wb') as f:
                f.write(extracted_bytes.tobytes())

            extracted_bytes_holder = extracted_bytes
            if progress_callback:
                progress_callback(1.0)

            return output_path


        finally:
            if extracted_bytes_holder is not None:
                secure_zero_array(extracted_bytes_holder)
            if flat_canvas_holder is not None:
                secure_zero_array(flat_canvas_holder)
            if expanded_lut_holder is not None:
                secure_zero_array(expanded_lut_holder)
            if expanded_colors_holder is not None:
                secure_zero_array(expanded_colors_holder)
            shutil.rmtree(temp_dir, ignore_errors=True)


# ==========================================
# 5. WORKER THREAD HELPER
# ==========================================
class WorkerThread(threading.Thread):
    def __init__(self, target, args=(), kwargs=None, on_done=None):
        super().__init__(daemon=True)
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.on_done = on_done
        self.result = None
        self.error = None

    def run(self):
        try:
            self.result = self.target(*self.args, **self.kwargs)
        except Exception as e:
            self.error = e
        finally:
            if self.on_done:
                self.on_done(self)


# ==========================================
# 6. GRAPHICAL USER INTERFACE (GUI)
# ==========================================
class CaptainFractalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Captain Fractal Encryption Studio v1.0")
        self.root.geometry("640x420")
        self.root.configure(bg="#1e1e1e")
        
        self.machine_seed = HardwareAuth.get_machine_fingerprint()
        self.engine = FastStegoEngine()
        
        if not os.path.exists("key_2_dictionary.json"):
            self.engine.generate_dictionary(self.machine_seed)

        self.progress = tk.DoubleVar(value=0.0)
        self.progress_bar = None
        self.status_var = tk.StringVar(value="Ready.")
        self._worker = None
        
        self.setup_ui()


    def setup_ui(self):
        title = tk.Label(self.root, text="Captain Fractal Studio", font=("Helvetica", 20, "bold"), bg="#1e1e1e", fg="#00ffcc")
        title.pack(pady=16)

        hw_label = tk.Label(self.root, text=f"Locked to Machine ID: {self.machine_seed[:16]}...", bg="#1e1e1e", fg="#aaaaaa")
        hw_label.pack(pady=4)

        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress, maximum=1.0, length=520)
        self.progress_bar.pack(pady=12)

        btn_frame = tk.Frame(self.root, bg="#1e1e1e")
        btn_frame.pack(pady=14)

        btn_encrypt = tk.Button(btn_frame, text="Encrypt a File", font=("Helvetica", 14), bg="#333333", fg="white", width=18, command=self.encrypt_action)
        btn_encrypt.grid(row=0, column=0, padx=12, pady=10)

        btn_decrypt = tk.Button(btn_frame, text="Decrypt an Archive", font=("Helvetica", 14), bg="#333333", fg="white", width=18, command=self.decrypt_action)
        btn_decrypt.grid(row=0, column=1, padx=12, pady=10)

        self.status = tk.Label(self.root, textvariable=self.status_var, bg="#1e1e1e", fg="#00ffcc", wraplength=580, justify="center")
        self.status.pack(pady=18)

        note = tk.Label(self.root, text="Drag-and-drop not yet supported; use the dialogs above.", bg="#1e1e1e", fg="#666666")
        note.pack(pady=(0, 12))

    def _set_busy(self, busy: bool):
        state = "normal" if not busy else "disabled"
        for child in self.root.winfo_children():
            try:
                child.configure(state=state)
            except Exception:
                pass

    def _start_worker(self, target, on_done, *args):
        if self._worker and self._worker.is_alive():
            messagebox.showinfo("Busy", "Please wait for the current operation to finish.")
            return
        self._set_busy(True)
        self.progress.set(0.0)
        self.status_var.set("Working...")
        self.root.update_idletasks()
        self._worker = WorkerThread(
            target=target,
            args=args,
            on_done=on_done,
        )
        self._worker.start()
        self._poll_worker()

    def _poll_worker(self):
        if self._worker and self._worker.is_alive():
            self.root.after(200, self._poll_worker)
            return
        self._set_busy(False)
        if not self._worker:
            return
        if self._worker.error:
            self.status_var.set("Operation failed.")
            messagebox.showerror("Error", str(self._worker.error))
            return
        if self._worker.result and hasattr(self._worker, "_success_text"):
            self.status_var.set(self._worker._success_text)
            messagebox.showinfo("Success", getattr(self._worker, "_success_detail", "Done."))

    def encrypt_action(self):
        src = filedialog.askopenfilename(title="Select File to Encrypt")
        if not src:
            return

        dst = filedialog.asksaveasfilename(
            title="Save Encrypted Archive As",
            defaultextension=".captain.zip",
            initialfile=os.path.basename(src) + ".captain.zip",
            filetypes=[("Captain Archive", "*.captain.zip")],
        )
        if not dst:
            return

        def task(src=src, dst=dst):
            def progress(p):
                self.progress.set(max(self.progress.get(), min(1.0, p)))
            return self.engine.encrypt_and_package(src, self.machine_seed, output_path=dst, progress_callback=progress)

        def on_done(worker):
            if worker.error:
                return
            worker._success_text = f"Saved secure archive:\n{dst}"
            worker._success_detail = "File successfully encrypted into a fractal and packaged."

        self._start_worker(task, on_done)

    def decrypt_action(self):
        src = filedialog.askopenfilename(title="Select .captain.zip Archive", filetypes=[("Captain Archive", "*.captain.zip")])
        if not src:
            return

        suggested = os.path.basename(src).replace(".captain.zip", "_RESTORED")
        dst = filedialog.asksaveasfilename(
            title="Save Decrypted File As",
            initialfile=suggested,
        )
        if not dst:
            return

        def task(src=src, dst=dst):
            def progress(p):
                self.progress.set(max(self.progress.get(), min(1.0, p)))
            return self.engine.decrypt_and_extract(src, self.machine_seed, output_path=dst, progress_callback=progress)

        def on_done(worker):
            if worker.error:
                return
            worker._success_text = f"Decrypted file restored to:\n{dst}"
            worker._success_detail = "Decryption complete. Data successfully extracted from fractal."

        self._start_worker(task, on_done)


if __name__ == "__main__":
    root = tk.Tk()
    app = CaptainFractalGUI(root)
    root.mainloop()
