import os
import io
import math
import requests
import asyncio
import edge_tts
import json
import numpy as np
import streamlit as st
from dotenv import load_dotenv
from google import genai
from PIL import Image
from pydub import AudioSegment
from huggingface_hub import InferenceClient
from moviepy import VideoClip, VideoFileClip, concatenate_videoclips, AudioFileClip
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from elevenlabs.client import elevenlabs

# --- SETUP & AUTHENTICATION ---
load_dotenv()
client = genai.Client()
eleven_client = elevenlabs.Client(api_key=os.getenv('ELEVENLABS_API_KEY'))

# --- 1. MULTI-SCENE SCRIPT GENERATION (1-MINUTE RUNTIME OPTIMIZED) ---
def generate_rhyme_and_prompts(topic: str):
    prompt = f"""
    You are a master songwriter for a hit toddler channel like Cocomelon.
    Write a highly repetitive, bouncy, and extremely catchy nursery rhyme song about: "{topic}".
    
    CRITICAL DURATION TARGET: The total song MUST be long enough to last approximately 1 minute (60 seconds) when spoken aloud. 
    To achieve this, the entire song must contain a total volume of roughly 130 to 150 words.
    
    Break the song down into exactly 4 sequential scenes. Each scene's lyrics must be a substantial, multi-line verse or chorus block containing roughly 35 words (to guarantee ~15 seconds of narration time per scene).
    
    Do NOT include structural labels like "Verse 1" or "Chorus" inside the lyrics themselves.
    
    CRITICAL LANGUAGE INSTRUCTION:
    1. Automatically detect the language of the topic input text.
    2. The "lyrics" values inside the JSON MUST be written in that exact same language. If the input topic is written in Hindi (e.g., "हाथी", "चंदा मामा", "बंदर"), the lyrics must be written completely in rhythmic, playful Hindi using the Devanagari script.
    3. The "image_prompt" values MUST always be written in English, regardless of the topic language, so that the downstream image compilation engine can interpret it accurately.
    
    Return your response STRICTLY as a valid JSON array of objects, with no markdown formatting wrappers, matching this schema:
    [
      {{"lyrics": "A substantial 35-word block of bouncy, highly repetitive lyrics for Scene 1...", "image_prompt": "Bright, colorful 3D Pixar style scene description in English matching the lyrics..."}},
      {{"lyrics": "A substantial 35-word block of bouncy, highly repetitive lyrics for Scene 2...", "image_prompt": "Next scene description in English..."}},
      {{"lyrics": "A substantial 35-word block of bouncy, highly repetitive lyrics for Scene 3...", "image_prompt": "Next scene description in English..."}},
      {{"lyrics": "A substantial 35-word block of bouncy, highly repetitive lyrics for Scene 4...", "image_prompt": "Next scene description in English..."}}
    ]
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

# --- 2. EXPRESSIVE VOICEOVER (ELEVENLABS) ---
def generate_voiceover(text: str, filename="raw_voice.mp3"):
    """Generates hyper-expressive audio using ElevenLabs."""
    # Using a default friendly voice ID (Rachel) - you can swap this with a kid's voice ID from your dashboard
    audio_generator = eleven_client.text_to_speech.convert(
        text=text,
        voice_id="HVHOSc49fGYttVjeiWb2",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    
    with open(filename, "wb") as f:
        if hasattr(audio_generator, '__iter__') and not isinstance(audio_generator, bytes):
             for chunk in audio_generator:
                 f.write(chunk)
        else:
             f.write(audio_generator)
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

# --- 4. IMAGE GENERATION (HUGGING FACE) ---
def generate_image(prompt: str, filename="background_art.png"):
    """Generates a landscape scene using the official Hugging Face Python SDK."""
    hf_client = InferenceClient(api_key=os.getenv('HUGGINGFACE_API_KEY'))
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
    
# --- 5. LOCAL MOTION ENGINE (PER-SCENE COMPILATION) ---
def create_scene_video(image_file: str, duration: float, output_file: str):
    """Creates a dynamic visual-only clip from an image with a smooth zoom tracking matrix."""
    base_img = Image.open(image_file).convert("RGB")
    base_w, base_h = base_img.size
    
    def make_frame(t):
        fraction = t / duration if duration > 0 else 0
        scale = 1.0 + (0.12 * fraction)  # Smooth continuous 12% zoom effect per scene
        
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
    video_clip.write_videofile(
        output_file, 
        fps=24, 
        codec="libx264", 
        audio=False,  
        logger=None
    )
    video_clip.close()
    base_img.close()
    return output_file

def compile_full_storyboard_video(scene_data, bgm_file="bg_music.mp3", output_file="final_video.mp4"):
    """Orchestrates asset compilation across scenes, blending audio tracks globally."""
    video_clips = []
    combined_voice = AudioSegment.empty()
    temp_files = []
    
    for i, scene in enumerate(scene_data):
        st.write(f"🎬 Compiling Scene Layout {i+1}/{len(scene_data)}...")
        
        # 1. Generate local voice snippet for this scene
        v_file = f"temp_voice_{i}.mp3"
        generate_voiceover(scene['lyrics'], filename=v_file)
        temp_files.append(v_file)
        
        # Read duration boundaries using pydub
        seg = AudioSegment.from_mp3(v_file)
        duration = len(seg) / 1000.0
        combined_voice += seg  
        
        # 2. Generate unique background artwork for this scene
        img_file = f"temp_img_{i}.png"
        generate_image(scene['image_prompt'], filename=img_file)
        temp_files.append(img_file)
        
        # 3. Create independent zooming visual segment
        vid_file = f"temp_vid_{i}.mp4"
        create_scene_video(img_file, duration, vid_file)
        temp_files.append(vid_file)
        
        video_clips.append(VideoFileClip(vid_file))
        
    st.write("🎵 Mixing complete speech track with background orchestration...")
    raw_voice_path = "temp_full_voice.mp3"
    combined_voice.export(raw_voice_path, format="mp3")
    temp_files.append(raw_voice_path)
    
    # Mix global voice track with background melody
    final_audio_path = mix_audio(raw_voice_path, bgm_file, "final_audio.mp3")
    
    st.write("🎞️ Stitching distinct scenes into visual timeline...")
    final_visual_timeline = concatenate_videoclips(video_clips, method="compose")
    
    # Bind full audio track back to visual timeline mesh
    audio_track = AudioFileClip(final_audio_path)
    final_video = final_visual_timeline.with_audio(audio_track)
    
    st.write(f"🚀 Rendering final unified multi-scene publication file (Total Duration: {audio_track.duration:.1f}s)...")
    final_video.write_videofile(
        output_file,
        fps=24,
        codec="libx264",
        audio_codec="aac",
        logger=None
    )
    
    # File cleanup closures
    audio_track.close()
    final_video.close()
    final_visual_timeline.close()
    for clip in video_clips:
        clip.close()
        
    for file in temp_files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except:
            pass
            
    return output_file

# --- 7. YOUTUBE UPLOAD AUTOMATION (CLOUD SAFE) ---
def upload_to_youtube(video_file: str, title: str, description: str):
    """Authenticates using background tokens without desktop browser dependencies."""
    scopes = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None
    
    if "TOKEN_JSON" not in st.secrets:
        raise Exception("Authentication layout failure: TOKEN_JSON key not found in Streamlit Secrets.")
        
    try:
        token_info = json.loads(st.secrets["TOKEN_JSON"])
        creds = Credentials.from_authorized_user_info(token_info, scopes)
    except Exception as e:
        raise Exception(f"Failed to compile authorization profile: {e}")
        
    if creds and creds.expired and creds.refresh_token:
        try:
            st.info("🔄 Renewing API session tokens dynamically...")
            creds.refresh(Request())
        except Exception as e:
            raise Exception(f"OAuth core rejection during key renewal: {e}")

    if not creds or not creds.valid:
        raise Exception("Google verification validation failure. Please re-run your local token script.")

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

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
st.subheader("Multi-Scene Automated Production Dashboard (~1 Min Target)")

topic_input = st.text_input("Enter a topic for the rhyme (e.g., 'Monkey' or 'हाथी'):")

if "generated_text" not in st.session_state:
    st.session_state.generated_text = None

if st.button("Generate Script & Prompts"):
    if topic_input:
        with st.spinner("Writing storyboard scripts..."):
            try:
                st.session_state.generated_text = generate_rhyme_and_prompts(topic_input)
            except Exception as e:
                st.error(f"Error calling API: {e}")
    else:
        st.warning("Please enter a topic first!")

if st.session_state.generated_text:
    st.markdown("### 📋 Generated Video Storyboard Struct")
    
    try:
        raw_text = st.session_state.generated_text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
        parsed_scenes = json.loads(raw_text)
        
        for idx, scene in enumerate(parsed_scenes):
            with st.expander(f"🎬 Scene {idx + 1} Configuration Profile"):
                st.write(f"**Lyrics Segment:** {scene['lyrics']}")
                st.write(f"**Visual Generation Blueprint (English):** {scene['image_prompt']}")
    except Exception as json_err:
        st.text_area("Raw AI Structure (Fallback view)", st.session_state.generated_text, height=150)
        parsed_scenes = None
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Render Final Video", type="primary"):
            if not parsed_scenes:
                st.error("JSON data format error. Click regenerate to build a fresh schema profile.")
            else:
                with st.spinner("Processing composite multi-scene canvas pipeline..."):
                    try:
                        final_video_path = compile_full_storyboard_video(parsed_scenes, "bg_music.mp3", "final_video.mp4")
                        st.success("🎬 Widescreen Video Render Complete!")
                        
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
                
                st.markdown(f"🍿 **[Click here to watch your live YouTube Video](https://www.youtube.com/watch?v={video_id})**")
                st.info(f"🔗 Direct shareable video link: `https://youtu.be/{video_id}`")
            except Exception as e:
                st.error(f"Upload failed: {e}")