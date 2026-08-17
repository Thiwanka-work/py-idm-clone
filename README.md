<div align="center">
  <img src="extension/icons/icon128.png" alt="IDM Clone Logo" width="128" height="128">
  <h1>Python IDM Clone</h1>
  <p>A fast, modern Download Manager and Chrome Extension built with Python and CustomTkinter.</p>
</div>

## ✨ Features

- **Modern UI**: A sleek, dark-mode ready graphical interface powered by `CustomTkinter`.
- **Fast Downloads**: Multi-threaded downloading engine to accelerate file downloads.
- **YouTube Downloader**: Integrated YouTube video downloader with resolution selection.
- **Chrome Extension**: Seamless integration with your browser to intercept downloads and detect YouTube videos.
- **Pause/Resume**: Easily pause, resume, or cancel ongoing downloads.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Google Chrome

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Thiwanka-work/py-idm-clone.git
   cd py-idm-clone
   ```

2. **Install Python dependencies**
   ```bash
   cd app
   pip install -r requirements.txt
   ```

3. **Install the Chrome Extension**
   - Open Chrome and navigate to `chrome://extensions/`
   - Enable **Developer mode** in the top right corner.
   - Click **Load unpacked** and select the `extension` folder from this repository.

### Running the App

Start the Python backend and GUI by running:

```bash
python app/main.py
```

The application will start the Flask server on `http://localhost:6578` (for the Chrome extension to communicate with) and launch the GUI.

## 📁 Project Structure

- `app/`: Contains the Python backend (Flask), the Download Engine, and the UI.
- `extension/`: Contains the Chrome Extension source code (manifest, content scripts, background worker).

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📝 License

This project is open-source and free to use.
