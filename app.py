import os
import asyncio
import streamlit as st
import edge_tts
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()
client = genai.Client()

def generate_rhyme_and_prompts(topic: str):
    """
    Sends a highly engineered prompt to Gemini to return a Cocomelon-style 
    song and a 3D animation style image description.
    """
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

# --- EDGE-TTS AUDIO FUNCTIONS ---
async def async_generate_audio(text: str, filename: str, voice: str):
    """The asynchronous core function that talks to Microsoft Edge TTS."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(filename)

def generate_audio(text: str, filename="rhyme_audio.mp3"):
    """Synchronous wrapper so Streamlit can run the async function."""
    # Using a cheerful female voice
    voice = "en-US-AriaNeural" 
    
    asyncio.run(async_generate_audio(text, filename, voice))
    return filename

# --- Streamlit UI Setup ---
st.title("🤖 Kids Rhyme Video Engine")
st.subheader("Step 1 & 2: Content Generation & Edge TTS")

topic_input = st.text_input("Enter a topic for the rhyme:")

if "generated_text" not in st.session_state:
    st.session_state.generated_text = None

if st.button("Generate Script & Prompts"):
    if topic_input:
        with st.spinner("Writing Cocomelon-style hit..."):
            try:
                st.session_state.generated_text = generate_rhyme_and_prompts(topic_input)
            except Exception as e:
                st.error(f"Error calling API: {e}")
    else:
        st.warning("Please enter a topic first!")

if st.session_state.generated_text:
    st.markdown("### 📋 Generated Output")
    st.text_area("Raw AI Output", st.session_state.generated_text, height=250)
    
    full_text = st.session_state.generated_text
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Approve & Generate Voiceover", type="primary"):
            with st.spinner("Recording Edge TTS voiceover..."):
                try:
                    # Parse out just the pure rhyme
                    rhyme_only = full_text.split("IMAGE_PROMPT:")[0].replace("RHYME:", "").strip()
                except:
                    rhyme_only = full_text
                
                # Generate and save the audio
                audio_file_path = generate_audio(rhyme_only)
                
                st.success("Audio generated successfully! 🎧")
                st.audio(audio_file_path, format="audio/mp3")
                
    with col2:
        if st.button("❌ Reject / Regenerate"):
            st.session_state.generated_text = None
            st.rerun()