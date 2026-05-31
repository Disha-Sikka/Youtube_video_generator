
import os
import io
import requests
import streamlit as st
from dotenv import load_dotenv
from google import genai
from PIL import Image
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment

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
    """Sends the extracted prompt to Hugging Face Inference API."""
    API_URL = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {os.getenv('HUGGINGFACE_API_KEY')}"}
    
    enhanced_prompt = f"3D animation style, bright vibrant colors, cute, Cocomelon style, Pixar style, {prompt}"
    
    payload = {"inputs": enhanced_prompt}
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        image = Image.open(io.BytesIO(response.content))
        image.save(filename)
        return filename
    else:
        raise Exception(f"Image API failed: {response.text}")

# --- STREAMLIT UI ---
st.title("🐢 Kids Rhyme Video Engine")
st.subheader("Automated Asset Generation Dashboard")

topic_input = st.text_input("Enter a topic for the rhyme (e.g., 'Picking up litter makes the earth smile'):")

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
    st.text_area("Raw AI Output", st.session_state.generated_text, height=200)
    
    full_text = st.session_state.generated_text
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Generate Final Assets", type="primary"):
            with st.spinner("Building audio and visuals..."):
                try:
                    # 1. Parse text
                    parts = full_text.split("IMAGE_PROMPT:")
                    rhyme_only = parts[0].replace("RHYME:", "").strip()
                    image_prompt = parts[1].strip() if len(parts) > 1 else "Cute colorful kids scene"
                    
                    # 2. Generate Voiceover
                    raw_voice = generate_voiceover(rhyme_only)
                    
                    # 3. Mix with Background Music
                    final_audio_path = mix_audio(raw_voice, "bg_music.mp3", "final_audio.mp3")
                    st.success("Audio Pipeline Complete! 🎧")
                    st.audio(final_audio_path, format="audio/mp3")
                    
                    # 4. Generate Image
                    image_file = generate_image(image_prompt)
                    st.success("Visual Pipeline Complete! 🎨")
                    st.image(image_file, caption="Generated 3D Background")
                    
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
                
    with col2:
        if st.button("❌ Reject / Regenerate"):
            st.session_state.generated_text = None
            st.rerun()