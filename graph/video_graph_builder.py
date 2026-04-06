"""
Video Graph Network Architecture
Inspired by assignment: Transform videos into rich graph representations
Instead of storing raw video files, create detailed graph networks per video
"""

import cv2
import networkx as nx
import json
import numpy as np
from datetime import timedelta
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Tuple
import hashlib

@dataclass
class VideoFrame:
    """Represents a single frame in the video graph"""
    timestamp: float
    frame_hash: str
    dominant_colors: List[Tuple[int, int, int]]
    brightness: float
    objects_detected: List[Dict]
    scene_type: str

@dataclass
class ObjectNode:
    """Represents a detected object across frames"""
    object_id: str
    object_type: str
    confidence: float
    bounding_box: Tuple[int, int, int, int]
    position_history: List[Tuple[float, int, int]]  # (timestamp, x, y)

@dataclass
class SceneTransition:
    """Represents transitions between scenes/shots"""
    from_frame: int
    to_frame: int
    transition_type: str  # 'cut', 'fade', 'pan', 'zoom'
    similarity_score: float

class VideoGraphBuilder:
    """
    Converts videos into graph networks capturing:
    - Frame-to-frame relationships
    - Object tracking and movement
    - Scene transitions and camera movements
    - Temporal patterns and rhythms
    """
    
    def __init__(self, video_path: str):
        self.video_path = video_path
        self.graph = nx.MultiDiGraph()  # Directed graph with multiple edge types
        self.frames = []
        self.objects = {}
        self.scene_transitions = []
        
    def extract_frame_features(self, frame, timestamp):
        """Extract rich features from a single frame"""
        # Convert to different color spaces for analysis
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Basic frame properties
        height, width = frame.shape[:2]
        
        # Color analysis
        dominant_colors = self.extract_dominant_colors(frame)
        brightness = np.mean(gray)
        
        # Edge density (indicates complexity)
        edges = cv2.Canny(gray, 50, 150)
        edge_density = np.sum(edges > 0) / (height * width)
        
        # Motion vectors (if previous frame exists)
        motion_vectors = self.calculate_motion_vectors(gray) if hasattr(self, 'prev_gray') else []
        
        # Frame hash for similarity detection
        frame_hash = self.calculate_frame_hash(gray)
        
        features = {
            'timestamp': timestamp,
            'frame_hash': frame_hash,
            'dominant_colors': dominant_colors,
            'brightness': brightness,
            'edge_density': edge_density,
            'motion_vectors': motion_vectors,
            'width': width,
            'height': height
        }
        
        self.prev_gray = gray
        return features
    
    def extract_dominant_colors(self, frame, k=3):
        """Extract dominant colors using k-means clustering"""
        # Reshape frame to be a list of pixels
        data = frame.reshape((-1, 3))
        data = np.float32(data)
        
        # Apply k-means clustering to find dominant colors
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(data, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
        
        # Convert back to uint8 and return as list of tuples
        centers = np.uint8(centers)
        return [tuple(color) for color in centers]
    
    def calculate_frame_hash(self, gray_frame):
        """Calculate perceptual hash for frame similarity"""
        # Resize to small size for hash calculation
        small = cv2.resize(gray_frame, (8, 8))
        avg = small.mean()
        hash_bits = small > avg
        return hashlib.md5(hash_bits.tobytes()).hexdigest()[:16]
    
    def calculate_motion_vectors(self, current_gray):
        """Calculate optical flow motion vectors"""
        if not hasattr(self, 'prev_gray'):
            return []
        
        # Calculate dense optical flow
        flow = cv2.calcOpticalFlowPyrLK(
            self.prev_gray, current_gray, 
            np.array([[100, 100]], dtype=np.float32),  # Sample points
            None
        )
        
        # Extract motion magnitude and direction
        if flow[0] is not None:
            motion_vectors = []
            for point in flow[0]:
                if point is not None:
                    motion_vectors.append({
                        'magnitude': float(np.linalg.norm(point)),
                        'direction': float(np.arctan2(point[1], point[0]))
                    })
            return motion_vectors
        return []
    
    def detect_scene_transitions(self):
        """Detect cuts, fades, and other scene transitions"""
        transitions = []
        
        for i in range(1, len(self.frames)):
            prev_frame = self.frames[i-1]
            curr_frame = self.frames[i]
            
            # Calculate frame similarity
            similarity = self.calculate_frame_similarity(
                prev_frame['frame_hash'], 
                curr_frame['frame_hash']
            )
            
            # Brightness change (for fade detection)
            brightness_change = abs(curr_frame['brightness'] - prev_frame['brightness'])
            
            # Determine transition type
            if similarity < 0.3:  # Low similarity = hard cut
                transition_type = 'cut'
            elif brightness_change > 50:  # Significant brightness change = fade
                transition_type = 'fade'
            elif self.has_camera_movement(prev_frame, curr_frame):
                transition_type = 'camera_movement'
            else:
                transition_type = 'none'
            
            if transition_type != 'none':
                transitions.append(SceneTransition(
                    from_frame=i-1,
                    to_frame=i,
                    transition_type=transition_type,
                    similarity_score=similarity
                ))
        
        return transitions
    
    def calculate_frame_similarity(self, hash1, hash2):
        """Calculate similarity between frame hashes"""
        # Simple hash distance (in real implementation, use perceptual hashing)
        if hash1 == hash2:
            return 1.0
        
        # Convert hashes to binary and calculate Hamming distance
        bin1 = bin(int(hash1, 16))[2:].zfill(64)
        bin2 = bin(int(hash2, 16))[2:].zfill(64)
        
        differences = sum(b1 != b2 for b1, b2 in zip(bin1, bin2))
        return 1.0 - (differences / 64.0)
    
    def has_camera_movement(self, prev_frame, curr_frame):
        """Detect camera panning, zooming, or tilting"""
        prev_motion = prev_frame.get('motion_vectors', [])
        curr_motion = curr_frame.get('motion_vectors', [])
        
        if not prev_motion or not curr_motion:
            return False
        
        # Calculate average motion magnitude
        avg_motion = np.mean([mv['magnitude'] for mv in curr_motion])
        return avg_motion > 5.0  # Threshold for significant movement
    
    def build_graph_network(self):
        """Build the complete graph network for the video"""
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = 0
        
        print(f"🎬 Building graph network for video...")
        
        # Process each frame
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_count / fps
            
            # Extract frame features
            features = self.extract_frame_features(frame, timestamp)
            self.frames.append(features)
            
            # Add frame node to graph
            node_id = f"frame_{frame_count}"
            self.graph.add_node(
                node_id,
                node_type='frame',
                timestamp=timestamp,
                **features
            )
            
            # Connect to previous frame (temporal edge)
            if frame_count > 0:
                prev_node = f"frame_{frame_count-1}"
                
                # Calculate frame-to-frame similarity
                similarity = self.calculate_frame_similarity(
                    self.frames[-2]['frame_hash'],
                    features['frame_hash']
                )
                
                self.graph.add_edge(
                    prev_node, node_id,
                    edge_type='temporal',
                    similarity=similarity,
                    time_delta=1/fps
                )
            
            frame_count += 1
            
            # Process every nth frame for efficiency
            if frame_count % 5 != 0:  # Process every 5th frame
                continue
        
        cap.release()
        
        # Detect scene transitions
        self.scene_transitions = self.detect_scene_transitions()
        
        # Add scene transition edges
        for transition in self.scene_transitions:
            from_node = f"frame_{transition.from_frame}"
            to_node = f"frame_{transition.to_frame}"
            
            self.graph.add_edge(
                from_node, to_node,
                edge_type='scene_transition',
                transition_type=transition.transition_type,
                similarity=transition.similarity_score
            )
        
        print(f"✅ Graph built: {len(self.graph.nodes)} nodes, {len(self.graph.edges)} edges")
        return self.graph
    
    def analyze_video_structure(self):
        """Analyze the structural patterns in the video"""
        analysis = {
            'total_frames': len(self.frames),
            'total_transitions': len(self.scene_transitions),
            'average_shot_length': 0,
            'dominant_colors_timeline': [],
            'brightness_profile': [],
            'motion_intensity_timeline': [],
            'scene_types': {}
        }
        
        # Calculate average shot length
        if self.scene_transitions:
            shot_lengths = []
            for i, transition in enumerate(self.scene_transitions):
                if i == 0:
                    shot_length = transition.from_frame
                else:
                    shot_length = transition.from_frame - self.scene_transitions[i-1].to_frame
                shot_lengths.append(shot_length)
            
            analysis['average_shot_length'] = np.mean(shot_lengths)
        
        # Extract timelines
        for frame in self.frames:
            analysis['brightness_profile'].append(frame['brightness'])
            
            # Motion intensity
            motion_vectors = frame.get('motion_vectors', [])
            if motion_vectors:
                avg_motion = np.mean([mv['magnitude'] for mv in motion_vectors])
                analysis['motion_intensity_timeline'].append(avg_motion)
            else:
                analysis['motion_intensity_timeline'].append(0)
        
        return analysis
    
    def export_graph_database(self, db_path):
        """Export graph to database for efficient querying"""
        conn = sqlite3.connect(db_path)
        
        # Create tables
        conn.execute('''
            CREATE TABLE IF NOT EXISTS video_graphs (
                video_id TEXT PRIMARY KEY,
                video_path TEXT,
                total_frames INTEGER,
                duration REAL,
                graph_data TEXT
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS frame_nodes (
                video_id TEXT,
                frame_id TEXT,
                timestamp REAL,
                brightness REAL,
                edge_density REAL,
                dominant_colors TEXT,
                motion_vectors TEXT,
                PRIMARY KEY (video_id, frame_id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS frame_edges (
                video_id TEXT,
                from_frame TEXT,
                to_frame TEXT,
                edge_type TEXT,
                similarity REAL,
                transition_type TEXT
            )
        ''')
        
        # Insert video graph data
        video_id = hashlib.md5(self.video_path.encode()).hexdigest()[:16]
        
        # Insert nodes
        for node, data in self.graph.nodes(data=True):
            if data.get('node_type') == 'frame':
                conn.execute('''
                    INSERT OR REPLACE INTO frame_nodes VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video_id, node, data['timestamp'], data['brightness'],
                    data['edge_density'], json.dumps(data['dominant_colors']),
                    json.dumps(data.get('motion_vectors', []))
                ))
        
        # Insert edges
        for from_node, to_node, data in self.graph.edges(data=True):
            conn.execute('''
                INSERT INTO frame_edges VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                video_id, from_node, to_node, data['edge_type'],
                data.get('similarity', 0), data.get('transition_type', '')
            ))
        
        # Insert video metadata
        analysis = self.analyze_video_structure()
        conn.execute('''
            INSERT OR REPLACE INTO video_graphs VALUES (?, ?, ?, ?, ?)
        ''', (
            video_id, self.video_path, analysis['total_frames'],
            analysis['total_frames'] / 30.0,  # Assuming 30fps
            json.dumps(nx.node_link_data(self.graph))
        ))
        
        conn.commit()
        conn.close()
        
        print(f"💾 Graph exported to database: {db_path}")
        return video_id

def main():
    # Example usage
    video_path = "downloads/DRt0DAPEcv1.mp4"  # Your downloaded video
    
    builder = VideoGraphBuilder(video_path)
    graph = builder.build_graph_network()
    
    # Analyze structure
    analysis = builder.analyze_video_structure()
    print(f"\n📊 Video Analysis:")
    print(f"   Total Frames: {analysis['total_frames']}")
    print(f"   Scene Transitions: {analysis['total_transitions']}")
    print(f"   Average Shot Length: {analysis['average_shot_length']:.1f} frames")
    
    # Export to database
    video_id = builder.export_graph_database("video_graphs.db")
    print(f"   Video Graph ID: {video_id}")

if __name__ == "__main__":
    main()