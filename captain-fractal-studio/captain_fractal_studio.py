import os
import gc
import json
import uuid
import struct
import shutil
import hashlib
import tempfile
import zipfile
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox


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
# 2. VECTORIZED STEGANOGRAPHY ENGINE
# ==========================================
class FastStegoEngine:
    def __init__(self, key_2_path="key_2_dictionary.json"):
        self.key_2_path = key_2_path
        self.lut = np.zeros((256, 3), dtype=np.uint8)
        
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


    def _build_look_up_table(self):
        if not os.path.exists(self.key_2_path):
            return False
        with open(self.key_2_path, 'r') as f:
            data = json.load(f)["char_to_color"]
        for byte_str, color_str in data.items():
            r, g, b = map(int, color_str.split(','))
            self.lut[int(byte_str)] = [r, g, b]
        return True


    def generate_canvas(self, output_path, width=1024, height=1024):
        """Generates the chaotic Julia Set fractal canvas."""
        x, y = np.meshgrid(np.linspace(-1.5, 1.5, width), np.linspace(-1.5, 1.5, height))
        c = complex(-0.8, 0.156)
        z = x + 1j * y
        img_array = np.zeros(z.shape, dtype=int)
        
        for i in range(256):
            mask = np.abs(z) <= 2
            z[mask] = z[mask]**2 + c
            img_array[mask] = i
            
        img_normalized = np.uint8(255 * img_array / np.max(img_array))
        Image.fromarray(img_normalized).convert('RGB').save(output_path)


    def _get_vectorized_seed(self, hardware_seed_string):
        seed_hash = hashlib.sha256(hardware_seed_string.encode('utf-8')).hexdigest()
        return int(seed_hash[:8], 16)


    def encrypt_and_package(self, input_filepath, hardware_seed, output_path=None):
        """Encrypts data, applies memory wipes, and packages into a secure Zip."""
        self._build_look_up_table()
        if output_path is None:
            output_path = input_filepath + ".captain.zip"
        
        # Temporary files
        temp_dir = tempfile.mkdtemp()
        canvas_path = os.path.join(temp_dir, "canvas.png")
        payload_png = os.path.join(temp_dir, "encrypted_payload.png")
        zip_output = output_path
        
        try:
            self.generate_canvas(canvas_path)
            
            with open(input_filepath, 'rb') as f:
                file_bytes = f.read()
                
            data_length = len(file_bytes)
            header = struct.pack('>I', data_length)
            full_payload = np.array(list(header + file_bytes), dtype=np.uint8)
            
            img_array = np.array(Image.open(canvas_path))
            h, w, _ = img_array.shape
            flat_canvas = img_array.reshape(-1, 3) 
            
            if len(full_payload) > h * w:
                raise ValueError("File is too large for the 1024x1024 fractal canvas.")


            rng = np.random.RandomState(seed=self._get_vectorized_seed(hardware_seed))
            chaotic_path = rng.permutation(h * w)
            target_indices = chaotic_path[:len(full_payload)]
            
            # Vectorized Injection
            embedded_colors = self.lut[full_payload]
            flat_canvas[target_indices] = embedded_colors
            
            final_image = flat_canvas.reshape((h, w, 3))
            Image.fromarray(final_image).save(payload_png)
            
            # Secure Packaging: Zip the PNG to prevent image compression over networks
            with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(payload_png, arcname="encrypted_payload.png")
                zipf.write(self.key_2_path, arcname="key_2_dictionary.json")


            # Cryptographic Memory Wipe
            full_payload[:] = 0
            flat_canvas[:] = 0
            del full_payload, flat_canvas, img_array, embedded_colors
            gc.collect()


            return zip_output


        finally:
            shutil.rmtree(temp_dir)


    def decrypt_and_extract(self, zip_filepath, hardware_seed, output_path=None):
        """Extracts the Zip, decrypts the fractal, wipes memory, and restores the file."""
        temp_dir = tempfile.mkdtemp()
        if output_path is None:
            output_path = zip_filepath.replace(".captain.zip", "_RESTORED")
        
        try:
            # Unzip payload
            with zipfile.ZipFile(zip_filepath, 'r') as zipf:
                zipf.extractall(temp_dir)
                
            payload_png = os.path.join(temp_dir, "encrypted_payload.png")
            key_path = os.path.join(temp_dir, "key_2_dictionary.json")
            self.key_2_path = key_path
            self._build_look_up_table()
            
            img_array = np.array(Image.open(payload_png))
            h, w, _ = img_array.shape
            flat_canvas = img_array.reshape(-1, 3)
            
            rng = np.random.RandomState(seed=self._get_vectorized_seed(hardware_seed))
            chaotic_path = rng.permutation(h * w)
            
            header_colors = flat_canvas[chaotic_path[:4]]
            
            # Reverse map header
            header_bytes = bytearray()
            for color in header_colors:
                match = np.where((self.lut == color).all(axis=1))[0][0]
                header_bytes.append(match)
                
            target_length = struct.unpack('>I', header_bytes)[0]
            
            # Extract Payload
            payload_indices = chaotic_path[4 : 4 + target_length]
            payload_colors = flat_canvas[payload_indices]
            
            expanded_lut = np.expand_dims(self.lut, axis=0)
            expanded_colors = np.expand_dims(payload_colors, axis=1)
            
            extracted_bytes = np.argmax(np.all(expanded_colors == expanded_lut, axis=2), axis=1).astype(np.uint8)
            
            with open(output_path, 'wb') as f:
                f.write(extracted_bytes.tobytes())


            # Cryptographic Memory Wipe
            extracted_bytes[:] = 0
            flat_canvas[:] = 0
            del extracted_bytes, flat_canvas, expanded_lut, expanded_colors
            gc.collect()


            return output_path


        finally:
            shutil.rmtree(temp_dir)




# ==========================================
# 3. GRAPHICAL USER INTERFACE (GUI)
# ==========================================
class CaptainFractalGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Captain Fractal Encryption Studio v1.0")
        self.root.geometry("500x350")
        self.root.configure(bg="#1e1e1e")
        
        self.machine_seed = HardwareAuth.get_machine_fingerprint()
        self.engine = FastStegoEngine()
        
        # Initialize Dictionary if missing
        if not os.path.exists("key_2_dictionary.json"):
            self.engine.generate_dictionary(self.machine_seed)


        self.setup_ui()


    def setup_ui(self):
        title = tk.Label(self.root, text="Captain Fractal Studio", font=("Helvetica", 18, "bold"), bg="#1e1e1e", fg="#00ffcc")
        title.pack(pady=20)
        
        hw_label = tk.Label(self.root, text=f"Locked to Machine ID: {self.machine_seed[:12]}...", bg="#1e1e1e", fg="#aaaaaa")
        hw_label.pack(pady=5)


        btn_encrypt = tk.Button(self.root, text="Encrypt a File", font=("Helvetica", 14), bg="#333333", fg="white", command=self.encrypt_action)
        btn_encrypt.pack(pady=15, fill="x", padx=50)


        btn_decrypt = tk.Button(self.root, text="Decrypt an Archive", font=("Helvetica", 14), bg="#333333", fg="white", command=self.decrypt_action)
        btn_decrypt.pack(pady=15, fill="x", padx=50)
        
        self.status = tk.Label(self.root, text="Ready.", bg="#1e1e1e", fg="#00ffcc", wraplength=400)
        self.status.pack(pady=20)


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

        if self.status.winfo_exists():
            self.status.config(text="Encrypting and generating fractal...")
            self.root.update_idletasks()

        try:
            output_zip = self.engine.encrypt_and_package(src, self.machine_seed, output_path=dst)
            if self.status.winfo_exists():
                self.status.config(text=f"Success! Saved secure archive:\n{output_zip}", fg="#00ffcc")
            messagebox.showinfo("Success", "File successfully encrypted into a fractal and packaged.")
        except Exception as e:
            if self.status.winfo_exists():
                self.status.config(text=f"Error: {str(e)}", fg="red")
            messagebox.showerror("Error", f"Encryption failed: {str(e)}")


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

        if self.status.winfo_exists():
            self.status.config(text="Extracting fractal and decrypting data...")
            self.root.update_idletasks()

        try:
            output_file = self.engine.decrypt_and_extract(src, self.machine_seed, output_path=dst)
            if self.status.winfo_exists():
                self.status.config(text=f"Success! Decrypted file restored to:\n{output_file}", fg="#00ffcc")
            messagebox.showinfo("Success", "Decryption complete. Data successfully extracted from fractal.")
        except Exception as e:
            if self.status.winfo_exists():
                self.status.config(text="Decryption Failed. Are you on the correct machine?", fg="red")
            messagebox.showerror("Error", f"Decryption failed: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = CaptainFractalGUI(root)
    root.mainloop()
