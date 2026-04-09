import streamlit as st
import osmnx as ox
import networkx as nx
import folium
import streamlit.components.v1 as components

st.set_page_config(page_title="彰化路徑規劃器", layout="wide")

st.title("🗺️ 彰化縣路徑規劃系統")

# --- 側邊欄設定 ---
st.sidebar.header("座標設定")
start_lat = st.sidebar.number_input("起點緯度 (Lat)", value=24.0817, format="%.4f")
start_lon = st.sidebar.number_input("起點經度 (Lon)", value=120.5385, format="%.4f")
end_lat = st.sidebar.number_input("終點緯度 (Lat)", value=24.0786, format="%.4f")
end_lon = st.sidebar.number_input("終點經度 (Lon)", value=120.5485, format="%.4f")

st.sidebar.markdown("---")
dist_slider = st.sidebar.slider("搜尋範圍 (公尺)", 1000, 5000, 2500)

# --- 路徑規劃核心函式 ---
@st.cache_data(show_spinner="正在抓取地圖數據並計算路徑...")
def get_map_html(s_lat, s_lon, e_lat, e_lon, search_dist):
    # 1. 計算兩點中心座標，作為下載地圖的中心點
    center_lat = (s_lat + e_lat) / 2
    center_lon = (s_lon + e_lon) / 2
    
    # 2. 下載路網 (使用 drive 駕車模式)
    G = ox.graph_from_point((center_lat, center_lon), dist=search_dist, network_type='drive')
    
    # 3. 尋找最近節點
    orig_node = ox.distance.nearest_nodes(G, X=s_lon, Y=s_lat)
    dest_node = ox.distance.nearest_nodes(G, X=e_lon, Y=e_lat)
    
    # 4. 計算最短路徑 (Dijkstra 演算法)
    route = nx.shortest_path(G, orig_node, dest_node, weight='length')
    
    # 5. 提取路徑座標供 Folium 使用
    route_points = []
    for node in route:
        node_data = G.nodes[node]
        route_points.append((node_data['y'], node_data['x']))
    
    # 6. 建立 Folium 地圖物件
    m = folium.Map(location=[center_lat, center_lon], zoom_start=14)
    
    # 加入路徑線條
    folium.PolyLine(route_points, color='blue', weight=5, opacity=0.7).add_to(m)
    
    # 加入起點與終點標記
    folium.Marker([s_lat, s_lon], popup="起點", icon=folium.Icon(color='green')).add_to(m)
    folium.Marker([e_lat, e_lon], popup="終點", icon=folium.Icon(color='red')).add_to(m)
    
    # 回傳 HTML 字串
    return m._repr_html_()

# --- 主要顯示區 ---
col1, col2 = st.columns([3, 1])

with col2:
    st.write("### 狀態資訊")
    st.info(f"起點: `{start_lat}, {start_lon}`")
    st.info(f"終點: `{end_lat}, {end_lon}`")
    run_btn = st.button("🚀 開始規劃", use_container_width=True)

with col1:
    if run_btn:
        try:
            html_data = get_map_html(start_lat, start_lon, end_lat, end_lon, dist_slider)
            components.html(html_data, height=600)
            st.success("路徑規劃完成！")
        except Exception as e:
            st.error(f"規劃失敗: {e}")
            st.warning("提示：請嘗試調大側邊欄的「搜尋範圍」，或是檢查座標是否在陸地上。")
    else:
        st.info("👈 請在左側輸入座標，然後點擊「開始規劃」按鈕。")


