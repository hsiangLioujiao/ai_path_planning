import time
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
# import seaborn as sns
import streamlit as st
import osmnx as ox
import networkx as nx
import folium


pd.options.mode.copy_on_write = True
fm.fontManager.addfont('TaipeiSansTCBeta-Regular.ttf')
plt.rcParams["font.size"] = 14
plt.rcParams['font.family'] = 'Taipei Sans TC Beta'
st.set_page_config(page_title="功能打樣版 僅供3人同時使用", page_icon = "random", layout="wide")


# 彰化火車站座標(24.0817, 120.5385)
# 車輛中心座標(24.0622, 120.3856)
if "start_node" not in st.session_state:
    st.session_state.start_node = pd.DataFrame([{"名稱": "車輛中心", "緯度": 24.0622, "經度": 120.3856}])
# 洋厝座標(24.09934869695348, 120.45080839620647)
if "mid_nodes" not in st.session_state:
    st.session_state.mid_nodes = pd.DataFrame({"名稱":["洋厝"], "緯度":[24.0993], "經度":[120.4508]})
# 八卦山大佛座標(24.0786, 120.5485)
# 線西座標(24.1333, 120.4642)
if "end_node" not in st.session_state:
    st.session_state.end_node = pd.DataFrame([{"名稱": "線西", "緯度": 24.1333, "經度": 120.4642}])
if 'path_planning' not in st.session_state:
    st.session_state.path_planning = False
if 'dist_meters' not in st.session_state:
    st.session_state.dist_meters = 0
if 'map_html' not in st.session_state:
    st.session_state.map_html = None




@st.cache_data(show_spinner="正在抓取地圖數據並計算路徑...")
def get_route_data(coords_list, search_dist):
    """
    coords_list: 格式為 [(lat1, lon1), (lat2, lon2), ...] 的串列
    search_dist: 搜尋範圍(公尺)
    """

    # 計算所有點的中心點
    all_lats = [c[0] for c in coords_list]
    all_lons = [c[1] for c in coords_list]
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)
    
    # 下載路網(使用 drive 駕車模式)
    G = ox.graph_from_point((center_lat, center_lon), dist=search_dist, network_type='drive')
    G = ox.add_edge_speeds(G) # 補齊缺失速限(使用預設補齊邏輯)'speed_kph'
    G = ox.add_edge_travel_times(G)
    print("完成路網下載")
    
    # 逐段規劃路徑
    full_route = []
    total_distance = 0
    for i in range(len(coords_list) - 1):
        s_lat, s_lon = coords_list[i]
        e_lat, e_lon = coords_list[i+1]
        
        # 尋找最近的節點(舊版本參數順序可能不同，建議明確指定 X, Y)
        orig_node = ox.distance.nearest_nodes(G, X=s_lon, Y=s_lat)
        dest_node = ox.distance.nearest_nodes(G, X=e_lon, Y=e_lat)
        print("完成最近節點尋找")
        
        # 計算最短路徑(Dijkstra 演算法)與路徑長度
        sub_route = nx.shortest_path(G, orig_node, dest_node, weight='length') # 會回傳一個包含節點編號的串列，例如：[102, 105, 210, ...]。
        sub_dist = nx.shortest_path_length(G, orig_node, dest_node, weight='length') # 公尺
        print("完成最短路徑規劃")
        
        if not full_route:
            full_route.extend(sub_route)
        else:
            full_route.extend(sub_route[1:]) # 避免轉折節點重複
        total_distance += sub_dist
    
    # 透過route連續節點編號，查詢圖資物件中的邊資料(Edge Data)
    for u, v in zip(full_route[:-1], full_route[1:]):
        edge_info = G.get_edge_data(u, v)[0] # 若為MultiDiGraph(OSMNX預設)，需取index 0
        length = edge_info.get('length') # 距離(公尺)
        speed = edge_info.get('maxspeed') # 道路等級速限(可能為字串或列表)
        filling_speed = edge_info.get('speed_kph')
        name = edge_info.get('name') # 路名
        print(f"從節點 {u} 到 {v}：路名 {name}, 距離 {length:.1f}m, 速限 {speed}→{filling_speed}")
    

    # ##########################
    # 將圖資路徑轉換為GeoDataFrame
    print()
    print(ox.graph_to_gdfs(G, nodes=False)[['highway', 'speed_kph', 'travel_time']].head(10))
    route_gdf = ox.routing.route_to_gdf(G, full_route)
    route_gdf.to_csv(".//data//test_gdf.csv", encoding= 'utf-8-sig', index=False)

    
    # 從圖資路徑提取節點(緯度, 經度)
    route_points = [(G.nodes[n]['y'], G.nodes[n]['x']) for n in full_route] # 最終產生一個Tuple的串列，例如：[(24.1, 120.6), (24.11, 120.62), ...]。

    
    # 使用folium 繪製地圖，建立地圖中心、畫出路徑線條、加入起點與終點標記
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12) # 14
    folium.PolyLine(route_points, color='blue', weight=5, opacity=0.5).add_to(m)

    # 標記所有點位
    # for i, (lat, lon) in enumerate(coords_list):
        # if i == 0:
            # color = 'green'
            # label = "起點"
        # elif i == len(coords_list) - 1:
            # color = 'red'
            # label = "終點"
        # else:
            # color = 'orange'
            # label = f"經過點 {i}"
        
        # folium.Marker(
            # [lat, lon], 
            # popup=label, 
            # icon=folium.Icon(color=color, icon='info-sign')
        # ).add_to(m)    
    for i, (lat, lon) in enumerate(coords_list):
        color = 'green' if i == 0 else ('red' if i == len(coords_list)-1 else 'orange')
        folium.Marker([lat, lon], icon=folium.Icon(color=color)).add_to(m)
        
    return m._repr_html_(), total_distance




st.title("🗺️ 大貨車行駛路徑規劃及用油量預測")


st.sidebar.header("座標設定")
st.sidebar.write("📍 **設定起點**")
edit_start = st.sidebar.data_editor(
    st.session_state.start_node, 
    num_rows="fixed", 
    hide_index=True,
    key="edit_start"
)

st.sidebar.write("➕ **新增上下貨載點**")
edit_mid = st.sidebar.data_editor(
    st.session_state.mid_nodes, 
    num_rows="dynamic", 
    hide_index=True,
    key="edit_mid"
)

st.sidebar.write("🏁 **設定終點**")
edit_end = st.sidebar.data_editor(
    st.session_state.end_node, 
    num_rows="fixed", 
    hide_index=True,
    key="edit_end"
)

full_df = pd.concat([edit_start, edit_mid, edit_end], ignore_index=True)
coords_list = list(zip(full_df['緯度'], full_df['經度']))


st.sidebar.markdown("---")
dist_slider = st.sidebar.slider("**搜尋範圍** (公尺)", 1000, 10000, 5000)


col1, col2 = st.columns([1, 2])
with col1:
    st.write("### 狀態資訊")
    st.info(f"已設定 `{len(coords_list)}` 個地點")
    run_btn = st.button("🚀 開始規劃及預測", use_container_width=True)

    if st.session_state.path_planning:
        # 顯示預測結果
        st.metric("**規劃行駛距離**", f"{st.session_state.dist_meters/1000:.2f} km")
        # 假設油耗 5 km/L
        fuel_est = (st.session_state.dist_meters/1000) / 5 
        st.metric("**預估用油量**", f"{fuel_est:.2f} L")

with col2:
    if run_btn:
        if len(coords_list) < 2:
            st.error("請至少設定兩個座標（起點與終點）。")
        else:
            try:
                html_data, dist_meters = get_route_data(coords_list, dist_slider)
                st.success("路徑規劃完成！")            
                st.iframe(html_data, height=350)
                st.session_state.path_planning = True
                st.session_state.map_html = html_data
                st.session_state.dist_meters = dist_meters              
                st.rerun() 
            except Exception as e:
                st.error(f"規劃失敗: {e}")
                st.warning("提示：請嘗試調大側邊欄的「搜尋範圍」，或是檢查座標是否在陸地上。")
    else:
        if not st.session_state.path_planning:
            st.info("👈 請在左側欄位輸入座標，然後點擊「開始規劃及預測」按鈕。")

    if st.session_state.map_html:
        st.success("路徑規劃完成！")
        st.iframe(st.session_state.map_html, height=350)     

if st.session_state.map_html:
    st.write("**參考資料：**")
    st.write("Boeing, G. (2025). Modeling and Analyzing Urban Networks and Amenities with OSMnx. Geographical Analysis 57 (4), 567-577. doi:10.1111/gean.70009")
