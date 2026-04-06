"""
Video Graph Visualization
Create an interactive network graph showing frame relationships
"""

import sqlite3
import networkx as nx
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots

def create_video_graph_visualization():
    """Create an interactive visualization of the video graph network"""
    
    st.title("🕸️ Video Graph Network Visualization")
    st.markdown("*See your Instagram video as an actual graph network*")
    
    # Load graph data
    try:
        conn = sqlite3.connect("demo_video_graphs.db")
        
        # Get frame nodes
        frames = conn.execute("""
            SELECT frame_id, timestamp, brightness, edge_density
            FROM frame_nodes 
            WHERE video_id = 'demo_instagram_reel'
            ORDER BY timestamp
        """).fetchall()
        
        # Get edges
        edges = conn.execute("""
            SELECT from_frame, to_frame, similarity, transition_type
            FROM frame_edges 
            WHERE video_id = 'demo_instagram_reel'
        """).fetchall()
        
        conn.close()
        
        if not frames:
            st.error("No graph data found. Please run the video conversion first.")
            st.code("python demo_video_graph.py")
            return
            
        st.success(f"📊 Loaded {len(frames)} nodes and {len(edges)} edges")
        
    except Exception as e:
        st.error(f"Error loading graph data: {e}")
        return
    
    # Create NetworkX graph
    G = nx.DiGraph()
    
    # Add nodes with attributes
    for frame_id, timestamp, brightness, edge_density in frames:
        G.add_node(frame_id, 
                  timestamp=timestamp,
                  brightness=brightness, 
                  edge_density=edge_density)
    
    # Add edges
    for from_frame, to_frame, similarity, transition_type in edges:
        G.add_edge(from_frame, to_frame, 
                  similarity=similarity,
                  transition_type=transition_type)
    
    # Graph analysis tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🌐 Network View", "📈 Timeline Graph", "🎯 Node Analysis", "📊 Statistics"])
    
    with tab1:
        st.header("Network Visualization")
        
        # Layout options
        layout_option = st.selectbox(
            "Choose Graph Layout:",
            ["spring", "circular", "kamada_kawai", "shell"]
        )
        
        # Generate layout
        if layout_option == "spring":
            pos = nx.spring_layout(G, k=1, iterations=50)
        elif layout_option == "circular":
            pos = nx.circular_layout(G)
        elif layout_option == "kamada_kawai":
            pos = nx.kamada_kawai_layout(G)
        else:
            pos = nx.shell_layout(G)
        
        # Create node traces
        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        node_sizes = []
        
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            
            # Get node attributes
            attrs = G.nodes[node]
            timestamp = attrs.get('timestamp', 0)
            brightness = attrs.get('brightness', 0)
            complexity = attrs.get('edge_density', 0)
            
            node_text.append(f"Frame: {node}<br>Time: {timestamp:.1f}s<br>Brightness: {brightness:.1f}<br>Complexity: {complexity:.4f}")
            node_colors.append(brightness)  # Color by brightness
            node_sizes.append(max(10, complexity * 5000))  # Size by complexity
        
        # Create edge traces
        edge_x = []
        edge_y = []
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])
        
        # Create the plot
        fig = go.Figure()
        
        # Add edges
        fig.add_trace(go.Scatter(
            x=edge_x, y=edge_y,
            line=dict(width=0.5, color='#888'),
            hoverinfo='none',
            mode='lines',
            name='Temporal Connections'
        ))
        
        # Add nodes
        fig.add_trace(go.Scatter(
            x=node_x, y=node_y,
            mode='markers',
            hoverinfo='text',
            text=node_text,
            marker=dict(
                showscale=True,
                colorscale='Viridis',
                reversescale=True,
                color=node_colors,
                size=node_sizes,
                colorbar=dict(
                    thickness=15,
                    len=0.5,
                    x=1.02,
                    title="Brightness"
                ),
                line=dict(width=2, color='white')
            ),
            name='Video Frames'
        ))
        
        fig.update_layout(
            title=f'Video Graph Network ({len(frames)} frames)',
            title_font_size=16,
            showlegend=True,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[ dict(
                text="Node size = Visual Complexity<br>Node color = Brightness",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002,
                xanchor="left", yanchor="bottom",
                font=dict(color="#888", size=12)
            )],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=600
        )
        
        st.plotly_chart(fig, width='stretch')
        
        # Network statistics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Nodes", len(G.nodes()))
        with col2:
            st.metric("Edges", len(G.edges()))
        with col3:
            density = nx.density(G)
            st.metric("Network Density", f"{density:.3f}")
        with col4:
            avg_degree = sum(dict(G.degree()).values()) / len(G.nodes()) if G.nodes() else 0
            st.metric("Avg Degree", f"{avg_degree:.1f}")
    
    with tab2:
        st.header("Timeline Graph View")
        st.markdown("*Video frames arranged by timestamp showing temporal flow*")
        
        # Create timeline visualization
        df_frames = pd.DataFrame(frames, columns=['frame_id', 'timestamp', 'brightness', 'edge_density'])
        
        # Create subplot with secondary y-axis
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        
        # Add brightness trace
        fig.add_trace(
            go.Scatter(
                x=df_frames['timestamp'],
                y=df_frames['brightness'],
                mode='lines+markers',
                name='Brightness',
                line=dict(color='gold', width=2),
                marker=dict(size=6)
            ),
            secondary_y=False,
        )
        
        # Add complexity trace
        fig.add_trace(
            go.Scatter(
                x=df_frames['timestamp'],
                y=df_frames['edge_density'],
                mode='lines+markers',
                name='Visual Complexity',
                line=dict(color='red', width=2),
                marker=dict(size=6)
            ),
            secondary_y=True,
        )
        
        # Update layout
        fig.update_xaxes(title_text="Time (seconds)")
        fig.update_yaxes(title_text="Brightness", secondary_y=False)
        fig.update_yaxes(title_text="Visual Complexity", secondary_y=True)
        
        fig.update_layout(
            title="Video Content Evolution Over Time",
            height=500,
            showlegend=True
        )
        
        st.plotly_chart(fig, width='stretch')
        
        # Show temporal connections
        st.subheader("Temporal Edge Analysis")
        
        if edges:
            edge_df = pd.DataFrame(edges, columns=['from_frame', 'to_frame', 'similarity', 'transition_type'])
            
            # Similarity distribution
            fig_sim = px.histogram(edge_df, x='similarity', bins=20, 
                                 title="Frame-to-Frame Similarity Distribution")
            st.plotly_chart(fig_sim, width='stretch')
            
            # Show some example edges
            st.subheader("Sample Temporal Connections")
            sample_edges = edge_df.head(10)
            st.dataframe(sample_edges)
    
    with tab3:
        st.header("Individual Node Analysis")
        
        # Node selector
        frame_ids = [f[0] for f in frames]
        selected_frame = st.selectbox("Select a frame to analyze:", frame_ids)
        
        if selected_frame:
            # Get node data
            node_data = next((f for f in frames if f[0] == selected_frame), None)
            
            if node_data:
                frame_id, timestamp, brightness, edge_density = node_data
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("Frame Properties")
                    st.metric("Frame ID", frame_id)
                    st.metric("Timestamp", f"{timestamp:.2f}s")
                    st.metric("Brightness", f"{brightness:.1f}/255")
                    st.metric("Visual Complexity", f"{edge_density:.4f}")
                
                with col2:
                    st.subheader("Network Position")
                    
                    # Get neighbors
                    predecessors = list(G.predecessors(selected_frame))
                    successors = list(G.successors(selected_frame))
                    
                    st.write(f"**Incoming connections:** {len(predecessors)}")
                    if predecessors:
                        st.write(", ".join(predecessors[:3]) + ("..." if len(predecessors) > 3 else ""))
                    
                    st.write(f"**Outgoing connections:** {len(successors)}")
                    if successors:
                        st.write(", ".join(successors[:3]) + ("..." if len(successors) > 3 else ""))
                
                # Show context in video
                st.subheader("Temporal Context")
                
                # Get surrounding frames
                frame_idx = frame_ids.index(selected_frame)
                context_start = max(0, frame_idx - 2)
                context_end = min(len(frame_ids), frame_idx + 3)
                
                context_frames = []
                for i in range(context_start, context_end):
                    f = frames[i]
                    context_frames.append({
                        'Frame': f[0],
                        'Time': f"{f[1]:.1f}s",
                        'Brightness': f"{f[2]:.1f}",
                        'Current': "👉" if f[0] == selected_frame else ""
                    })
                
                st.dataframe(pd.DataFrame(context_frames), hide_index=True)
    
    with tab4:
        st.header("Graph Statistics & Insights")
        
        # Basic stats
        st.subheader("Network Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Nodes", len(G.nodes()))
            st.metric("Total Edges", len(G.edges()))
            
        with col2:
            density = nx.density(G)
            st.metric("Network Density", f"{density:.4f}")
            
            # Connectivity
            if nx.is_connected(G.to_undirected()):
                st.metric("Connected", "Yes ✅")
            else:
                st.metric("Connected", "No ❌")
                
        with col3:
            # Path metrics
            try:
                diameter = nx.diameter(G.to_undirected()) if nx.is_connected(G.to_undirected()) else "N/A"
                st.metric("Diameter", diameter)
                
                avg_path = nx.average_shortest_path_length(G.to_undirected()) if nx.is_connected(G.to_undirected()) else "N/A"
                st.metric("Avg Path Length", f"{avg_path:.2f}" if avg_path != "N/A" else "N/A")
            except:
                st.metric("Diameter", "N/A")
                st.metric("Avg Path Length", "N/A")
        
        # Content analysis
        st.subheader("Content Analysis")
        
        df_frames = pd.DataFrame(frames, columns=['frame_id', 'timestamp', 'brightness', 'edge_density'])
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Brightness Distribution**")
            fig_bright = px.box(df_frames, y='brightness', title="Brightness Range")
            fig_bright.update_layout(height=300)
            st.plotly_chart(fig_bright, width='stretch')
            
        with col2:
            st.write("**Complexity Distribution**")
            fig_complex = px.box(df_frames, y='edge_density', title="Visual Complexity Range")
            fig_complex.update_layout(height=300)
            st.plotly_chart(fig_complex, width='stretch')
        
        # Key insights
        st.subheader("🎯 Key Graph Insights")
        
        avg_brightness = df_frames['brightness'].mean()
        max_complexity_frame = df_frames.loc[df_frames['edge_density'].idxmax()]
        
        insights = [
            f"📊 **Average Brightness:** {avg_brightness:.1f}/255 ({'Dark' if avg_brightness < 85 else 'Bright'} content)",
            f"🎨 **Most Complex Frame:** {max_complexity_frame['frame_id']} at {max_complexity_frame['timestamp']:.1f}s",
            f"🔗 **Network Structure:** {'Linear' if density < 0.1 else 'Complex'} temporal flow",
            f"⏱️ **Duration:** {df_frames['timestamp'].max():.1f} seconds analyzed",
            f"📈 **Sampling Efficiency:** {len(frames)} frames represent full {77:.1f}s video"
        ]
        
        for insight in insights:
            st.write(insight)

if __name__ == "__main__":
    create_video_graph_visualization()