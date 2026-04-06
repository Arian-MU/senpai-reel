"""
Streamlit Graph Query Interface
Interactive interface for querying video graph networks
Brings academic assignment concept to life through interactive visualization
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from graph.video_graph_query_engine import VideoGraphQueryEngine
import pandas as pd
import json

st.set_page_config(page_title="🔍 Graph Query Engine", layout="wide")

@st.cache_resource
def get_query_engine():
    return VideoGraphQueryEngine("demo_video_graphs.db")

def plot_motion_timeline(motion_data):
    """Plot camera motion intensity over time"""
    if not motion_data['timeline']:
        st.warning("No motion data available")
        return
    
    df = pd.DataFrame(motion_data['timeline'])
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['motion_intensity'],
        mode='lines+markers',
        name='Motion Intensity',
        line=dict(color='#FF6B6B', width=2),
        marker=dict(size=4)
    ))
    
    # Add pattern annotations
    patterns = motion_data['patterns']
    for pattern_type, pattern_data in patterns.items():
        if pattern_data:
            y_values = [2.0 if pattern_type == 'static_shots' else 
                       10.0 if pattern_type == 'quick_cuts' else 5.0 
                       for _ in pattern_data]
            fig.add_trace(go.Scatter(
                x=[p['timestamp'] for p in pattern_data],
                y=y_values,
                mode='markers',
                name=pattern_type.replace('_', ' ').title(),
                marker=dict(size=8, symbol='diamond')
            ))
    
    fig.update_layout(
        title="Camera Motion Analysis",
        xaxis_title="Time (seconds)",
        yaxis_title="Motion Intensity",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_color_evolution(color_data):
    """Plot color evolution over time"""
    if not color_data['timeline']:
        st.warning("No color data available")
        return
    
    # Extract brightness timeline
    timestamps = [frame['timestamp'] for frame in color_data['timeline']]
    brightness = [frame['brightness'] for frame in color_data['timeline']]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps,
        y=brightness,
        mode='lines',
        name='Brightness',
        line=dict(color='#4ECDC4', width=2),
        fill='tonexty'
    ))
    
    # Mark significant color transitions
    transitions = color_data['color_transitions']
    if transitions:
        transition_times = [t['timestamp'] for t in transitions]
        transition_brightness = [brightness[timestamps.index(t)] for t in transition_times if t in timestamps]
        
        fig.add_trace(go.Scatter(
            x=transition_times,
            y=transition_brightness,
            mode='markers',
            name='Color Transitions',
            marker=dict(size=10, color='red', symbol='star')
        ))
    
    fig.update_layout(
        title="Color Evolution Analysis",
        xaxis_title="Time (seconds)",
        yaxis_title="Brightness",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_video_signature(signature):
    """Display video signature in a structured format"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🎬 Structural")
        st.metric("Total Shots", signature['structural_fingerprint']['total_shots'])
        st.metric("Avg Shot Length", f"{signature['structural_fingerprint']['avg_shot_length']:.1f} frames")
        st.info(f"**Pacing:** {signature['structural_fingerprint']['pacing_style'].replace('_', ' ').title()}")
    
    with col2:
        st.subheader("🎨 Visual")
        st.metric("Brightness Variance", f"{signature['visual_fingerprint']['brightness_variance']:.1f}")
        st.metric("Color Transitions", signature['visual_fingerprint']['color_transitions'])
        st.metric("Visual Motifs", signature['visual_fingerprint']['visual_motifs'])
    
    with col3:
        st.subheader("📹 Motion")
        st.metric("Movement Ratio", f"{signature['motion_fingerprint']['movement_ratio']:.1%}")
        st.metric("Pan Sequences", signature['motion_fingerprint']['movement_patterns'])

def main():
    st.title("🔍 Video Graph Query Engine")
    st.markdown("*Query and analyze video content through graph representations*")
    
    engine = get_query_engine()
    
    # Sidebar for video selection and query options
    with st.sidebar:
        st.header("Query Options")
        
        # Video ID input (in real app, this would be a dropdown of available videos)
        video_id = st.text_input("Video ID", value="demo_instagram_reel", help="Enter the ID of the video to analyze")
        
        st.divider()
        
        # Analysis type selection
        analysis_type = st.selectbox(
            "Analysis Type",
            ["Video Signature", "Motion Analysis", "Color Evolution", "Scene Structure", 
             "Visual Motifs", "Frame Similarity", "Video Comparison"]
        )
        
        # Additional parameters based on analysis type
        if analysis_type == "Frame Similarity":
            similarity_threshold = st.slider("Similarity Threshold", 0.0, 1.0, 0.8, 0.1)
        
        if analysis_type == "Video Comparison":
            video_id2 = st.text_input("Second Video ID", value="sample_video_2")
    
    # Main content area
    if st.button("🚀 Run Analysis", type="primary"):
        with st.spinner("Analyzing video graph..."):
            try:
                if analysis_type == "Video Signature":
                    signature = engine.generate_video_signature(video_id)
                    st.success("Video signature generated!")
                    display_video_signature(signature)
                    
                    # Show raw data in expander
                    with st.expander("Raw Signature Data"):
                        st.json(signature)
                
                elif analysis_type == "Motion Analysis":
                    motion_data = engine.analyze_camera_movement_patterns(video_id)
                    st.success("Motion analysis complete!")
                    
                    # Show summary metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Movement Time", motion_data['total_movement_time'])
                    with col2:
                        st.metric("Static Time", motion_data['static_time'])
                    with col3:
                        movement_ratio = motion_data['total_movement_time'] / (motion_data['total_movement_time'] + motion_data['static_time']) if (motion_data['total_movement_time'] + motion_data['static_time']) > 0 else 0
                        st.metric("Movement Ratio", f"{movement_ratio:.1%}")
                    
                    # Plot motion timeline
                    plot_motion_timeline(motion_data)
                    
                    # Show pattern breakdown
                    st.subheader("Movement Patterns")
                    pattern_df = pd.DataFrame([
                        {'Pattern': pattern_type.replace('_', ' ').title(), 
                         'Count': len(pattern_data)} 
                        for pattern_type, pattern_data in motion_data['patterns'].items()
                    ])
                    st.dataframe(pattern_df, use_container_width=True)
                
                elif analysis_type == "Color Evolution":
                    color_data = engine.analyze_color_evolution(video_id)
                    st.success("Color analysis complete!")
                    
                    # Show summary metrics
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Brightness Variance", f"{color_data['brightness_variance']:.1f}")
                    with col2:
                        st.metric("Color Transitions", len(color_data['color_transitions']))
                    
                    # Plot color evolution
                    plot_color_evolution(color_data)
                    
                    # Show color transitions
                    if color_data['color_transitions']:
                        st.subheader("Significant Color Transitions")
                        for i, transition in enumerate(color_data['color_transitions'][:5]):  # Show first 5
                            st.write(f"**Transition {i+1}** at {transition['timestamp']:.1f}s (Similarity: {transition['similarity']:.2f})")
                
                elif analysis_type == "Scene Structure":
                    scene_data = engine.query_scene_structure(video_id)
                    st.success("Scene structure analysis complete!")
                    
                    # Show summary metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Shots", scene_data['total_shots'])
                    with col2:
                        st.metric("Avg Shot Length", f"{scene_data['average_shot_length']:.1f} frames")
                    with col3:
                        st.metric("Shot Length Variance", f"{scene_data['shot_length_variance']:.1f}")
                    with col4:
                        pacing_style = scene_data['pacing_analysis'].get('pacing_style', 'unknown')
                        st.metric("Pacing Style", pacing_style.replace('_', ' ').title())
                    
                    # Plot shot length distribution
                    if scene_data['shot_lengths']:
                        fig = px.histogram(
                            x=scene_data['shot_lengths'], 
                            title="Shot Length Distribution",
                            labels={'x': 'Shot Length (frames)', 'y': 'Count'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    # Show pacing breakdown
                    pacing = scene_data['pacing_analysis']
                    if pacing:
                        st.subheader("Pacing Analysis")
                        pacing_df = pd.DataFrame([
                            {'Shot Type': 'Short (<1s)', 'Ratio': pacing.get('short_shots_ratio', 0)},
                            {'Shot Type': 'Medium (1-5s)', 'Ratio': pacing.get('medium_shots_ratio', 0)},
                            {'Shot Type': 'Long (>5s)', 'Ratio': pacing.get('long_shots_ratio', 0)}
                        ])
                        
                        fig = px.bar(pacing_df, x='Shot Type', y='Ratio', title="Shot Type Distribution")
                        st.plotly_chart(fig, use_container_width=True)
                
                elif analysis_type == "Visual Motifs":
                    motifs = engine.find_visual_motifs(video_id)
                    st.success(f"Found {len(motifs)} visual motifs!")
                    
                    if motifs:
                        for i, motif in enumerate(motifs[:3]):  # Show first 3 motifs
                            st.subheader(f"Motif {i+1}")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Occurrences", motif['count'])
                            with col2:
                                st.metric("Avg Brightness", f"{motif['avg_brightness']:.1f}")
                            with col3:
                                st.write(f"**Timestamps:** {', '.join([f'{t:.1f}s' for t in motif['timestamps'][:5]])}")
                            
                            # Show dominant colors
                            colors = motif['dominant_colors']
                            if colors:
                                color_squares = ""
                                for color in colors[:5]:  # Show first 5 colors
                                    color_squares += f'<span style="display:inline-block; width:20px; height:20px; background-color:rgb({color[0]},{color[1]},{color[2]}); margin:2px;"></span>'
                                st.markdown(f"**Dominant Colors:** {color_squares}", unsafe_allow_html=True)
                    else:
                        st.info("No recurring visual motifs found in this video.")
                
                elif analysis_type == "Frame Similarity":
                    patterns = engine.query_frame_similarity_patterns(video_id, similarity_threshold)
                    st.success(f"Found {len(patterns)} similar frame patterns!")
                    
                    if patterns:
                        # Show top patterns
                        st.subheader("Top Similar Frame Patterns")
                        pattern_df = pd.DataFrame(patterns[:10])  # Show top 10
                        pattern_df['time_gap'] = pattern_df['time_gap'].round(2)
                        pattern_df['similarity'] = pattern_df['similarity'].round(3)
                        st.dataframe(pattern_df, use_container_width=True)
                        
                        # Plot similarity distribution
                        fig = px.histogram(
                            x=[p['similarity'] for p in patterns],
                            title="Frame Similarity Distribution",
                            labels={'x': 'Similarity Score', 'y': 'Count'}
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No similar frame patterns found above the threshold.")
                
                elif analysis_type == "Video Comparison":
                    if video_id2:
                        comparison = engine.compare_videos(video_id, video_id2)
                        st.success("Video comparison complete!")
                        
                        # Show overall similarity
                        st.metric("Overall Similarity", f"{comparison['overall_similarity']:.1%}")
                        
                        # Show detailed similarity breakdown
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Structural Similarity", f"{comparison['structural_similarity']:.1%}")
                        with col2:
                            st.metric("Visual Similarity", f"{comparison['visual_similarity']:.1%}")
                        with col3:
                            st.metric("Motion Similarity", f"{comparison['motion_similarity']:.1%}")
                        
                        # Show signatures side by side
                        st.subheader("Video Signatures Comparison")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**{video_id}**")
                            st.json(comparison['signature1'])
                        with col2:
                            st.write(f"**{video_id2}**")
                            st.json(comparison['signature2'])
                    else:
                        st.error("Please provide a second video ID for comparison.")
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.info("Make sure you have video graph data in your database.")
    
    # Information section
    with st.expander("ℹ️ About Video Graph Queries"):
        st.markdown("""
        This query engine enables sophisticated video analysis through graph representations:
        
        **🎬 Scene Structure**: Analyze shot composition, transitions, and pacing patterns
        
        **🎨 Visual Analysis**: Track color evolution, brightness changes, and visual motifs
        
        **📹 Motion Patterns**: Detect camera movements, static shots, and dynamic sequences
        
        **🔍 Frame Similarity**: Find repeated visual patterns and content loops
        
        **📊 Video Signatures**: Generate unique fingerprints for content comparison
        
        **⚡ Benefits over raw video storage:**
        - 90% smaller storage footprint
        - Instant queryability without video processing
        - Rich semantic analysis capabilities
        - Cost-effective at scale
        """)

if __name__ == "__main__":
    main()