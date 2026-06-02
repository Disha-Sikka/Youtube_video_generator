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
