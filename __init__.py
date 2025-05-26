import speech_recognition as sr
import webrtcvad
import pyaudio
import collections
import time
# Audio configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 8000  # Use 8kHz to reduce processing (webrtcvad supports 8kHz, 16kHz, 24kHz, 32kHz)
CHUNK = 160  # 20ms at 8kHz (webrtcvad supports 10ms, 20ms, 30ms frames)
VAD_MODE = 3  # Aggressiveness mode (0-3, 3 is most aggressive)
# Initialize VAD
vad = webrtcvad.Vad()
vad.set_mode(VAD_MODE)
# Ring buffer to store audio frames (~1.5 seconds)
RING_BUFFER_SIZE = 75  # 75 * 20ms = 1.5 seconds
ring_buffer = collections.deque(maxlen=RING_BUFFER_SIZE)
# Speech detection variables
is_speech_active = False
speech_start_time = None
MIN_SPEECH_DURATION = 5  # Minimum speech duration in seconds
SILENCE_TIMEOUT = 1.0  # Seconds of silence before stopping
def is_speech_frame(frame, sample_rate):
    """Check if the audio frame contains speech using webrtcvad."""
    return vad.is_speech(frame, sample_rate)
recognizer = sr.Recognizer()
def recognize_speech(audio_data):
    """Transcribe audio data using speech recognition."""
    audio = sr.AudioData(audio_data, RATE, 2)  # 2 bytes per sample
    try:
        # Using Google's speech recognition (requires internet)
        text = recognizer.recognize_whisper(audio,model="medium")
        print(f"Transcription: {text}")
    except sr.UnknownValueError:
        print("Could not understand audio")
    except sr.RequestError as e:
        print(f"Recognition error: {e}")

    # For fully offline recognition, use Whisper (uncomment below)
    """
    import whisper
    model = whisper.load_model("tiny")  # Load Whisper model (e.g., tiny, base, small)
    result = model.transcribe(audio_data, fp16=False)
    print(f"Whisper Transcription: {result['text']}")
    """
def process_audio():
    """Process audio chunks and perform speech recognition."""
    global is_speech_active, speech_start_time

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("Listening... Press Ctrl+C to stop.")
    try:
        while True:
            frame = stream.read(CHUNK, exception_on_overflow=False)
            ring_buffer.append(frame)

            # Check if the frame contains speech
            is_speech = is_speech_frame(frame, RATE)

            if is_speech and not is_speech_active:
                # Speech detected
                is_speech_active = True
                speech_start_time = time.time()
                print("Speech started...")

            elif is_speech_active:
                if is_speech:
                    # Reset silence timer
                    speech_start_time = time.time()
                elif time.time() - speech_start_time > SILENCE_TIMEOUT:
                    # Silence detected, process the buffered audio
                    is_speech_active = False
                    print("Speech ended. Processing...")

                    # Combine buffered audio
                    audio_data = b''.join(ring_buffer)

                    # Recognize speech (sequential, no threading)
                    recognize_speech(audio_data)

    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()