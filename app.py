from flask import Flask, render_template_string, request, jsonify, send_file, Response
import yt_dlp
import os
import tempfile
from pathlib import Path
import threading
import time

app = Flask(__name__)

# Temporary folder for downloads (will be cleaned immediately)
TEMP_FOLDER = tempfile.gettempdir()

# Store download status
download_status = {}

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Downloader</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
            
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 100%;
        }
        
        h1 {
            color: #333;
            margin-bottom: 10px;
            text-align: center;
            font-size: 2em;
        }
        
        .subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
            font-size: 0.9em;
        }
        
        .platforms {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        
        .platform {
            padding: 8px 16px;
            background: #f0f0f0;
            border-radius: 20px;
            font-size: 0.85em;
            color: #555;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        input[type="text"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .format-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .format-btn {
            flex: 1;
            padding: 12px;
            border: 2px solid #e0e0e0;
            background: white;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 14px;
        }
        
        .format-btn:hover {
            border-color: #667eea;
        }
        
        .format-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        button.download-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        button.download-btn:hover {
            transform: translateY(-2px);
        }
        
        button.download-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            display: none;
        }
        
        .status.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .status.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .status.loading {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .progress-container {
            width: 100%;
            background: #f0f0f0;
            border-radius: 10px;
            margin-top: 15px;
            overflow: hidden;
            display: none;
        }

        .progress-bar {
            height: 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 14px;
        }
        
        .loader {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
            display: none;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .info-box {
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-top: 20px;
            border-radius: 5px;
        }

        .info-box h3 {
            color: #1976D2;
            margin-bottom: 8px;
            font-size: 16px;
        }

        .info-box p {
            color: #555;
            font-size: 14px;
            line-height: 1.5;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎥 Video Downloader</h1>
        <p class="subtitle">Download videos directly to your device</p>
        
        <div class="platforms">
            <span class="platform">YouTube</span>
            <span class="platform">TikTok</span>
            <span class="platform">Facebook</span>
        </div>
        
        <div class="input-group">
            <input type="text" id="videoUrl" placeholder="Paste video URL here..." />
        </div>
        
        <div class="format-group">
            <button class="format-btn active" data-format="video">📹 Video</button>
            <button class="format-btn" data-format="audio">🎵 Audio Only</button>
        </div>
        
        <button class="download-btn" onclick="downloadVideo()">Download to My Device</button>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar" id="progressBar">0%</div>
        </div>

        <div class="loader" id="loader"></div>
        <div class="status" id="status"></div>

        <div class="info-box">
            <h3>📱 Downloads to Your Device</h3>
            <p>
                • On <strong>Mobile</strong>: Video saves to Downloads folder or asks where to save<br>
                • On <strong>Computer</strong>: Video saves to your Downloads folder<br>
                • No files stored on server - downloads directly to you!
            </p>
        </div>
    </div>
    
    <script>
        let selectedFormat = 'video';
        let downloadCheckInterval = null;
        
        // Format button selection
        document.querySelectorAll('.format-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
                selectedFormat = this.getAttribute('data-format');
            });
        });
        
        async function downloadVideo() {
            const url = document.getElementById('videoUrl').value.trim();
            const statusDiv = document.getElementById('status');
            const loader = document.getElementById('loader');
            const downloadBtn = document.querySelector('.download-btn');
            const progressContainer = document.getElementById('progressContainer');
            const progressBar = document.getElementById('progressBar');
            
            if (!url) {
                showStatus('Please enter a video URL', 'error');
                return;
            }
            
            // Show loading
            downloadBtn.disabled = true;
            loader.style.display = 'block';
            statusDiv.style.display = 'none';
            progressContainer.style.display = 'none';
            progressBar.style.width = '0%';
            progressBar.textContent = '0%';
            
            try {
                showStatus('Processing video...', 'loading');
                
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        url: url,
                        format: selectedFormat
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    showStatus('Preparing download...', 'loading');
                    progressContainer.style.display = 'block';
                    
                    // Start checking download status
                    checkDownloadStatus(data.download_id);
                    
                } else {
                    showStatus(data.message, 'error');
                    downloadBtn.disabled = false;
                    loader.style.display = 'none';
                }
            } catch (error) {
                showStatus('Download failed: ' + error.message, 'error');
                downloadBtn.disabled = false;
                loader.style.display = 'none';
            }
        }

        async function checkDownloadStatus(downloadId) {
            const statusDiv = document.getElementById('status');
            const downloadBtn = document.querySelector('.download-btn');
            const loader = document.getElementById('loader');
            const progressBar = document.getElementById('progressBar');
            
            downloadCheckInterval = setInterval(async () => {
                try {
                    const response = await fetch('/status/' + downloadId);
                    const data = await response.json();
                    
                    if (data.status === 'ready') {
                        clearInterval(downloadCheckInterval);
                        
                        // Update progress to 100%
                        progressBar.style.width = '100%';
                        progressBar.textContent = '100%';
                        
                        showStatus('Download starting...', 'success');
                        
                        // Trigger download
                        const downloadUrl = '/get_file/' + downloadId;
                        const a = document.createElement('a');
                        a.href = downloadUrl;
                        a.download = data.filename;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        
                        setTimeout(() => {
                            showStatus('✓ Video downloaded to your device!', 'success');
                            downloadBtn.disabled = false;
                            loader.style.display = 'none';
                        }, 1000);
                        
                    } else if (data.status === 'error') {
                        clearInterval(downloadCheckInterval);
                        showStatus(data.message, 'error');
                        downloadBtn.disabled = false;
                        loader.style.display = 'none';
                    } else if (data.status === 'processing') {
                        const progress = data.progress || 0;
                        progressBar.style.width = progress + '%';
                        progressBar.textContent = progress + '%';
                    }
                } catch (error) {
                    clearInterval(downloadCheckInterval);
                    showStatus('Status check failed: ' + error.message, 'error');
                    downloadBtn.disabled = false;
                    loader.style.display = 'none';
                }
            }, 1000);
        }
        
        function showStatus(message, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.textContent = message;
            statusDiv.className = 'status ' + type;
            statusDiv.style.display = 'block';
        }
        
        // Allow Enter key to trigger download
        document.getElementById('videoUrl').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                downloadVideo();
            }
        });
    </script>
</body>
</html>
'''

def cleanup_old_files():
    """Clean up files older than 1 hour"""
    try:
        for filename in os.listdir(TEMP_FOLDER):
            if filename.startswith('video_') or filename.startswith('audio_'):
                filepath = os.path.join(TEMP_FOLDER, filename)
                if os.path.isfile(filepath):
                    if time.time() - os.path.getmtime(filepath) > 3600:
                        os.remove(filepath)
    except Exception as e:
        print(f"Cleanup error: {e}")

def download_video_task(download_id, url, format_type):
    """Background task to download video"""
    try:
        download_status[download_id] = {'status': 'processing', 'progress': 10}
        
        # Generate unique filename
        timestamp = int(time.time())
        temp_output = os.path.join(TEMP_FOLDER, f'{download_id}_%(title)s.%(ext)s')
        
        ydl_opts = {
            'outtmpl': temp_output,
            'quiet': True,
            'no_warnings': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'skip_unavailable_fragments': True,
        }
        
        if format_type == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else:
            ydl_opts['format'] = 'best'
        
        download_status[download_id] = {'status': 'processing', 'progress': 30}
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            if info is None:
                download_status[download_id] = {
                    'status': 'error',
                    'message': 'Could not extract video information'
                }
                return
            
            download_status[download_id] = {'status': 'processing', 'progress': 50}
            
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if format_type == 'audio':
                filename = os.path.splitext(filename)[0] + '.mp3'
            
            download_status[download_id] = {'status': 'processing', 'progress': 90}
            
            if os.path.exists(filename):
                download_status[download_id] = {
                    'status': 'ready',
                    'filepath': filename,
                    'filename': os.path.basename(filename),
                    'progress': 100
                }
            else:
                download_status[download_id] = {
                    'status': 'error',
                    'message': 'Download completed but file not found'
                }
                
    except Exception as e:
        error_msg = str(e)
        
        if 'Private video' in error_msg:
            error_msg = 'This video is private'
        elif 'Video unavailable' in error_msg:
            error_msg = 'Video unavailable or removed'
        elif 'HTTP Error 403' in error_msg:
            error_msg = 'Access forbidden - video may be geo-restricted'
        elif 'HTTP Error 404' in error_msg:
            error_msg = 'Video not found - check the URL'
        
        download_status[download_id] = {
            'status': 'error',
            'message': error_msg
        }

@app.route('/')
def index():
    cleanup_old_files()
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get('url')
    format_type = data.get('format', 'video')
    
    if not url:
        return jsonify({'success': False, 'message': 'URL is required'})
    
    # Generate unique download ID
    download_id = f'dl_{int(time.time())}_{os.urandom(4).hex()}'
    
    # Start background download
    thread = threading.Thread(
        target=download_video_task,
        args=(download_id, url, format_type)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'download_id': download_id,
        'message': 'Download started'
    })

@app.route('/status/<download_id>')
def status(download_id):
    if download_id in download_status:
        return jsonify(download_status[download_id])
    else:
        return jsonify({'status': 'not_found'})

@app.route('/get_file/<download_id>')
def get_file(download_id):
    if download_id not in download_status:
        return jsonify({'error': 'Download not found'}), 404
    
    status_info = download_status[download_id]
    
    if status_info.get('status') != 'ready':
        return jsonify({'error': 'File not ready'}), 400
    
    filepath = status_info.get('filepath')
    filename = status_info.get('filename')
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        # Send file to user's device
        response = send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
        # Schedule file deletion after sending
        @response.call_on_close
        def cleanup():
            try:
                time.sleep(2)
                if os.path.exists(filepath):
                    os.remove(filepath)
                if download_id in download_status:
                    del download_status[download_id]
            except:
                pass
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)