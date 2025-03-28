'''
class SpeechRecognitionWorker(QObject):
    """Worker for speech recognition running in a separate QThread with **Offline VAD** (Silero)."""

    listen_signal = pyqtSignal(str)
    transcription_signal = pyqtSignal(str)  # Signal to send transcription results
    error_signal = pyqtSignal(str)         # Signal for errors

    def __init__(self, recognizer, stop_event, vad_threshold=0.8):
        super().__init__()
        self.recognizer = recognizer
        self.stop_event = stop_event
        self.log = logging.getLogger(__name__)
        self.log.setLevel(SRC_LOG_LEVELS["AUDIO"])

        # Load **Silero VAD Model** for Offline Speech Detection
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                               model='silero_vad',
                                               force_reload=True,
                                               trust_repo=True)
        (self.get_speech_timestamps, self.save_audio, self.read_audio, self.VADIterator, *_) = utils

        self.vad_threshold = vad_threshold  # Adjust speech sensitivity (0.5 - 0.8 recommended)

    def detect_speech(self, audio_waveform, sample_rate):
        """
        Perform Voice Activity Detection (VAD) on the given audio waveform.
        """

        # 🔥 Convert Stereo to Mono
        if len(audio_waveform.shape) > 1:
            print(f"🔄 Converting Stereo ({audio_waveform.shape}) → Mono")
            audio_waveform = torch.mean(audio_waveform, dim=0, keepdim=True)

        # 🔹 Ensure correct sample rate
        if sample_rate != 16000:
            print(f"⚠️ Warning: Expected 16kHz, but got {sample_rate}Hz. Resampling is recommended.")

        # 🔹 Normalize and Amplify Audio (Avoids low volume issues)
        max_val = torch.max(torch.abs(audio_waveform))
        if max_val < 0.05:
            print(f"🔊 Audio signal is too quiet ({max_val:.5f}), amplifying...")
            audio_waveform = audio_waveform * 5  # Boost volume

        audio_waveform = audio_waveform / torch.max(torch.abs(audio_waveform))  # Normalize

        # 🔹 Debug Info
        print(f"🎤 Running VAD with Sample Rate: {sample_rate}Hz, Threshold: {self.vad_threshold}")

        # 🔥 Run VAD
        speech_timestamps = self.get_speech_timestamps(
            audio_waveform.squeeze(0),
            self.vad_model,
            sampling_rate=sample_rate,
            threshold=self.vad_threshold
        )

        # 🔥 If No Speech Detected, Reduce Threshold and Retry
        if not speech_timestamps:
            print("⚠️ No Speech Detected. Lowering threshold and retrying...")
            for new_threshold in [self.vad_threshold - 0.1, self.vad_threshold - 0.2]:
                print(f"🔽 Trying VAD with threshold: {new_threshold}")
                speech_timestamps = self.get_speech_timestamps(
                    audio_waveform.squeeze(0),
                    self.vad_model,
                    sampling_rate=sample_rate,
                    threshold=new_threshold
                )
                if speech_timestamps:
                    print(f"✅ Speech detected at lower threshold: {new_threshold}")
                    break

        if not speech_timestamps:
            print("🚨 Still No Speech Detected. Check microphone volume and try again.")

        return speech_timestamps

    def run(self):
        """Perform speech recognition with **Offline VAD**."""
        try:
            self.listen_signal.emit("Listening...")
            sample_rate = 16000  # Required sample rate for Silero VAD
            duration = 5  # Max recording duration in seconds

            self.log.info("Recording audio...")
            audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
            sd.wait()

            self.log.info("Analyzing speech activity...")
            speech_timestamps = self.detect_speech(torch.tensor(audio_data).to(self.device), sample_rate)

            if not speech_timestamps:
                self.error_signal.emit("No speech detected.")
                return

            # Extract speech segments from recorded audio
            speech_audio = np.concatenate([audio_data[timestamp['start']:timestamp['end']] for timestamp in speech_timestamps])

            # Convert audio to `AudioData` format for Whisper
            speech_audio = resample(speech_audio, len(speech_audio) * 2)  # Resample to 32kHz for Whisper
            audio_data = sr.AudioData(speech_audio.tobytes(), sample_rate, 2)

            self.listen_signal.emit("Recognizing...")
            transcription = self.recognizer.recognize_whisper(audio_data, model="large-v3-turbo")

            self.log.info(f"Transcription: {transcription}")
            self.transcription_signal.emit(transcription)

        except sr.UnknownValueError:
            self.log.error("Sorry, I didn't catch that.")
            self.error_signal.emit("Sorry, I didn't catch that.")
        except sr.RequestError as e:
            self.log.error(f"API error: {e}")
            self.error_signal.emit(f"API error: {e}")
'''