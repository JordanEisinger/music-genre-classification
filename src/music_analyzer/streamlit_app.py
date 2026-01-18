# src/music_analyzer/streamlit_app.py
import streamlit as st
import streamlit.components.v1 as components
import os
import sys
from pathlib import Path
import base64
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent.parent))
from music_analyzer.song_detector import SongDetector

st.set_page_config(
    page_title="Song Analyzer",
    page_icon="🎵",
    layout="wide"
)

# Initialize session state
if 'audio_path' not in st.session_state:
    st.session_state.audio_path = None
if 'source_type' not in st.session_state:
    st.session_state.source_type = None
if 'video_title' not in st.session_state:
    st.session_state.video_title = None

@st.cache_resource
def get_detector():
    return SongDetector()

def download_youtube_audio(youtube_url, output_base):
    """Download audio without requiring ffmpeg"""
    try:
        import yt_dlp
        
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': output_base,
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': 30,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            if duration > 600:
                return False, "Video too long (max 10 minutes)", 0, None
            
            ydl.download([youtube_url])
            
            # Find the downloaded file
            for ext in ['.webm', '.m4a', '.opus', '.mp4', '.ogg']:
                test_path = output_base + ext
                if os.path.exists(test_path):
                    return True, title, duration, test_path
            
            if os.path.exists(output_base):
                return True, title, duration, output_base
            
            return False, "Downloaded file not found", 0, None
    
    except Exception as e:
        return False, str(e), 0, None

def create_audio_player_with_waveform(audio_file_or_path, is_file=True):
    """Create an interactive audio player with live waveform"""
    
    if is_file:
        audio_bytes = audio_file_or_path.read()
        filename = audio_file_or_path.name
    else:
        with open(audio_file_or_path, 'rb') as f:
            audio_bytes = f.read()
        filename = os.path.basename(audio_file_or_path)
    
    audio_base64 = base64.b64encode(audio_bytes).decode()
    
    file_extension = filename.split('.')[-1].lower()
    mime_types = {
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav',
        'ogg': 'audio/ogg',
        'flac': 'audio/flac',
        'm4a': 'audio/mp4',
        'webm': 'audio/webm',
        'opus': 'audio/opus',
        'mp4': 'audio/mp4'
    }
    mime_type = mime_types.get(file_extension, 'audio/mpeg')
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/wavesurfer.js@7"></script>
        <style>
            body {{
                margin: 0;
                padding: 20px;
                font-family: Arial, sans-serif;
                background: transparent;
            }}
            #waveform {{
                width: 100%;
                height: 128px;
                margin-bottom: 20px;
                cursor: pointer;
            }}
            .controls {{
                display: flex;
                gap: 10px;
                align-items: center;
                flex-wrap: wrap;
            }}
            button {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                transition: all 0.3s;
            }}
            button:hover {{
                opacity: 0.8;
            }}
            .time {{
                font-size: 14px;
                color: #666;
                min-width: 100px;
            }}
        </style>
    </head>
    <body>
        <div id="waveform"></div>
        <div class="controls">
            <button id="playPause">▶️ Play</button>
            <span class="time" id="time">0:00 / 0:00</span>
            <input type="range" id="volume" min="0" max="100" value="50" style="width: 150px;">
            <span style="font-size: 14px;">🔊</span>
        </div>

        <script>
            const wavesurfer = WaveSurfer.create({{
                container: '#waveform',
                waveColor: '#667eea',
                progressColor: '#764ba2',
                cursorColor: '#764ba2',
                barWidth: 2,
                barRadius: 3,
                height: 128,
                barGap: 2,
                responsive: true,
                normalize: true
            }});

            wavesurfer.load('data:{mime_type};base64,{audio_base64}');

            const playPauseBtn = document.getElementById('playPause');
            playPauseBtn.addEventListener('click', () => wavesurfer.playPause());
            document.getElementById('waveform').addEventListener('click', () => wavesurfer.playPause());

            wavesurfer.on('play', () => playPauseBtn.textContent = '⏸️ Pause');
            wavesurfer.on('pause', () => playPauseBtn.textContent = '▶️ Play');
            wavesurfer.on('finish', () => playPauseBtn.textContent = '▶️ Play');

            wavesurfer.on('audioprocess', () => {{
                document.getElementById('time').textContent = 
                    formatTime(wavesurfer.getCurrentTime()) + ' / ' + formatTime(wavesurfer.getDuration());
            }});

            wavesurfer.on('ready', () => {{
                document.getElementById('time').textContent = 
                    '0:00 / ' + formatTime(wavesurfer.getDuration());
            }});

            document.getElementById('volume').addEventListener('input', (e) => {{
                wavesurfer.setVolume(e.target.value / 100);
            }});

            function formatTime(s) {{
                const m = Math.floor(s / 60);
                const sec = Math.floor(s % 60);
                return m + ':' + (sec < 10 ? '0' : '') + sec;
            }}
        </script>
    </body>
    </html>
    """
    
    return html_code

# Main App
st.title("🎵 Song Analyzer")
st.markdown("Upload an audio file or provide a YouTube URL to detect its musical key")

tab1, tab2 = st.tabs(["📁 Upload File", "🎬 YouTube URL"])

with tab1:
    st.markdown("### Upload an audio file")
    uploaded_file = st.file_uploader(
        "Choose an audio file",
        type=['mp3', 'wav', 'flac', 'm4a', 'ogg']
    )
    
    if uploaded_file is not None:
        # Save to session state
        os.makedirs("/tmp", exist_ok=True)
        temp_path = f"/tmp/{uploaded_file.name}"
        
        # Only write if file changed
        if st.session_state.audio_path != temp_path:
            with open(temp_path, 'wb') as f:
                f.write(uploaded_file.getbuffer())
            
            st.session_state.audio_path = temp_path
            st.session_state.source_type = "upload"
            st.session_state.video_title = uploaded_file.name

with tab2:
    st.markdown("### Provide a YouTube URL")
    youtube_url = st.text_input(
        "YouTube URL",
        placeholder="https://www.youtube.com/watch?v=..."
    )
    
    if youtube_url and st.button("📥 Download Audio", type="primary"):
        if not ('youtube.com' in youtube_url or 'youtu.be' in youtube_url):
            st.error("❌ Please provide a valid YouTube URL")
        else:
            try:
                import yt_dlp
            except ImportError:
                st.error("❌ yt-dlp not installed. Run: `pip install yt-dlp`")
                st.stop()
            
            with st.spinner("📥 Downloading audio from YouTube..."):
                os.makedirs("/tmp", exist_ok=True)
                temp_base = f"/tmp/youtube_{abs(hash(youtube_url))}"
                
                success, title, duration, actual_path = download_youtube_audio(youtube_url, temp_base)
                
                if success and actual_path:
                    st.success(f"✅ Downloaded: {title}")
                    st.info(f"⏱️ Duration: {duration // 60}:{duration % 60:02d}")
                    
                    # Save to session state
                    st.session_state.audio_path = actual_path
                    st.session_state.source_type = "youtube"
                    st.session_state.video_title = title
                    
                    ext = os.path.splitext(actual_path)[1]
                else:
                    st.error(f"❌ Failed: {title}")

# Display audio player if we have a file
if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
    
    # Display audio player
    html_code = create_audio_player_with_waveform(st.session_state.audio_path, is_file=False)
    components.html(html_code, height=250)
    
    # Analyze button
    if st.button("🎹 Analyze Song", type="primary", use_container_width=True):
        with st.spinner("🎧 Analyzing audio..."):
            try:
                detector = get_detector()
                key, key_confidence = detector.detect_key(st.session_state.audio_path)
                tempo, tempo_confidence = detector.detect_tempo(st.session_state.audio_path)
                time_sig, ts_confidence = detector.detect_time_signature(st.session_state.audio_path)
                
                # st.success("✅ Analysis complete!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Detected Key", key)
                    st.metric("Detected Tempo", f"{tempo:.0f} BPM")
                    st.metric("Detected Time Signature", time_sig)
                with col2:
                    st.metric("Confidence", f"{key_confidence:.1%}")
                    st.metric("Confidence", f"{tempo_confidence:.1%}")
                    st.metric("Confidence", f"{ts_confidence:.1%}")
                
                st.subheader("🎸 Detected Chords")
                chords = detector.detect_chords(st.session_state.audio_path)

                cols = st.columns(4)
                for idx, (chord, count) in enumerate(chords):
                    with cols[idx % 4]:
                        st.metric(f"#{idx+1}", chord, f"{count} occurrences")
                
                # In your Streamlit app:
                with st.expander("📊 View Spectrogram", expanded=False):
                    with st.spinner("Generating spectrogram..."):
                        fig = detector.create_spectrogram(st.session_state.audio_path)
                        st.pyplot(fig)
                        plt.close(fig)
                
                st.success("✅ Analysis complete!")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

else:
    st.info("👆 Upload a file or provide a YouTube URL to get started")

# Add a button to clear/reset
if st.session_state.audio_path:
    if st.button("🔄 Analyze a Different Song"):
        st.session_state.audio_path = None
        st.session_state.source_type = None
        st.session_state.video_title = None
        st.rerun()