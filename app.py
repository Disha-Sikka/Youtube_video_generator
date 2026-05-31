import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from gtts import gTTS  # <-- NEW IMPORT

# Load environment variables
load_dotenv()
client = genai.Client()

def generate_rhyme_and_prompts(topic: str):
    prompt = f"""
    You are an expert children's content creator. 
    Create a short, fun, 4-line rhyming verse for toddlers about the topic: "{topic}".
    
    Also, provide a vivid description for an image generator (like Stable Diffusion) 
    to create a cute, bright background/character illustration matching this rhyme.
    
    Format your response exactly like this:
    RHYME:
    [Insert 4-line rhyme here]
    
    IMAGE_PROMPT:
    [Insert image prompt here]
    """
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
    )
    return response.text

# --- NEW AUDIO FUNCTION ---
def generate_audio(text: str, filename="rhyme_audio.mp3"):
    """Converts text to speech and saves it as an MP3."""
    # We use lang='en' for English. 
    tts = gTTS(text=text, lang='en', slow=False)
    tts.save(filename)
    return filename

# --- Streamlit UI Setup ---
st.title("🤖 Kids Rhyme Video Engine")
st.subheader("Step 1 & 2: Content Generation & Voiceover")

topic_input = st.text_input("Enter a topic for the rhyme:")

if "generated_text" not in st.session_state:
    st.session_state.generated_text = None

if st.button("Generate Script & Prompts"):
    if topic_input:
        with st.spinner("Generating creative ideas..."):
            try:
                st.session_state.generated_text = generate_rhyme_and_prompts(topic_input)
            except Exception as e:
                st.error(f"Error calling API: {e}")
    else:
        st.warning("Please enter a topic first!")

if st.session_state.generated_text:
    st.markdown("### 📋 Generated Output")
    st.text_area("Raw AI Output (Review carefully)", st.session_state.generated_text, height=250)
    
    full_text = st.session_state.generated_text
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Approve & Generate Voiceover", type="primary"):
            with st.spinner("Recording voiceover..."):
                # 1. Parse out just the rhyme (we don't want the robot reading the image prompt!)
                try:
                    # Split the text at "IMAGE_PROMPT:" and take the first half, then remove "RHYME:"
                    rhyme_only = full_text.split("IMAGE_PROMPT:")[0].replace("RHYME:", "").strip()
                except:
                    # Fallback just in case Gemini changes the formatting
                    rhyme_only = full_text
                
                # 2. Generate and save the audio
                audio_file_path = generate_audio(rhyme_only)
                
                # 3. Display audio player in the UI
                st.success("Audio generated successfully! 🎧")
                st.audio(audio_file_path, format="audio/mp3")
                
    with col2:
        if st.button("❌ Reject / Regenerate"):
            st.session_state.generated_text = None
            st.rerun()