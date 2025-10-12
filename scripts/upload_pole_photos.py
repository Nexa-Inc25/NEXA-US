#!/usr/bin/env python3
"""
Upload Utility for Real Utility Pole Photos
Helps organize and prepare your actual pole photos for YOLO training
"""

import os
import shutil
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
from PIL import Image
import hashlib

class PolePhotoUploader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("NEXA Pole Photo Uploader")
        self.root.geometry("700x600")
        self.root.configure(bg="#f0f0f0")
        
        # Destination folder
        self.dest_folder = Path("sample_pole_images")
        self.dest_folder.mkdir(exist_ok=True)
        
        # Statistics
        self.uploaded_count = 0
        self.existing_images = []
        
        self.setup_ui()
        self.update_stats()
    
    def setup_ui(self):
        # Title
        title = tk.Label(self.root, text="🎯 NEXA YOLO Training Photo Uploader", 
                        font=("Arial", 18, "bold"), bg="#f0f0f0")
        title.pack(pady=20)
        
        # Info frame
        info_frame = tk.Frame(self.root, bg="#e0e0e0", relief=tk.RAISED, bd=2)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_text = """Upload your utility pole photos for YOLO training.
        
        📸 IDEAL PHOTOS SHOULD INCLUDE:
        • Clear utility poles (wood, steel, or concrete)
        • Crossarms and insulators visible
        • Transformers and guy wires
        • Various angles and lighting conditions
        • Both closeup and distance shots
        • Any safety infractions or issues
        
        Supported formats: JPG, JPEG, PNG, BMP"""
        
        tk.Label(info_frame, text=info_text, justify=tk.LEFT, bg="#e0e0e0",
                font=("Arial", 10)).pack(padx=10, pady=10)
        
        # Stats frame
        stats_frame = tk.Frame(self.root, bg="#f0f0f0")
        stats_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.stats_label = tk.Label(stats_frame, text="", font=("Arial", 12), bg="#f0f0f0")
        self.stats_label.pack()
        
        # Buttons frame
        button_frame = tk.Frame(self.root, bg="#f0f0f0")
        button_frame.pack(pady=20)
        
        # Upload single photo button
        single_btn = tk.Button(button_frame, text="📷 Upload Single Photo",
                              command=self.upload_single, width=20, height=2,
                              bg="#4CAF50", fg="white", font=("Arial", 11, "bold"))
        single_btn.grid(row=0, column=0, padx=10)
        
        # Upload multiple photos button
        multi_btn = tk.Button(button_frame, text="📁 Upload Multiple Photos",
                             command=self.upload_multiple, width=20, height=2,
                             bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
        multi_btn.grid(row=0, column=1, padx=10)
        
        # Upload folder button
        folder_btn = tk.Button(button_frame, text="📂 Upload Entire Folder",
                              command=self.upload_folder, width=20, height=2,
                              bg="#FF9800", fg="white", font=("Arial", 11, "bold"))
        folder_btn.grid(row=1, column=0, padx=10, pady=10)
        
        # View uploaded button
        view_btn = tk.Button(button_frame, text="👁️ View Uploaded Photos",
                            command=self.view_uploaded, width=20, height=2,
                            bg="#9C27B0", fg="white", font=("Arial", 11, "bold"))
        view_btn.grid(row=1, column=1, padx=10, pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.root, length=400, mode='determinate')
        self.progress.pack(pady=10)
        
        # Status text
        self.status_text = tk.Text(self.root, height=8, width=80, bg="#f9f9f9")
        self.status_text.pack(padx=20, pady=10)
        
        # Start training button
        train_btn = tk.Button(self.root, text="🚀 Start YOLO Training",
                             command=self.start_training, height=2,
                             bg="#F44336", fg="white", font=("Arial", 12, "bold"))
        train_btn.pack(pady=10, fill=tk.X, padx=100)
    
    def update_stats(self):
        """Update statistics display"""
        existing = list(self.dest_folder.glob("*.jpg"))
        existing.extend(list(self.dest_folder.glob("*.png")))
        self.existing_images = existing
        
        stats_text = f"📊 Current Dataset: {len(self.existing_images)} images"
        if len(self.existing_images) < 20:
            stats_text += " (⚠️ Need at least 20 for good training)"
        elif len(self.existing_images) < 50:
            stats_text += " (🔶 More images = better accuracy)"
        else:
            stats_text += " (✅ Good dataset size!)"
        
        self.stats_label.config(text=stats_text)
    
    def validate_image(self, file_path):
        """Validate image file"""
        try:
            # Check if it's a valid image
            img = Image.open(file_path)
            img.verify()
            
            # Check dimensions
            img = Image.open(file_path)
            width, height = img.size
            
            if width < 200 or height < 200:
                return False, "Image too small (min 200x200)"
            
            if width > 4000 or height > 4000:
                return False, "Image too large (max 4000x4000)"
            
            return True, "Valid"
        except:
            return False, "Invalid image file"
    
    def copy_image(self, source_path):
        """Copy image to destination with unique name"""
        source = Path(source_path)
        
        # Generate hash for duplicate detection
        with open(source, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        
        # Create unique filename
        dest_name = f"pole_{file_hash}_{source.name}"
        dest_path = self.dest_folder / dest_name
        
        # Check if already exists
        if dest_path.exists():
            return False, "Duplicate image"
        
        # Copy file
        shutil.copy2(source, dest_path)
        return True, dest_path
    
    def upload_single(self):
        """Upload single photo"""
        file_path = filedialog.askopenfilename(
            title="Select Utility Pole Photo",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            valid, msg = self.validate_image(file_path)
            if valid:
                success, dest = self.copy_image(file_path)
                if success:
                    self.log_message(f"✅ Uploaded: {Path(file_path).name}")
                    self.uploaded_count += 1
                else:
                    self.log_message(f"⚠️ Skipped (duplicate): {Path(file_path).name}")
            else:
                self.log_message(f"❌ Invalid: {Path(file_path).name} - {msg}")
            
            self.update_stats()
    
    def upload_multiple(self):
        """Upload multiple photos"""
        file_paths = filedialog.askopenfilenames(
            title="Select Multiple Utility Pole Photos",
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp"),
                ("All files", "*.*")
            ]
        )
        
        if file_paths:
            self.progress['maximum'] = len(file_paths)
            self.progress['value'] = 0
            
            for i, file_path in enumerate(file_paths):
                valid, msg = self.validate_image(file_path)
                if valid:
                    success, dest = self.copy_image(file_path)
                    if success:
                        self.log_message(f"✅ [{i+1}/{len(file_paths)}] Uploaded: {Path(file_path).name}")
                        self.uploaded_count += 1
                    else:
                        self.log_message(f"⚠️ [{i+1}/{len(file_paths)}] Skipped (duplicate)")
                else:
                    self.log_message(f"❌ [{i+1}/{len(file_paths)}] Invalid: {msg}")
                
                self.progress['value'] = i + 1
                self.root.update()
            
            self.update_stats()
            messagebox.showinfo("Upload Complete", 
                               f"Processed {len(file_paths)} files\n"
                               f"Successfully uploaded: {self.uploaded_count}")
    
    def upload_folder(self):
        """Upload entire folder of photos"""
        folder_path = filedialog.askdirectory(title="Select Folder with Pole Photos")
        
        if folder_path:
            folder = Path(folder_path)
            image_files = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.bmp']:
                image_files.extend(folder.glob(ext))
            
            if not image_files:
                messagebox.showwarning("No Images", "No image files found in selected folder")
                return
            
            self.progress['maximum'] = len(image_files)
            self.progress['value'] = 0
            uploaded = 0
            
            for i, img_path in enumerate(image_files):
                valid, msg = self.validate_image(img_path)
                if valid:
                    success, dest = self.copy_image(img_path)
                    if success:
                        self.log_message(f"✅ [{i+1}/{len(image_files)}] {img_path.name}")
                        uploaded += 1
                    else:
                        self.log_message(f"⚠️ [{i+1}/{len(image_files)}] Duplicate")
                else:
                    self.log_message(f"❌ [{i+1}/{len(image_files)}] {msg}")
                
                self.progress['value'] = i + 1
                self.root.update()
            
            self.update_stats()
            messagebox.showinfo("Folder Upload Complete",
                               f"Processed {len(image_files)} files\n"
                               f"Successfully uploaded: {uploaded}")
    
    def view_uploaded(self):
        """Open folder with uploaded images"""
        os.startfile(self.dest_folder)
    
    def log_message(self, message):
        """Add message to status text"""
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
    
    def start_training(self):
        """Start YOLO training with uploaded images"""
        if len(self.existing_images) < 10:
            messagebox.showwarning("Not Enough Images", 
                                  f"You need at least 10 images for training.\n"
                                  f"Currently have: {len(self.existing_images)}")
            return
        
        response = messagebox.askyesno("Start Training",
                                       f"Ready to train YOLO with {len(self.existing_images)} images?\n\n"
                                       f"This will:\n"
                                       f"• Prepare dataset structure\n"
                                       f"• Split into train/val/test\n"
                                       f"• Start YOLO training\n"
                                       f"• May take 30 min to several hours")
        
        if response:
            self.root.destroy()
            # Training will be started from PowerShell script
            print(f"\n✅ Ready to train with {len(self.existing_images)} images!")
            print("Run: .\\train_yolo_complete.ps1")
    
    def run(self):
        """Run the uploader GUI"""
        self.root.mainloop()

def main():
    print("🚀 Starting NEXA Pole Photo Uploader...")
    app = PolePhotoUploader()
    app.run()

if __name__ == "__main__":
    main()
