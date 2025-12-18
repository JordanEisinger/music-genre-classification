import librosa
import numpy as np

class SongDetector:
    def __init__(self):
        # Initialize any models or constants
        pass
    
    def detect_key(self, audio_path):
        y, sr = librosa.load(audio_path) # Load the audio file into a numpy array (y) and get its sample rate (sr)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr) # Extract chroma features - represents the intensity of each of the 12 pitches
        chroma_mean = np.mean(chroma, axis=1) # Average the chroma across all time frames to get a single 12-value vecto gives us the overall pitch class distribution for the entire song
        
        # Krumhansl-Schmuckler key profiles 
        # Empirically derived weights showing how "presence" of each pitch class is in major and minor keys
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 
                                2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                                2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        # List of all 12 possible keys (using flats)
        keys = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
        
        # Calculate correlation for all keys
        correlations = []
        for i in range(12):
            # Rotate profiles for each key
            major_rotated = np.roll(major_profile, i)
            minor_rotated = np.roll(minor_profile, i)
            
            # Calculate Pearson correlation between the song's chroma and major/minor profile
            major_corr = np.corrcoef(chroma_mean, major_rotated)[0, 1]
            minor_corr = np.corrcoef(chroma_mean, minor_rotated)[0, 1]
            
            # Add both major and minor possibilities for this root note
            correlations.append((keys[i] + ' Major', major_corr))
            correlations.append((keys[i] + ' Minor', minor_corr))
        
        # Find the key with the highest correlation score
        best_key, best_corr = max(correlations, key=lambda x: x[1])
        
        # Convert correlation from [-1, 1] range to [0, 1] range for easier interpretation
        confidence = (best_corr + 1) / 2  # Convert -1,1 range to 0,1 range
        
        return best_key, confidence

    def detect_tempo(self, audio_path):
        """
        Detect tempo with confidence score.
        
        Returns:
            tuple: (tempo, confidence)
                tempo: float - BPM
                confidence: float - 0.0 to 1.0
        """

        # Load audio and detect tempo/beats
        y, sr = librosa.load(audio_path)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        
        # Convert tempo to scalar if needed
        if isinstance(tempo, np.ndarray):
            tempo = float(tempo[0]) if len(tempo) > 0 else 100.0
        else:
            tempo = float(tempo)
        
        # Calculate confidence from beat consistency
        if len(beat_frames) > 2:
            # Convert beat frame numbers to actual times
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            
            # Calculate intervals between consecutive beats
            intervals = np.diff(beat_times)
            
            # Calculate coefficient of variation (lower = more consistent)
            mean_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            
            if mean_interval > 0:
                cv = std_interval / mean_interval
                # Convert to confidence: consistent beats = high confidence
                confidence = np.clip(1.0 - (cv * 2.0), 0.0, 1.0)
            else:
                confidence = 0.5
        else:
            # Too few beats detected
            confidence = 0.3
        
        return tempo, confidence

    def detect_time_signature(self, audio_path):
        """
        Detect time signature using downbeat detection.
        
        Returns:
            tuple: (time_signature, confidence)
        """
        
        # Load audio
        y, sr = librosa.load(audio_path)
        
        # Get onset strength
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Detect tempo and beats
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr
        )
        
        if len(beat_frames) < 8:
            return "4/4", 0.3
        
        # Get beat times
        beat_times = librosa.frames_to_time(beat_frames, sr=sr)
        
        # Calculate beat intervals
        intervals = np.diff(beat_times)
        median_interval = np.median(intervals)
        
        # Analyze onset strength at beats
        beat_strengths = onset_env[beat_frames]
        
        # Find peaks in beat strength (potential downbeats)
        from scipy.signal import find_peaks
        
        # Peaks that are significantly stronger than neighbors
        peaks, properties = find_peaks(
            beat_strengths,
            prominence=np.std(beat_strengths) * 0.5
        )
        
        if len(peaks) < 2:
            return "4/4", 0.4
        
        # Calculate distances between peaks (in number of beats)
        peak_distances = np.diff(peaks)
        
        # Most common distance suggests beats per bar
        if len(peak_distances) > 0:
            # Find most common distance
            unique, counts = np.unique(peak_distances, return_counts=True)
            most_common_distance = unique[np.argmax(counts)]
            consistency = np.max(counts) / len(peak_distances)
            
            # Map distance to time signature
            if most_common_distance == 4:
                time_sig = "4/4"
            elif most_common_distance == 3:
                time_sig = "3/4"
            elif most_common_distance == 2:
                time_sig = "2/4"
            elif most_common_distance == 6:
                time_sig = "6/8"
            elif most_common_distance == 5:
                time_sig = "5/4"
            else:
                time_sig = "4/4"  # Default
            
            # Confidence based on consistency
            confidence = np.clip(consistency, 0.0, 1.0)
        else:
            time_sig = "4/4"
            confidence = 0.4
        
        return time_sig, confidence