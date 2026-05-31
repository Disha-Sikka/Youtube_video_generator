import os
import streamlit as st
from dotenv import load_dotenv
from google import genai

# 1. Load the environment variables from the .env file
load_dotenv()

# 2. Initialize the Gemini Client
# It will now automatically grab the GEMINI_API_KEY loaded by dotenv
client = genai.Client()

def generate_rhyme_and_prompts(topic: str):
    """
    Sends a structured prompt to Gemini to return a rhyme and 
    corresponding image generation descriptions.
    """
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

# --- Streamlit UI Setup ---
st.title("🤖 Kids Rhyme Video Engine")
st.subheader("Step 1: Content Generation & Verification")

# Input from user
topic_input = st.text_input("Enter a topic for the rhyme (e.g., 'A happy little sea turtle'):")

# Initialize session state to store generated content across button clicks
if "generated_text" not in st.session_state:
    st.session_state.generated_text = None

if st.button("Generate Script & Prompts"):
    if topic_input:
        with st.spinner("Generating creative ideas..."):
            try:
                result = generate_rhyme_and_prompts(topic_input)
                st.session_state.generated_text = result
            except Exception as e:
                st.error(f"Error calling API: {e}")
    else:
        st.warning("Please enter a topic first!")

# Display results if they exist in session state
if st.session_state.generated_text:
    st.markdown("### 📋 Generated Output")
    st.text_area("Raw AI Output (Review carefully)", st.session_state.generated_text, height=250)
    
    # Action buttons for the next stage of the pipeline
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Approve & Proceed to Video/Audio Generation", type="primary"):
            st.success("Moving to the next stage! (We will hook up the asset generation here next).")
            
    with col2:
        if st.button("❌ Reject / Regenerate"):
            st.session_state.generated_text = None
            st.rerun()