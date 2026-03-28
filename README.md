# 🎯 FaceTracker

> Realtids ansiktsdetektering, tracking och galleri — ett skolprojekt i Python.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)
![OpenCV](https://img.shields.io/badge/OpenCV-4.8%2B-green?style=flat-square&logo=opencv)
![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)
![Syfte](https://img.shields.io/badge/Syfte-Skolarbete-orange?style=flat-square)

---

## ✨ Funktioner

| Funktion | Beskrivning |
|---|---|
| 🔲 Realtidsdetektering | Ritar en färgad box runt varje ansikte i kameraflödet |
| 👤 Unika ID:n | Varje ny person får automatiskt "Person 1", "Person 2" osv. |
| 👥 Multi-face | Hanterar flera ansikten samtidigt |
| 📸 Bildgalleri | Sparar bilder per person — klicka för att se alla |
| 🔒 Lokal lagring | All data stannar på din dator, inget skickas online |

---

## 📁 Projektstruktur

```
facetracker/
├── src/
│   └── main.py          # Huvudprogrammet
├── docs/
│   └── index.html       # Projektets hemsida
├── requirements.txt     # Python-beroenden
├── .gitignore
└── README.md
```

---

## 🚀 Installation

### Förkrav
- Python **3.8–3.11** (3.12+ kan ha problem med dlib)
- Webbkamera

### 1. Klona repot

```bash
git clone https://github.com/DITT-ANVÄNDARNAMN/facetracker.git
cd facetracker
```

### 2. Skapa virtuell miljö

```bash
python -m venv venv

# Mac/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Installera beroenden

```bash
pip install -r requirements.txt
```

> **⚠️ Windows-användare:** `dlib` kräver [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/).
> Om installationen misslyckas, ladda ner ett förbyggt hjul från [z-mahmud22/Dlib_Windows_Python3.x](https://github.com/z-mahmud22/Dlib_Windows_Python3.x) och installera det manuellt:
> ```bash
> pip install dlib-19.24.1-cp310-cp310-win_amd64.whl
> ```

### 4. Starta

```bash
python src/main.py
```

---

## 🎮 Användning

1. Klicka **▶ STARTA KAMERA** — webbkameran aktiveras
2. Ansikten detekteras automatiskt och markeras med färgade boxar
3. Varje unik person får ett eget ID och färg
4. Galleriet längst ner visar alla detekterade personer
5. Klicka på en persons miniatyrbild för att se alla sparade bilder
6. **■ STOPPA** stänger kameran — **🗑 RENSA ALLT** nollställer sessionen

---

## ⚙️ Konfiguration

Ändra dessa konstanter i toppen av `src/main.py`:

| Konstant | Standard | Beskrivning |
|---|---|---|
| `CAPTURE_INTERVAL` | `2.0` | Sekunder mellan sparade bilder per person |
| `TOLERANCE` | `0.55` | Matchningsstrikthet (lägre = striktare) |
| `FRAME_SCALE` | `0.5` | Skalfaktor för detektering (lägre = snabbare) |
| `UNKNOWN_THRESHOLD` | `3` | Frames innan ny person bekräftas |
| `MAX_THUMBNAILS` | `20` | Max sparade bilder per person |

---

## 🔬 Teknisk översikt

```
Kameraframe
     │
     ▼
  Nedskalning (FRAME_SCALE)
     │
     ▼
  face_locations()  ◄── HOG-detektor (dlib)
     │
     ▼
  face_encodings()  ◄── 128-dim vektor per ansikte
     │
     ▼
  face_distance()   ◄── Jämför mot kända encodings
     │
  ┌──┴──────────┐
  │             │
Match < 0.55   Ny person (buffras 3 frames)
  │             │
  ▼             ▼
Rita box     Skapa FacePerson + ID
  │
  ▼
Spara bild (var 2:a sekund)
```

---

## 🔒 Integritet & etik

- **Lokal lagring** — inga bilder eller encodings skickas till internet
- **Temporär data** — `captured_faces/` ignoreras av git (se `.gitignore`)
- **Skolbruk** — programmet är enbart avsett som ett utbildningsprojekt
- Radera mappen `captured_faces/` lokalt för att ta bort all sparad data

---

## 🛠 Felsökning

| Problem | Lösning |
|---|---|
| `ModuleNotFoundError: dlib` | Installera Visual Studio Build Tools (Windows) |
| Kameran öppnas inte | Prova `cv2.VideoCapture(1)` istället för `0` |
| Långsam detektering | Sänk `FRAME_SCALE` till `0.35` |
| För många falska nya personer | Sänk `TOLERANCE` till `0.50` |
| Samma person får flera ID:n | Höj `TOLERANCE` till `0.60` |

---

## 📄 Licens

MIT — se [LICENSE](LICENSE) för detaljer.

---

*Skolprojekt — all insamlad data är temporär och lagras enbart lokalt.*
