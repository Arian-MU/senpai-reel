"""
Audio Extraction and Transcription Pipeline
Extract audio from Instagram videos and transcribe speech/narration
Inspired by how ChatGPT analyzes video content through audio understanding
"""

import cv2
import whisper
import moviepy.editor as mp
import os
import json
import sqlite3
import numpy as np
from pathlib import Path
import librosa
import soundfile as sf
from datetime import datetime
import subprocess

class VideoAudioAnalyzer:
    """
    Extract and analyze audio from videos for content understanding
    Similar to how modern AI systems process video content
    """
    
    def __init__(self, db_path="video_audio_analysis.db"):
        self.db_path = db_path
        self.whisper_model = None
        self.init_database()
    
    def init_database(self):
        """Initialize database for audio analysis results"""
        conn = sqlite3.connect(self.db_path)
        
        # Table for audio metadata
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audio_metadata (
            video_id TEXT PRIMARY KEY,
            audio_duration REAL,
            sample_rate INTEGER,
            has_speech BOOLEAN,
            audio_energy REAL,
            dominant_frequency REAL,
            audio_file_path TEXT,
            extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Table for speech transcription
        conn.execute("""
        CREATE TABLE IF NOT EXISTS speech_transcription (
            video_id TEXT,
            segment_id INTEGER,
            start_time REAL,
            end_time REAL,
            text TEXT,
            confidence REAL,
            language TEXT,
            PRIMARY KEY (video_id, segment_id)
        )
        """)
        
        # Table for audio features
        conn.execute("""
        CREATE TABLE IF NOT EXISTS audio_features (
            video_id TEXT,
            timestamp REAL,
            mfcc_features TEXT,  -- JSON array of MFCC coefficients
            spectral_centroid REAL,
            spectral_rolloff REAL,
            zero_crossing_rate REAL,
            tempo REAL,
            PRIMARY KEY (video_id, timestamp)
        )
        """)
        
        conn.commit()
        conn.close()
    
    def extract_audio_from_video(self, video_path, output_dir="audio_extracts"):
        """Extract audio track from video file"""
        try:
            # Create output directory
            Path(output_dir).mkdir(exist_ok=True)
            
            # Get video filename without extension
            video_name = Path(video_path).stem
            audio_path = os.path.join(output_dir, f"{video_name}.wav")
            
            print(f"🎵 Extracting audio from {video_path}")
            
            # Use moviepy for audio extraction
            video = mp.VideoFileClip(video_path)
            
            if video.audio is None:
                print(f"⚠️ No audio track found in {video_path}")
                return None
            
            # Extract audio and save as WAV
            audio = video.audio
            audio.write_audiofile(audio_path, verbose=False, logger=None)
            
            # Clean up
            video.close()
            audio.close()
            
            print(f"✅ Audio extracted to {audio_path}")
            return audio_path
            
        except Exception as e:
            print(f"❌ Error extracting audio: {e}")
            return None
    
    def analyze_audio_properties(self, audio_path):
        """Analyze basic audio properties"""
        try:
            # Load audio with librosa
            y, sr = librosa.load(audio_path, sr=None)
            
            duration = len(y) / sr
            
            # Calculate audio energy (RMS)
            rms = librosa.feature.rms(y=y)[0]
            audio_energy = np.mean(rms)
            
            # Dominant frequency
            stft = librosa.stft(y)
            magnitude = np.abs(stft)
            freqs = librosa.fft_frequencies(sr=sr)
            dominant_freq_idx = np.argmax(np.sum(magnitude, axis=1))
            dominant_frequency = freqs[dominant_freq_idx]
            
            # Speech detection (simplified - based on frequency content)
            # Speech typically contains energy in 85-255 Hz (fundamental frequency)
            # and harmonics up to 8kHz
            speech_band = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            has_speech = np.mean(speech_band) > 500 and np.mean(speech_band) < 4000
            
            return {
                'duration': duration,
                'sample_rate': sr,
                'audio_energy': float(audio_energy),
                'dominant_frequency': float(dominant_frequency),
                'has_speech': bool(has_speech)
            }
            
        except Exception as e:
            print(f"❌ Error analyzing audio properties: {e}")
            return None
    
    def load_whisper_model(self, model_size="base"):
        """Load Whisper model for transcription"""
        if self.whisper_model is None:
            print(f"🤖 Loading Whisper {model_size} model...")
            try:
                self.whisper_model = whisper.load_model(model_size)
                print("✅ Whisper model loaded successfully")
            except Exception as e:
                print(f"❌ Error loading Whisper model: {e}")
                return False
        return True
    
    def transcribe_audio(self, audio_path):
        """Transcribe speech from audio using Whisper"""
        if not self.load_whisper_model():
            return None
        
        try:
            print(f"🎙️ Transcribing audio...")
            
            # Transcribe with Whisper
            result = self.whisper_model.transcribe(audio_path, word_timestamps=True)
            
            # Extract segments with timestamps
            transcription_segments = []
            
            for segment in result.get('segments', []):
                transcription_segments.append({
                    'start_time': segment.get('start', 0),
                    'end_time': segment.get('end', 0),
                    'text': segment.get('text', '').strip(),
                    'confidence': segment.get('no_speech_prob', 0.0),  # Lower is better
                    'language': result.get('language', 'unknown')
                })
            
            print(f"✅ Transcribed {len(transcription_segments)} segments")
            return {
                'segments': transcription_segments,
                'language': result.get('language', 'unknown'),
                'full_text': result.get('text', '')
            }
            
        except Exception as e:
            print(f"❌ Error transcribing audio: {e}")
            return None
    
    def extract_audio_features(self, audio_path, window_size=5.0):
        """Extract detailed audio features over time"""
        try:
            print(f"🔍 Extracting detailed audio features...")
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=None)
            duration = len(y) / sr
            
            # Calculate window parameters
            hop_length = 512
            window_samples = int(window_size * sr)
            
            features = []
            
            # Extract features in windows
            for start_sample in range(0, len(y), window_samples):
                end_sample = min(start_sample + window_samples, len(y))
                window_audio = y[start_sample:end_sample]
                
                if len(window_audio) < hop_length:
                    continue
                
                timestamp = start_sample / sr
                
                # MFCC features (mel-frequency cepstral coefficients)
                mfcc = librosa.feature.mfcc(y=window_audio, sr=sr, n_mfcc=13)
                mfcc_mean = np.mean(mfcc, axis=1).tolist()
                
                # Spectral features
                spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=window_audio, sr=sr))
                spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=window_audio, sr=sr))
                zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(window_audio))
                
                # Tempo estimation
                try:
                    tempo, _ = librosa.beat.beat_track(y=window_audio, sr=sr)
                except:
                    tempo = 0.0
                
                features.append({
                    'timestamp': timestamp,
                    'mfcc_features': mfcc_mean,
                    'spectral_centroid': float(spectral_centroid),
                    'spectral_rolloff': float(spectral_rolloff),
                    'zero_crossing_rate': float(zero_crossing_rate),
                    'tempo': float(tempo)
                })
            
            print(f"✅ Extracted features for {len(features)} windows")
            return features
            
        except Exception as e:
            print(f"❌ Error extracting audio features: {e}")
            return []
    
    def process_video_audio(self, video_path, video_id):
        """Complete audio analysis pipeline for a video"""
        print(f"\n🎬 AUDIO ANALYSIS PIPELINE")
        print(f"📹 Video: {video_path}")
        print(f"🆔 ID: {video_id}")
        print("=" * 50)
        
        results = {
            'video_id': video_id,
            'success': False,
            'audio_path': None,
            'metadata': None,
            'transcription': None,
            'features': None,
            'processing_time': 0
        }
        
        start_time = datetime.now()
        
        try:
            # Step 1: Extract audio
            audio_path = self.extract_audio_from_video(video_path)
            if not audio_path:
                print("❌ No audio found in video")
                return results
            
            results['audio_path'] = audio_path
            
            # Step 2: Analyze basic properties
            metadata = self.analyze_audio_properties(audio_path)
            if metadata:
                results['metadata'] = metadata
                print(f"📊 Audio Duration: {metadata['duration']:.1f}s")
                print(f"🎵 Sample Rate: {metadata['sample_rate']}Hz")
                print(f"🔊 Has Speech: {'Yes' if metadata['has_speech'] else 'No'}")
                print(f"💪 Audio Energy: {metadata['audio_energy']:.4f}")
            
            # Step 3: Transcribe if speech detected
            if metadata and metadata['has_speech']:
                print(f"\n🎙️ Speech detected! Transcribing...")
                transcription = self.transcribe_audio(audio_path)
                if transcription:
                    results['transcription'] = transcription
                    print(f"📝 Language: {transcription['language']}")
                    print(f"📄 Segments: {len(transcription['segments'])}")
                    if transcription['full_text']:
                        preview = transcription['full_text'][:100] + "..." if len(transcription['full_text']) > 100 else transcription['full_text']
                        print(f"💭 Preview: {preview}")
            
            # Step 4: Extract detailed features
            features = self.extract_audio_features(audio_path)
            if features:
                results['features'] = features
                print(f"🔍 Audio features extracted for {len(features)} time windows")
            
            # Step 5: Store in database
            self.store_audio_analysis(results)
            
            results['success'] = True
            
        except Exception as e:
            print(f"❌ Pipeline error: {e}")
        
        finally:
            processing_time = (datetime.now() - start_time).total_seconds()
            results['processing_time'] = processing_time
            print(f"\n⏱️ Total processing time: {processing_time:.1f}s")
        
        return results
    
    def store_audio_analysis(self, results):
        """Store analysis results in database"""
        if not results.get('success'):
            return
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            video_id = results['video_id']
            
            # Store metadata
            if results.get('metadata'):
                metadata = results['metadata']
                conn.execute("""
                    INSERT OR REPLACE INTO audio_metadata 
                    (video_id, audio_duration, sample_rate, has_speech, audio_energy, 
                     dominant_frequency, audio_file_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_id,
                    metadata['duration'],
                    metadata['sample_rate'], 
                    metadata['has_speech'],
                    metadata['audio_energy'],
                    metadata['dominant_frequency'],
                    results.get('audio_path', '')
                ))
            
            # Store transcription
            if results.get('transcription'):
                transcription = results['transcription']
                
                # Clear existing transcription for this video
                conn.execute("DELETE FROM speech_transcription WHERE video_id = ?", (video_id,))
                
                # Insert new segments
                for i, segment in enumerate(transcription['segments']):
                    conn.execute("""
                        INSERT INTO speech_transcription 
                        (video_id, segment_id, start_time, end_time, text, confidence, language)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video_id, i,
                        segment['start_time'],
                        segment['end_time'], 
                        segment['text'],
                        1.0 - segment['confidence'],  # Convert to confidence score
                        segment['language']
                    ))
            
            # Store audio features
            if results.get('features'):
                # Clear existing features
                conn.execute("DELETE FROM audio_features WHERE video_id = ?", (video_id,))
                
                # Insert new features
                for feature in results['features']:
                    conn.execute("""
                        INSERT INTO audio_features 
                        (video_id, timestamp, mfcc_features, spectral_centroid, 
                         spectral_rolloff, zero_crossing_rate, tempo)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        video_id,
                        feature['timestamp'],
                        json.dumps(feature['mfcc_features']),
                        feature['spectral_centroid'],
                        feature['spectral_rolloff'],
                        feature['zero_crossing_rate'],
                        feature['tempo']
                    ))
            
            conn.commit()
            print("✅ Analysis results stored in database")
            
        except Exception as e:
            print(f"❌ Database storage error: {e}")
        
        finally:
            conn.close()
    
    def get_video_audio_summary(self, video_id):
        """Get summary of audio analysis for a video"""
        conn = sqlite3.connect(self.db_path)
        
        # Get metadata
        metadata = conn.execute("""
            SELECT audio_duration, has_speech, audio_energy, dominant_frequency
            FROM audio_metadata WHERE video_id = ?
        """, (video_id,)).fetchone()
        
        # Get transcription summary
        transcription = conn.execute("""
            SELECT COUNT(*) as segment_count, language, 
                   GROUP_CONCAT(text, ' ') as full_text
            FROM speech_transcription WHERE video_id = ?
        """, (video_id,)).fetchone()
        
        # Get feature summary
        features = conn.execute("""
            SELECT COUNT(*) as feature_windows,
                   AVG(spectral_centroid) as avg_spectral_centroid,
                   AVG(tempo) as avg_tempo
            FROM audio_features WHERE video_id = ?
        """, (video_id,)).fetchone()
        
        conn.close()
        
        return {
            'metadata': metadata,
            'transcription': transcription,
            'features': features
        }

def main():
    """Demo of the audio analysis pipeline"""
    analyzer = VideoAudioAnalyzer()
    
    # Process the demo video
    video_path = "downloads/DRt0DAPEcv1.mp4"
    video_id = "demo_instagram_audio"
    
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        return
    
    # Run complete analysis
    results = analyzer.process_video_audio(video_path, video_id)
    
    if results['success']:
        print(f"\n🎉 AUDIO ANALYSIS COMPLETE!")
        print(f"🔗 This adds another dimension to your graph analysis:")
        print(f"   • Visual graph networks (existing)")
        print(f"   • Audio transcription and features (new)")
        print(f"   • Combined multimodal understanding")
        
        # Show summary
        summary = analyzer.get_video_audio_summary(video_id)
        print(f"\n📊 SUMMARY:")
        if summary['metadata']:
            duration, has_speech, energy, freq = summary['metadata']
            print(f"   🎵 Duration: {duration:.1f}s")
            print(f"   🎙️ Contains speech: {'Yes' if has_speech else 'No'}")
            print(f"   🔊 Audio energy: {energy:.4f}")
        
        if summary['transcription'] and summary['transcription'][0] > 0:
            segments, language, text = summary['transcription']
            print(f"   📝 Transcribed segments: {segments}")
            print(f"   🌍 Language: {language}")
            if text:
                preview = text[:150] + "..." if len(text) > 150 else text
                print(f"   💭 Content: {preview}")

if __name__ == "__main__":
    main()