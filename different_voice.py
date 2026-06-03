'''

def generate_voiceover(text: str, filename="raw_voice.mp3"):
    """Generates voiceover using Edge TTS, automatically choosing the correct language engine."""
    # Check if any character falls into the Devanagari Unicode block (Hindi alphabet)
    is_hindi = any('\u0900' <= char <= '\u097F' for char in text)
    
    if is_hindi:
        voice = "hi-IN-SwaraNeural" 
    else:
        voice = "en-US-AriaNeural" 
    
    asyncio.run(async_generate_audio(text, filename, voice))
    return filename

# --- 3. AUDIO MIXING (PYDUB) ---
def mix_audio(voice_file: str, bgm_file="bg_music.mp3", output_file="final_audio.mp3"):
    """Overlays the compiled full voiceover track onto a looping background track."""
    if not os.path.exists(bgm_file):
        st.warning(f"Background music '{bgm_file}' not found. Skipping mixing.")
        return voice_file
        
    voice = AudioSegment.from_mp3(voice_file)
    bgm = AudioSegment.from_mp3(bgm_file)
    
    bgm = bgm - 15  # Duck background track volume by 15dB
    
    while len(bgm) < len(voice):
        bgm += bgm
        
    bgm = bgm[:len(voice)]
    final_audio = bgm.overlay(voice)
    final_audio.export(output_file, format="mp3")
    return output_file
'''