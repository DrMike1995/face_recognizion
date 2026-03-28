import cv2
import face_recognition
import numpy as np
import os
import time
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from collections import defaultdict
import threading

# ── Konfiguration ──────────────────────────────────────────────
CAPTURE_INTERVAL   = 2.0      # sekunder mellan auto-sparade bilder per person
MAX_THUMBNAILS     = 20       # max sparade bilder per person
THUMBNAIL_SIZE     = (80, 80) # storlek på miniatyrbilder i galleriet
FRAME_SCALE        = 0.5      # skala för ansiktsdetektering (snabbare)
TOLERANCE          = 0.55     # hur strikt matchning (lägre = striktare)
UNKNOWN_THRESHOLD  = 3        # antal frames innan ny person får ID
BOX_COLORS = [
    (0, 200, 100), (0, 140, 255), (200, 0, 200),
    (0, 200, 200), (255, 100, 0), (100, 0, 255),
]

SAVE_DIR = "captured_faces"
os.makedirs(SAVE_DIR, exist_ok=True)


class FacePerson:
    """Representerar en unik person som detekterats."""
    def __init__(self, person_id: int, encoding: np.ndarray):
        self.id           = person_id
        self.label        = f"Person {person_id}"
        self.encodings    = [encoding]
        self.images       = []
        self.last_capture = 0.0
        self.color        = BOX_COLORS[(person_id - 1) % len(BOX_COLORS)]
        self.seen_frames  = 0

    @property
    def mean_encoding(self):
        return np.mean(self.encodings, axis=0)

    def add_encoding(self, enc):
        self.encodings.append(enc)
        if len(self.encodings) > 30:
            self.encodings.pop(0)

    def save_image(self, face_img: np.ndarray):
        now = time.time()
        if now - self.last_capture < CAPTURE_INTERVAL:
            return
        self.last_capture = now
        pil_img = Image.fromarray(cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB))
        pil_img = pil_img.resize(THUMBNAIL_SIZE, Image.LANCZOS)
        self.images.append(pil_img)
        if len(self.images) > MAX_THUMBNAILS:
            self.images.pop(0)
        person_dir = os.path.join(SAVE_DIR, f"person_{self.id}")
        os.makedirs(person_dir, exist_ok=True)
        fname = os.path.join(person_dir, f"{int(now*1000)}.jpg")
        pil_img.save(fname)


class FaceTrackerApp:
    def __init__(self, root: tk.Tk):
        self.root    = root
        self.root.title("Face Tracker — Skolprojekt")
        self.root.configure(bg="#0d0d0d")
        self.root.resizable(True, True)

        self.persons: dict[int, FacePerson] = {}
        self.next_id  = 1
        self.running  = False
        self.cap      = None
        self.lock     = threading.Lock()
        self.pending: list[dict] = []

        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self.root, bg="#0d0d0d")
        top.pack(fill=tk.BOTH, expand=True, padx=12, pady=(12, 6))

        self.canvas = tk.Canvas(top, width=800, height=600,
                                bg="#111", highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        side = tk.Frame(top, bg="#181818", width=220)
        side.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        side.pack_propagate(False)

        tk.Label(side, text="LIVE STATS", font=("Courier", 11, "bold"),
                 fg="#00ff88", bg="#181818").pack(pady=(14, 4))

        self.stats_text = tk.Text(side, bg="#181818", fg="#cccccc",
                                  font=("Courier", 10), bd=0, state=tk.DISABLED,
                                  width=24, height=20)
        self.stats_text.pack(padx=8, fill=tk.BOTH, expand=True)

        bottom_wrap = tk.Frame(self.root, bg="#0d0d0d")
        bottom_wrap.pack(fill=tk.X, padx=12, pady=(0, 12))

        tk.Label(bottom_wrap, text="DETEKTERADE ANSIKTEN",
                 font=("Courier", 10, "bold"), fg="#888", bg="#0d0d0d"
                 ).pack(anchor="w", pady=(0, 4))

        gallery_outer = tk.Frame(bottom_wrap, bg="#111", height=160)
        gallery_outer.pack(fill=tk.X)
        gallery_outer.pack_propagate(False)

        self.gallery_canvas = tk.Canvas(gallery_outer, bg="#111",
                                        highlightthickness=0, height=150)
        scrollbar = ttk.Scrollbar(gallery_outer, orient=tk.HORIZONTAL,
                                  command=self.gallery_canvas.xview)
        self.gallery_canvas.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.gallery_canvas.pack(fill=tk.BOTH, expand=True)

        self.gallery_frame = tk.Frame(self.gallery_canvas, bg="#111")
        self.gallery_window = self.gallery_canvas.create_window(
            (0, 0), window=self.gallery_frame, anchor="nw")
        self.gallery_frame.bind("<Configure>", self._on_gallery_resize)

        btn_frame = tk.Frame(self.root, bg="#0d0d0d")
        btn_frame.pack(pady=(0, 8))

        self.start_btn = tk.Button(btn_frame, text="▶  STARTA KAMERA",
                                   command=self.start, font=("Courier", 11, "bold"),
                                   bg="#00ff88", fg="#000", relief=tk.FLAT,
                                   padx=20, pady=8, cursor="hand2")
        self.start_btn.pack(side=tk.LEFT, padx=6)

        self.stop_btn = tk.Button(btn_frame, text="■  STOPPA",
                                  command=self.stop, font=("Courier", 11, "bold"),
                                  bg="#ff4444", fg="#fff", relief=tk.FLAT,
                                  padx=20, pady=8, cursor="hand2", state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=6)

        tk.Button(btn_frame, text="🗑  RENSA ALLT",
                  command=self.clear_all, font=("Courier", 11),
                  bg="#333", fg="#aaa", relief=tk.FLAT,
                  padx=16, pady=8, cursor="hand2").pack(side=tk.LEFT, padx=6)

    def _on_gallery_resize(self, _event):
        self.gallery_canvas.configure(
            scrollregion=self.gallery_canvas.bbox("all"))

    def start(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[FaceTracker] Kunde inte öppna kameran!")
            return
        self.running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        threading.Thread(target=self._process_loop, daemon=True).start()
        self._update_canvas()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)

    def clear_all(self):
        with self.lock:
            self.persons.clear()
            self.next_id = 1
            self.pending.clear()
        for widget in self.gallery_frame.winfo_children():
            widget.destroy()
        self._update_stats()

    def _process_loop(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                break

            small     = cv2.resize(frame, (0, 0), fx=FRAME_SCALE, fy=FRAME_SCALE)
            rgb_small = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locations = face_recognition.face_locations(rgb_small, model="hog")
            encodings = face_recognition.face_encodings(rgb_small, locations)

            matched_ids = []
            with self.lock:
                for enc, loc in zip(encodings, locations):
                    person = self._match_or_create(enc)
                    if person is None:
                        matched_ids.append(None)
                        continue
                    person.seen_frames += 1
                    person.add_encoding(enc)
                    top, right, bottom, left = [int(v / FRAME_SCALE) for v in loc]
                    face_crop = frame[top:bottom, left:right]
                    if face_crop.size > 0:
                        person.save_image(face_crop)
                    matched_ids.append((person, top, right, bottom, left))

            annotated = frame.copy()
            for item in matched_ids:
                if item is None:
                    continue
                person, top, right, bottom, left = item
                color = person.color
                cv2.rectangle(annotated, (left, top), (right, bottom), color, 2)
                label_bg_y = top - 28 if top > 30 else bottom
                cv2.rectangle(annotated,
                              (left, label_bg_y),
                              (left + len(person.label) * 12 + 12, label_bg_y + 26),
                              color, -1)
                cv2.putText(annotated, person.label,
                            (left + 6, label_bg_y + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)

            self._current_frame = annotated
            self._update_stats()

    def _match_or_create(self, encoding: np.ndarray):
        if self.persons:
            known_encs = [p.mean_encoding for p in self.persons.values()]
            known_ids  = list(self.persons.keys())
            distances  = face_recognition.face_distance(known_encs, encoding)
            best_idx   = int(np.argmin(distances))
            if distances[best_idx] < TOLERANCE:
                return self.persons[known_ids[best_idx]]

        for p in self.pending:
            dist = face_recognition.face_distance([p["enc"]], encoding)[0]
            if dist < TOLERANCE:
                p["count"] += 1
                p["enc"] = np.mean([p["enc"], encoding], axis=0)
                if p["count"] >= UNKNOWN_THRESHOLD:
                    self.pending.remove(p)
                    person = FacePerson(self.next_id, p["enc"])
                    self.persons[self.next_id] = person
                    self.next_id += 1
                    self.root.after(0, self._rebuild_gallery)
                    return person
                return None

        self.pending.append({"enc": encoding.copy(), "count": 1})
        return None

    _current_frame = None

    def _update_canvas(self):
        if self.running and self._current_frame is not None:
            frame = self._current_frame
            h, w  = frame.shape[:2]
            cw = self.canvas.winfo_width()  or 800
            ch = self.canvas.winfo_height() or 600
            scale = min(cw / w, ch / h)
            nw, nh = int(w * scale), int(h * scale)
            resized = cv2.resize(frame, (nw, nh))
            rgb     = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            img     = ImageTk.PhotoImage(Image.fromarray(rgb))
            self.canvas.create_image(cw // 2, ch // 2, image=img, anchor=tk.CENTER)
            self.canvas._img = img
        if self.running:
            self.root.after(30, self._update_canvas)

    def _update_stats(self):
        self.root.after(0, self._draw_stats)

    def _draw_stats(self):
        with self.lock:
            lines = [f"Aktiva: {len(self.persons)} person(er)\n"]
            for p in self.persons.values():
                lines.append(f"  {p.label}")
                lines.append(f"  Bilder: {len(p.images)}\n")
        text = "\n".join(lines)
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete("1.0", tk.END)
        self.stats_text.insert(tk.END, text)
        self.stats_text.config(state=tk.DISABLED)

    def _rebuild_gallery(self):
        for w in self.gallery_frame.winfo_children():
            w.destroy()
        with self.lock:
            persons_copy = list(self.persons.values())
        for person in persons_copy:
            self._add_person_column(person)
        self.gallery_canvas.configure(
            scrollregion=self.gallery_canvas.bbox("all"))

    def _add_person_column(self, person: FacePerson):
        col = tk.Frame(self.gallery_frame, bg="#1a1a1a", relief=tk.FLAT, bd=1)
        col.pack(side=tk.LEFT, padx=6, pady=6, fill=tk.Y)
        hex_color = "#{:02x}{:02x}{:02x}".format(*person.color[::-1])
        tk.Label(col, text=person.label, font=("Courier", 9, "bold"),
                 fg=hex_color, bg="#1a1a1a").pack(pady=(4, 2))
        btn = tk.Button(col, text="Visa bilder",
                        font=("Courier", 8), bg="#222", fg="#aaa",
                        relief=tk.FLAT, cursor="hand2",
                        command=lambda p=person: self._open_gallery(p))
        btn.pack(pady=(0, 4), padx=6)
        self._update_person_thumbnail(col, person)

    def _update_person_thumbnail(self, frame: tk.Frame, person: FacePerson):
        if not person.images:
            return
        img   = person.images[-1].resize((70, 70), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        lbl   = tk.Label(frame, image=photo, bg="#1a1a1a", cursor="hand2")
        lbl.image = photo
        lbl.pack(padx=6, pady=(0, 6))
        lbl.bind("<Button-1>", lambda e, p=person: self._open_gallery(p))

    def _open_gallery(self, person: FacePerson):
        win = tk.Toplevel(self.root)
        win.title(f"Bilder — {person.label}")
        win.configure(bg="#0d0d0d")
        win.geometry("600x400")
        hex_color = "#{:02x}{:02x}{:02x}".format(*person.color[::-1])
        tk.Label(win, text=f"● {person.label}",
                 font=("Courier", 13, "bold"),
                 fg=hex_color, bg="#0d0d0d").pack(pady=(14, 8))
        tk.Label(win, text=f"{len(person.images)} sparade bilder",
                 font=("Courier", 9), fg="#555", bg="#0d0d0d").pack()
        container = tk.Frame(win, bg="#0d0d0d")
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        canvas = tk.Canvas(container, bg="#0d0d0d", highlightthickness=0)
        vsb    = ttk.Scrollbar(container, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        inner = tk.Frame(canvas, bg="#0d0d0d")
        canvas.create_window((0, 0), window=inner, anchor="nw")
        COLS = 6
        with self.lock:
            imgs = list(person.images)
        photo_refs = []
        for i, pil_img in enumerate(imgs):
            big   = pil_img.resize((88, 88), Image.LANCZOS)
            photo = ImageTk.PhotoImage(big)
            photo_refs.append(photo)
            lbl   = tk.Label(inner, image=photo, bg="#111", relief=tk.FLAT, bd=2)
            lbl.grid(row=i // COLS, column=i % COLS, padx=4, pady=4)
        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))
        win._photo_refs = photo_refs


if __name__ == "__main__":
    root = tk.Tk()
    app  = FaceTrackerApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: (app.stop(), root.destroy()))
    root.mainloop()
