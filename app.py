
import os
import io
import requests
import asyncio
import edge_tts
import streamlit as st
from dotenv import load_dotenv
from google import genai
from PIL import Image
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from huggingface_hub import InferenceClient
from moviepy import ImageClip, AudioFileClip

# --- SETUP & AUTHENTICATION ---
load_dotenv()
client = genai.Client()
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

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
    # "en-US-AriaNeural" is bright, clear, and excellent for storytelling
    voice = "en-US-AriaNeural" 
    
    asyncio.run(async_generate_audio(text, filename, voice))
    return filename

# --- 3. AUDIO MIXING (PYDUB) ---
def mix_audio(voice_file: str, bgm_file="bg_music.mp3", output_file="final_audio.mp3"):
    """Overlays the voiceover onto a looping background music track."""
    from pydub import AudioSegment
    
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
'''
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
'''
# --- 4. IMAGE GENERATION (HUGGING FACE HUB) ---
def generate_image(prompt: str, filename="background_art.png"):
    """Generates the image using the official Hugging Face Python SDK."""
    # Initialize the client with your token
    hf_client = InferenceClient(api_key=os.getenv('HUGGINGFACE_API_KEY'))
    
    enhanced_prompt = f"3D animation style, bright vibrant colors, cute, Cocomelon style, Pixar style, {prompt}"
    
    try:
        # Using FLUX.1-schnell: Currently the fastest and most widely supported free model
        image = hf_client.text_to_image(
            prompt=enhanced_prompt,
            model="black-forest-labs/FLUX.1-schnell" 
        )
        image.save(filename)
        return filename
    except Exception as e:
        raise Exception(f"Image API failed: {str(e)}")

# --- 5. NEW: VIDEO RENDERING (MOVIEPY) ---
def create_video(image_file: str, audio_file: str, output_file="final_video.mp4"):
    """Combines the static image and mixed audio into a final MP4 video file."""
    # Load the audio to get its exact duration
    audio_clip = AudioFileClip(audio_file)
    
    # Create an image clip that lasts exactly as long as the audio
    video_clip = ImageClip(image_file).with_duration(audio_clip.duration)
    
    # Set the audio of the video clip
    video_clip = video_clip.with_audio(audio_clip)
    
    # Write the result to a file (using 24fps for standard video)
    video_clip.write_videofile(output_file, fps=24, codec="libx264", audio_codec="aac")
    
    # Close clips to free up system memory
    audio_clip.close()
    video_clip.close()
    
    return output_file

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
                    # 1. Parse text
                    parts = full_text.split("IMAGE_PROMPT:")
                    rhyme_only = parts[0].replace("RHYME:", "").strip()
                    image_prompt = parts[1].strip() if len(parts) > 1 else "Cute colorful kids scene"
                    
                    # 2. Generate Voiceover
                    raw_voice = generate_voiceover(rhyme_only)
                    
                    # 3. Mix Audio
                    final_audio_path = mix_audio(raw_voice, "bg_music.mp3", "final_audio.mp3")
                    st.write("🎵 Audio mixed successfully...")
                    
                    # 4. Generate Image
                    image_file = generate_image(image_prompt)
                    st.write("🎨 Background art generated...")
                    
                    # 5. Render Video
                    final_video_path = create_video(image_file, final_audio_path, "final_video.mp4")
                    st.success("🎬 Video Render Complete!")
                    
                    # Display the final video player
                    st.video(final_video_path)
                    
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
                
    with col2:
        if st.button("❌ Reject / Regenerate"):
            st.session_state.generated_text = None
            st.rerun()