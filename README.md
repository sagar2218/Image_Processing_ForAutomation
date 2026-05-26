# Image Processing & Screen OCR Toolkit

A Python-based screen automation toolkit that combines **OpenCV template matching** and **Tesseract OCR** to locate images and text on your screen — useful for UI automation, RPA (Robotic Process Automation), and screen scraping tasks.

---

## Features

- Find images on screen using template matching
- Extract and search text from screen regions using OCR
- Fuzzy text matching for handling OCR inaccuracies
- Locate text relative to another text (e.g. value next to a label)
- Crop and save screen regions around matched templates

---

## Requirements

### System
- Windows OS
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed at `C:/Program Files/Tesseract-OCR/tesseract.exe`

### Python Dependencies

```
numpy
pyautogui
pywin32
opencv-python
Pillow
pytesseract
```

Install all dependencies:

```bash
pip install numpy pyautogui pywin32 opencv-python Pillow pytesseract
```

---

## Setup

1. Install Tesseract OCR from [here](https://github.com/UB-Mannheim/tesseract/wiki)
2. Update the Tesseract path in `Image_processing.py` if needed:
   ```python
   pytesseract.tesseract_cmd = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
   ```
3. Update the `image_path` in `crop_image()` to your local directory

---

## Functions

### `get_converted_text(image)`
Runs Tesseract OCR on an image and returns a dictionary of detected words with their bounding box coordinates.

```python
ocr_data = get_converted_text('screenshot.png')
```

---

### `text_coordinates(pos, converted_text, key, ...)`
Finds the screen coordinates of a text string within OCR data.

| Parameter | Description |
|---|---|
| `pos` | `(x, y)` offset of the image region on screen |
| `converted_text` | OCR dictionary from `get_converted_text()` |
| `key` | Text to search for |
| `key_next` | Secondary text to find relative to `key` |
| `flag_next` | `"nextToX"` (right of) or `"nextToY"` (below) |
| `contain_flag` | Match if word *starts with* the key |
| `near_by_match` | Enable fuzzy matching (>80% similarity) |
| `zooming` | Scale factor used during image preprocessing (default: `4`) |

Returns `(screen_x, screen_y, width, height)` or `(-1, -1, -1, -1)` if not found.

```python
x, y, w, h = text_coordinates((0, 0), ocr_data, "Submit", near_by_match=True)
```

---

### `imagesearch(image, precision=0.8)`
Searches for a template image on the current screen.

```python
x, y = imagesearch('button.png', precision=0.9)
```

Returns `(x, y)` of the top-left match, or `[-1, -1]` if not found.

---

### `image_croping_template(template, height, width=None)`
Finds a template on screen and returns its bounding box for cropping.

```python
x, y, w, h = image_croping_template('header.png', height=500)
```

---

### `image_OCR(text, images)`
Locates a template image on screen, runs OCR on that region, and returns the screen coordinates of the target text.

```python
x, y = image_OCR("Invoice Total", "invoice_header.png")
```

---

### `crop_image(sample_image, width, height)`
Takes a full screenshot, finds the template, and saves a cropped region around it.

```python
x1, y1, x2, y2 = crop_image('template.png', width=200, height=100)
```

Saves:
- `screenshot.png` — full screen capture
- `cropped_result.png` — cropped region around the match

---

## Example Usage

```python
# Crop a region around a template and run OCR on it
crop_image('template.png', width=300, height=150)

ocr_data = get_converted_text('cropped_result.png')

# Find all entries starting with a specific prefix
entries = [
    {
        'text': ocr_data['text'][i].strip(),
        'left': ocr_data['left'][i],
        'top': ocr_data['top'][i],
    }
    for i, text in enumerate(ocr_data['text'])
    if text.strip().startswith("PVD-CR-2")
]

last_entry = entries[-1] if entries else None

if last_entry:
    print("Found:", last_entry['text'])
    pyautogui.click(last_entry['left'], last_entry['top'])
```

---

## Notes

- `pyautogui.FAILSAFE = False` disables the emergency stop (moving mouse to screen corner). Re-enable during development for safety.
- Fuzzy matching uses Python's `difflib.SequenceMatcher` with an 80% similarity threshold.
- Image preprocessing (grayscale + resize) improves OCR accuracy on low-resolution or small text regions.
