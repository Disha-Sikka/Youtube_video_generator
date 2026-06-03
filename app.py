import os
import io
import requests
import asyncio
import edge_tts
import json
import streamlit as st
from dotenv import load_dotenv
from google import genai
from PIL import Image
from pydub import AudioSegment
from huggingface_hub import InferenceClient
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, ImageClip
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# --- SETUP & AUTHENTICATION ---
load_dotenv()
client = genai.Client()

# --- 1. SCRIPT GENERATION (GEMINI) ---
def generate_rhyme_and_prompts(topic: str):
    prompt = f"""
    You are a master songwriter for a hit toddler channel like Cocomelon.
    Write a highly repetitive, bouncy, and extremely catchy nursery rhyme song about: "{topic}".
    
    The song MUST have:
    1. A repeating, catchy hook or chorus.
    2. Fun sound words and actions (e.g., "Yay! Yay!", "Clap your hands!", "Chomp chomp!").
    3. A bouncy rhythm that naturally fits a happy nursery rhyme melody.
    
    CRITICAL INSTRUCTION: Do NOT include structural labels like "Verse 1", "Chorus", "Hook", or "Outro" in the text. Just write the pure lyrics.
    
    Format your response EXACTLY like this:
    RHYME:
    [Insert the bouncy song lyrics here]
    
    IMAGE_PROMPT:
    [Describe a bright, colorful, 3D animated scene (like Cocomelon or Pixar style) featuring cute, big-eyed toddlers and friendly animals matching the song.]
    """
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

async def async_generate_audio(text: str, filename: str, voice: str):
    """The asynchronous core function for Microsoft Edge TTS."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

def generate_voiceover(text: str, filename="raw_voice.mp3"):
    """Generates voiceover using Edge TTS completely for free."""
    voice = "en-US-AriaNeural" 
    asyncio.run(async_generate_audio(text, filename, voice))
    return filename

# --- 3. AUDIO MIXING (PYDUB) ---
def mix_audio(voice_file: str, bgm_file="bg_music.mp3", output_file="final_audio.mp3"):
    """Overlays the voiceover onto a looping background music track."""
    if not os.path.exists(bgm_file):
        st.warning(f"Background music '{bgm_file}' not found. Skipping mixing.")
        return voice_file
        
    voice = AudioSegment.from_mp3(voice_file)
    bgm = AudioSegment.from_mp3(bgm_file)
    
    # Lower the background music volume by 15 decibels so the voice is clear
    bgm = bgm - 15
    
    # Loop the background music until it's as long as the voiceover
    while len(bgm) < len(voice):
        bgm += bgm
        
    # Trim the music to end exactly when the voiceover ends
    bgm = bgm[:len(voice)]
    
    # Merge them together
    final_audio = bgm.overlay(voice)
    final_audio.export(output_file, format="mp3")
    return output_file

# --- 4. IMAGE GENERATION (WIDESCREEN 16:9 RECONSTRUCTED) ---
def generate_image(prompt: str, filename="background_art.png"):
    """Generates a landscape image using the official Hugging Face Python SDK."""
    hf_client = InferenceClient(api_key=os.getenv('HUGGINGFACE_API_KEY'))
    
    # Force landscape styling inside the prompt pipeline to block automatic Shorts conversion
    enhanced_prompt = f"Widescreen cinematic 16:9 aspect ratio, landscape view, 3D animation style, bright vibrant colors, cute, Cocomelon style, Pixar style, {prompt}"
    
    try:
        image = hf_client.text_to_image(
            prompt=enhanced_prompt,
            model="black-forest-labs/FLUX.1-schnell" 
        )
        image.save(filename)
        return filename
    except Exception as e:
        raise Exception(f"Image API failed: {str(e)}")
    
# --- 5. CINEMATIC VIDEO RENDERING ---
def create_video(image_file: str, audio_file: str, output_file="final_video.mp4"):
    """Creates a dynamic video from scratch to bypass ImageClip bugs."""
    import numpy as np
    from PIL import Image
    from moviepy import VideoClip, AudioFileClip
    
    audio_clip = AudioFileClip(audio_file)
    duration = audio_clip.duration
    
    base_img = Image.open(image_file).convert("RGB")
    base_w, base_h = base_img.size
    
    def make_frame(t):
        fraction = t / duration
        scale = 1.0 + (0.15 * fraction)  # Smooth 15% zoom over the video duration
        
        new_w = int(base_w * scale)
        new_h = int(base_h * scale)
        
        img_resized = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        left = int((new_w - base_w) / 2)
        top = int((new_h - base_h) / 2)
        right = left + base_w
        bottom = top + base_h
        
        cropped_img = img_resized.crop((left, top, right, bottom))
        return np.array(cropped_img, dtype=np.uint8)

    video_clip = VideoClip(make_frame, duration=duration)
    final_video = video_clip.with_audio(audio_clip)
    
    final_video.write_videofile(
        output_file, 
        fps=24, 
        codec="libx264", 
        audio_codec="aac",
        logger=None
    )
    
    audio_clip.close()
    video_clip.close()
    final_video.close()
    base_img.close()
    
    return output_file

# --- 7. YOUTUBE UPLOAD AUTOMATION (CLOUD SAFE) ---
def upload_to_youtube(video_file: str, title: str, description: str):
    """Authenticates using background tokens without desktop browser dependencies."""
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    
    # 1. Inspect environment secrets
    if "TOKEN_JSON" not in st.secrets:
        raise Exception("Authentication layout failure: TOKEN_JSON key not found in Streamlit Secrets.")
        
    # 2. Parse token string out of memory
    try:
        token_info = json.loads(st.secrets["TOKEN_JSON"])
        creds = Credentials.from_authorized_user_info(token_info, scopes)
    except Exception as e:
        raise Exception(f"Failed to compile authorization profile: {e}")
        
    # 3. Handle token refreshing silently in background
    if creds and creds.expired and creds.refresh_token:
        try:
            st.info("🔄 Renewing API session tokens dynamically...")
            creds.refresh(Request())
        except Exception as e:
            raise Exception(f"OAuth core rejection during key renewal: {e}")

    if not creds or not creds.valid:
        raise Exception("Google verification validation failure. Please re-run your local token script.")

    # 4. Initialize client architecture
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    # 5. Insert video parameters (Standard Long-Form Setup)
    request = youtube.videos().insert(
        part="snippet,status",
        body={
          "snippet": {
            "title": title,
            "description": description + "\n\n#children #nurseryrhyme #kids #education #animation",
            "tags": ["kids", "nursery rhyme", "education", "animation", "video", "stories"],
            "categoryId": "22" 
          },
          "status": {
            "privacyStatus": "public" 
          }
        },
        media_body=MediaFileUpload(video_file, chunksize=-1, resumable=True)
    )
    
    response = request.execute()
    return response['id']


# --- STREAMLIT UI ---
st.title("🐢 Kids Rhyme Video Engine")
st.subheader("Automated Video Generation Dashboard")

topic_input = st.text_input("Enter a topic for the rhyme:")

if "generated_text" not in st.session_state:
    st.session_state.generated_text = None

if st.button("Generate Script & Prompts"):
    if topic_input:
        with st.spinner("Writing hit song..."):
            try:
                st.session_state.generated_text = generate_rhyme_and_prompts(topic_input)
            except Exception as e:
                st.error(f"Error calling API: {e}")
    else:
        st.warning("Please enter a topic first!")

if st.session_state.generated_text:
    st.markdown("### 📋 Generated Output")
    st.text_area("Raw AI Output", st.session_state.generated_text, height=150)
    
    full_text = st.session_state.generated_text
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Render Final Video", type="primary"):
            with st.spinner("Executing full pipeline (this takes a minute)..."):
                try:
                    parts = full_text.split("IMAGE_PROMPT:")
                    rhyme_only = parts[0].replace("RHYME:", "").strip()
                    image_prompt = parts[1].strip() if len(parts) > 1 else "Cute colorful kids scene"
                    
                    raw_voice = generate_voiceover(rhyme_only)
                    final_audio_path = mix_audio(raw_voice, "bg_music.mp3", "final_audio.mp3")
                    st.write("🎵 Audio mixed successfully...")
                    
                    image_file = generate_image(image_prompt)
                    st.write("🎨 Widescreen context graphics generated...")
                    
                    st.write("✨ Synchronizing production media layers...")
                    final_video_path = create_video(image_file, final_audio_path, "final_video.mp4")
                    st.success("🎬 Video Render Complete!")
                    
                    st.video(final_video_path)
                    st.session_state.final_video = final_video_path
                    
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
                
    with col2:
        if st.button("❌ Reject / Regenerate"):
            st.session_state.generated_text = None
            if "final_video" in st.session_state:
                del st.session_state.final_video
            st.rerun()

# PUBLIC VIDEO UPLOAD MANAGEMENT PANEL
if "final_video" in st.session_state:
    st.markdown("---")
    st.markdown("### 🚀 Step 3: Publish to YouTube")
    
    video_title = st.text_input("YouTube Video Title:", value=f"{topic_input} - Kids Nursery Rhyme")
    video_desc = st.text_area("YouTube Description:", value="A fun and educational song for kids!")
    
    if st.button("📤 Publish Video to YouTube", type="primary"):
        with st.spinner("Uploading file blocks directly to your media feed..."):
            try:
                video_id = upload_to_youtube(st.session_state.final_video, video_title, video_desc)
                st.success(f"✅ Upload Complete! Video ID: {video_id}")
                
                # Public watch configurations
                st.markdown(f"🍿 **[Click here to watch your live YouTube Video](https://www.youtube.com/watch?v={video_id})**")
                st.info(f"🔗 Direct shareable video link: `https://youtu.be/{video_id}`")
            except Exception as e:
                st.error(f"Upload failed: {e}")