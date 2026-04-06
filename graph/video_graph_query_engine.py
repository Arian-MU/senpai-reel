"""
Video Graph Query Engine
Complex queries and analysis on video graph networks
Inspired by assignment: Enable sophisticated video content analysis through graph queries
"""

import sqlite3
import networkx as nx
import json
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
import plotly.graph_objects as go
import plotly.express as px

class VideoGraphQueryEngine:
    """
    Query engine for video graph networks
    Enables complex analysis without storing raw video files
    """
    
    def __init__(self, db_path="video_graphs.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
    
    def query_frame_similarity_patterns(self, video_id: str, similarity_threshold=0.8):
        """Find repeated visual patterns (similar frames)"""
        query = '''
            SELECT f1.frame_id as frame1, f2.frame_id as frame2, 
                   f1.timestamp as time1, f2.timestamp as time2,
                   e.similarity
            FROM frame_edges e
            JOIN frame_nodes f1 ON e.from_frame = f1.frame_id AND e.video_id = f1.video_id
            JOIN frame_nodes f2 ON e.to_frame = f2.frame_id AND e.video_id = f2.video_id
            WHERE e.video_id = ? AND e.similarity > ? AND e.edge_type != 'temporal'
            ORDER BY e.similarity DESC
        '''
        
        results = self.conn.execute(query, (video_id, similarity_threshold)).fetchall()
        
        patterns = []
        for row in results:
            patterns.append({
                'frame1': row[0],
                'frame2': row[1],
                'time1': row[2],
                'time2': row[3],
                'similarity': row[4],
                'time_gap': abs(row[3] - row[2])
            })
        
        return patterns
    
    def analyze_camera_movement_patterns(self, video_id: str):
        """Analyze camera movement and shot composition patterns"""
        query = '''
            SELECT frame_id, timestamp, motion_vectors
            FROM frame_nodes
            WHERE video_id = ? AND motion_vectors != '[]'
            ORDER BY timestamp
        '''
        
        results = self.conn.execute(query, (video_id,)).fetchall()
        
        movement_timeline = []
        for row in results:
            motion_data = json.loads(row[2])
            if motion_data:
                avg_magnitude = np.mean([mv['magnitude'] for mv in motion_data])
                movement_timeline.append({
                    'timestamp': row[1],
                    'motion_intensity': avg_magnitude,
                    'frame_id': row[0]
                })
        
        # Detect movement patterns
        patterns = self.detect_movement_patterns(movement_timeline)
        
        return {
            'timeline': movement_timeline,
            'patterns': patterns,
            'total_movement_time': len([m for m in movement_timeline if m['motion_intensity'] > 2.0]),
            'static_time': len([m for m in movement_timeline if m['motion_intensity'] <= 2.0])
        }
    
    def detect_movement_patterns(self, timeline):
        """Detect specific camera movement patterns"""
        patterns = {
            'static_shots': [],
            'pan_sequences': [],
            'quick_cuts': [],
            'zoom_sequences': []
        }
        
        for i in range(len(timeline)):
            intensity = timeline[i]['motion_intensity']
            
            if intensity < 1.0:
                patterns['static_shots'].append(timeline[i])
            elif intensity > 10.0:
                patterns['quick_cuts'].append(timeline[i])
            elif 3.0 < intensity < 8.0:
                patterns['pan_sequences'].append(timeline[i])
        
        return patterns
    
    def analyze_color_evolution(self, video_id: str):
        """Analyze how colors change throughout the video"""
        query = '''
            SELECT timestamp, dominant_colors, brightness
            FROM frame_nodes
            WHERE video_id = ?
            ORDER BY timestamp
        '''
        
        results = self.conn.execute(query, (video_id,)).fetchall()
        
        color_timeline = []
        brightness_timeline = []
        
        for row in results:
            colors = json.loads(row[1])
            color_timeline.append({
                'timestamp': row[0],
                'dominant_colors': colors,
                'color_diversity': len(set(tuple(c) for c in colors)),
                'brightness': row[2]
            })
            brightness_timeline.append(row[2])
        
        # Analyze color patterns
        analysis = {
            'timeline': color_timeline,
            'brightness_profile': brightness_timeline,
            'brightness_variance': np.var(brightness_timeline),
            'color_transitions': self.detect_color_transitions(color_timeline)
        }
        
        return analysis
    
    def detect_color_transitions(self, color_timeline):
        """Detect significant color palette changes"""
        transitions = []
        
        for i in range(1, len(color_timeline)):
            prev_colors = set(tuple(c) for c in color_timeline[i-1]['dominant_colors'])
            curr_colors = set(tuple(c) for c in color_timeline[i]['dominant_colors'])
            
            # Calculate color similarity
            intersection = len(prev_colors & curr_colors)
            union = len(prev_colors | curr_colors)
            similarity = intersection / union if union > 0 else 0
            
            if similarity < 0.5:  # Significant color change
                transitions.append({
                    'timestamp': color_timeline[i]['timestamp'],
                    'similarity': similarity,
                    'prev_colors': list(prev_colors),
                    'new_colors': list(curr_colors)
                })
        
        return transitions
    
    def query_scene_structure(self, video_id: str):
        """Analyze the overall scene structure and pacing"""
        transition_query = '''
            SELECT from_frame, to_frame, transition_type, similarity
            FROM frame_edges
            WHERE video_id = ? AND edge_type = 'scene_transition'
            ORDER BY from_frame
        '''
        
        transitions = self.conn.execute(transition_query, (video_id,)).fetchall()
        
        # Calculate shot lengths
        shot_lengths = []
        transition_types = []
        
        for i, (from_frame, to_frame, t_type, similarity) in enumerate(transitions):
            from_frame_num = int(from_frame.split('_')[1])
            to_frame_num = int(to_frame.split('_')[1])
            
            shot_length = to_frame_num - from_frame_num
            shot_lengths.append(shot_length)
            transition_types.append(t_type)
        
        analysis = {
            'total_shots': len(transitions),
            'shot_lengths': shot_lengths,
            'average_shot_length': np.mean(shot_lengths) if shot_lengths else 0,
            'shot_length_variance': np.var(shot_lengths) if shot_lengths else 0,
            'transition_types': transition_types,
            'pacing_analysis': self.analyze_pacing(shot_lengths)
        }
        
        return analysis
    
    def analyze_pacing(self, shot_lengths):
        """Analyze the pacing and rhythm of the video"""
        if not shot_lengths:
            return {}
        
        # Classify shots by length
        short_shots = len([s for s in shot_lengths if s < 30])  # < 1 second at 30fps
        medium_shots = len([s for s in shot_lengths if 30 <= s <= 150])  # 1-5 seconds
        long_shots = len([s for s in shot_lengths if s > 150])  # > 5 seconds
        
        total = len(shot_lengths)
        
        return {
            'short_shots_ratio': short_shots / total,
            'medium_shots_ratio': medium_shots / total,
            'long_shots_ratio': long_shots / total,
            'pacing_style': self.classify_pacing_style(short_shots/total, medium_shots/total, long_shots/total)
        }
    
    def classify_pacing_style(self, short_ratio, medium_ratio, long_ratio):
        """Classify the overall pacing style of the video"""
        if short_ratio > 0.6:
            return "fast_paced"
        elif long_ratio > 0.5:
            return "slow_paced"
        elif medium_ratio > 0.6:
            return "steady_paced"
        else:
            return "mixed_pacing"
    
    def find_visual_motifs(self, video_id: str):
        """Find recurring visual motifs and patterns"""
        # Get all frames with their features
        query = '''
            SELECT frame_id, timestamp, dominant_colors, brightness, edge_density
            FROM frame_nodes
            WHERE video_id = ?
            ORDER BY timestamp
        '''
        
        frames = self.conn.execute(query, (video_id,)).fetchall()
        
        # Group frames by visual similarity
        motifs = []
        processed_frames = set()
        
        for i, frame1 in enumerate(frames):
            if frame1[0] in processed_frames:
                continue
            
            similar_frames = [frame1]
            colors1 = json.loads(frame1[2])
            
            for j, frame2 in enumerate(frames[i+1:], i+1):
                if frame2[0] in processed_frames:
                    continue
                
                colors2 = json.loads(frame2[2])
                
                # Calculate visual similarity
                color_similarity = self.calculate_color_similarity(colors1, colors2)
                brightness_similarity = 1 - abs(frame1[3] - frame2[3]) / 255.0
                
                overall_similarity = (color_similarity + brightness_similarity) / 2
                
                if overall_similarity > 0.8:
                    similar_frames.append(frame2)
                    processed_frames.add(frame2[0])
            
            if len(similar_frames) > 2:  # Motif needs at least 3 instances
                motifs.append({
                    'frames': similar_frames,
                    'count': len(similar_frames),
                    'timestamps': [f[1] for f in similar_frames],
                    'avg_brightness': np.mean([f[3] for f in similar_frames]),
                    'dominant_colors': colors1
                })
                
                for frame in similar_frames:
                    processed_frames.add(frame[0])
        
        return motifs
    
    def calculate_color_similarity(self, colors1, colors2):
        """Calculate similarity between two color palettes"""
        if not colors1 or not colors2:
            return 0
        
        # Convert to numpy arrays for easier computation
        c1 = np.array(colors1)
        c2 = np.array(colors2)
        
        # Calculate minimum distances between colors
        similarities = []
        for color1 in c1:
            min_distance = float('inf')
            for color2 in c2:
                # Euclidean distance in RGB space
                distance = np.sqrt(np.sum((color1 - color2) ** 2))
                min_distance = min(min_distance, distance)
            
            # Convert distance to similarity (0-1 scale)
            similarity = 1 - (min_distance / (255 * np.sqrt(3)))
            similarities.append(max(0, similarity))
        
        return np.mean(similarities)
    
    def generate_video_signature(self, video_id: str):
        """Generate a unique signature/fingerprint for the video"""
        # Get key structural features
        scene_analysis = self.query_scene_structure(video_id)
        color_analysis = self.analyze_color_evolution(video_id)
        movement_analysis = self.analyze_camera_movement_patterns(video_id)
        motifs = self.find_visual_motifs(video_id)
        
        signature = {
            'structural_fingerprint': {
                'total_shots': scene_analysis['total_shots'],
                'avg_shot_length': scene_analysis['average_shot_length'],
                'pacing_style': scene_analysis['pacing_analysis'].get('pacing_style', 'unknown')
            },
            'visual_fingerprint': {
                'brightness_variance': color_analysis['brightness_variance'],
                'color_transitions': len(color_analysis['color_transitions']),
                'visual_motifs': len(motifs)
            },
            'motion_fingerprint': {
                'movement_ratio': movement_analysis['total_movement_time'] / 
                                (movement_analysis['total_movement_time'] + movement_analysis['static_time'])
                                if (movement_analysis['total_movement_time'] + movement_analysis['static_time']) > 0 else 0,
                'movement_patterns': len(movement_analysis['patterns']['pan_sequences'])
            }
        }
        
        return signature
    
    def compare_videos(self, video_id1: str, video_id2: str):
        """Compare two videos based on their graph signatures"""
        sig1 = self.generate_video_signature(video_id1)
        sig2 = self.generate_video_signature(video_id2)
        
        # Calculate similarity scores
        structural_sim = self.calculate_structural_similarity(
            sig1['structural_fingerprint'], 
            sig2['structural_fingerprint']
        )
        
        visual_sim = self.calculate_visual_similarity(
            sig1['visual_fingerprint'], 
            sig2['visual_fingerprint']
        )
        
        motion_sim = self.calculate_motion_similarity(
            sig1['motion_fingerprint'], 
            sig2['motion_fingerprint']
        )
        
        overall_similarity = (structural_sim + visual_sim + motion_sim) / 3
        
        return {
            'overall_similarity': overall_similarity,
            'structural_similarity': structural_sim,
            'visual_similarity': visual_sim,
            'motion_similarity': motion_sim,
            'signature1': sig1,
            'signature2': sig2
        }
    
    def calculate_structural_similarity(self, s1, s2):
        """Calculate structural similarity between two video signatures"""
        # Normalize and compare key metrics
        shot_diff = abs(s1['total_shots'] - s2['total_shots']) / max(s1['total_shots'], s2['total_shots'], 1)
        length_diff = abs(s1['avg_shot_length'] - s2['avg_shot_length']) / max(s1['avg_shot_length'], s2['avg_shot_length'], 1)
        pacing_match = 1.0 if s1['pacing_style'] == s2['pacing_style'] else 0.0
        
        return 1 - ((shot_diff + length_diff) / 2) * 0.7 + pacing_match * 0.3
    
    def calculate_visual_similarity(self, v1, v2):
        """Calculate visual similarity between two video signatures"""
        brightness_diff = abs(v1['brightness_variance'] - v2['brightness_variance']) / max(v1['brightness_variance'], v2['brightness_variance'], 1)
        transition_diff = abs(v1['color_transitions'] - v2['color_transitions']) / max(v1['color_transitions'], v2['color_transitions'], 1)
        motif_diff = abs(v1['visual_motifs'] - v2['visual_motifs']) / max(v1['visual_motifs'], v2['visual_motifs'], 1)
        
        return 1 - (brightness_diff + transition_diff + motif_diff) / 3
    
    def calculate_motion_similarity(self, m1, m2):
        """Calculate motion similarity between two video signatures"""
        movement_diff = abs(m1['movement_ratio'] - m2['movement_ratio'])
        pattern_diff = abs(m1['movement_patterns'] - m2['movement_patterns']) / max(m1['movement_patterns'], m2['movement_patterns'], 1)
        
        return 1 - (movement_diff + pattern_diff) / 2

def main():
    # Example usage of the query engine
    engine = VideoGraphQueryEngine()
    
    # Assuming you have video graphs in the database
    video_id = "your_video_id_here"  # Replace with actual video ID
    
    print("🔍 Video Graph Analysis")
    print("=" * 50)
    
    # Analyze scene structure
    scene_analysis = engine.query_scene_structure(video_id)
    print(f"Scene Analysis:")
    print(f"  Total shots: {scene_analysis['total_shots']}")
    print(f"  Average shot length: {scene_analysis['average_shot_length']:.1f} frames")
    print(f"  Pacing style: {scene_analysis['pacing_analysis'].get('pacing_style', 'unknown')}")
    
    # Analyze visual patterns
    motifs = engine.find_visual_motifs(video_id)
    print(f"\nVisual Motifs: {len(motifs)} found")
    
    # Generate video signature
    signature = engine.generate_video_signature(video_id)
    print(f"\nVideo Signature:")
    print(f"  Structural: {signature['structural_fingerprint']}")
    print(f"  Visual: {signature['visual_fingerprint']}")
    print(f"  Motion: {signature['motion_fingerprint']}")

if __name__ == "__main__":
    main()