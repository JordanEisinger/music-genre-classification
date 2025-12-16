import librosa
import numpy as np

class KeyDetector:
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
            correlations.append((keys[i] + ' major', major_corr))
            correlations.append((keys[i] + ' minor', minor_corr))
        
        # Find the key with the highest correlation score
        best_key, best_corr = max(correlations, key=lambda x: x[1])
        
        # Convert correlation from [-1, 1] range to [0, 1] range for easier interpretation
        confidence = (best_corr + 1) / 2  # Convert -1,1 range to 0,1 range
        
        return best_key, confidence