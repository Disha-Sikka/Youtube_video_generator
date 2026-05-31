import os
import streamlit as st
from dotenv import load_dotenv
from google import genai
from elevenlabs.client import ElevenLabs # <-- NEW IMPORT

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
    
    Keep it to 2 or 3 short, energetic stanzas.
    
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

# --- NEW AUDIO FUNCTION ---
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

def generate_audio(text: str, filename="rhyme_audio.mp3"):
    """Converts text to high-quality cheerful speech using the new ElevenLabs SDK."""
    
    # Use the new .text_to_speech.convert() syntax
    audio_generator = eleven_client.text_to_speech.convert(
        text=text,
        voice_id="JBFqnCBsd6RMkjVDRZzb", # This is a default voice ID, you can change it later
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    
    # Save the audio generator to a file
    with open(filename, "wb") as f:
        # Check if the output is a generator (streaming) or bytes
        if hasattr(audio_generator, '__iter__') and not isinstance(audio_generator, bytes):
             for chunk in audio_generator:
                 f.write(chunk)
        else:
             f.write(audio_generator)
            
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