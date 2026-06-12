import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests
import json

# ページの初期設定
st.set_page_config(page_title="ゴミマップ・コレクション", layout="wide")

# 🔴 【重要】ここにあなたのGoogleのウェブアプリURLを貼り付けてください！
GAS_URL = "https://script.google.com/macros/s/AKfycbzt_EtBmvvtMUojg--G6eLylj_3EPCZThskFkNnaJRoiYdbRyOf50mcceG00YV_S0Mm/exec"

# データの読み込み機能（Googleスプレッドシートから取得）
if 'trash_data' not in st.session_state:
    try:
        response = requests.get(GAS_URL)
        data = response.json()
        if len(data) > 0:
            st.session_state.trash_data = pd.DataFrame(data[1:], columns=data[0])
            st.session_state.trash_data['lat'] = pd.to_numeric(st.session_state.trash_data['lat'])
            st.session_state.trash_data['lng'] = pd.to_numeric(st.session_state.trash_data['lng'])
        else:
            raise Exception("空のデータ")
    except Exception as e:
        st.session_state.trash_data = pd.DataFrame(columns=[
            'lat', 'lng', 'trash_tags', 'specific_place', 'time_zone'
        ])

# 💡 タップされた位置を一時保存するセッション変数を初期化
if 'click_pos' not in st.session_state:
    st.session_state.click_pos = None

# スプレッドシートへ保存する関数
def save_to_google_sheets(df):
    header = [df.columns.tolist()]
    values = df.values.tolist()
    all_data = header + values
    requests.post(GAS_URL, data=json.dumps(all_data))

st.title("🗑️ ポイ捨てゴミ マップ情報収集アプリ (共有版)")
st.write("地図をクリックすると**その場にすぐ仮のピンが刺さります**。右側で詳細を入力して登録してください！")

# マップの初期位置設定（熊本駅周辺）
START_LAT, START_LNG = 32.7898, 130.6892

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ マップ")
    m = folium.Map(location=[START_LAT, START_LNG], zoom_start=14, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google")

    # 1. すでに登録されているゴミの場所をマップに「赤色」でピン表示
    for idx, row in st.session_state.trash_data.iterrows():
        popup_html = f"""
        <div style='font-family: sans-serif; min-width: 180px;'>
            <h4 style='margin: 0 0 5px 0; color: #d32f2f;'>🗑️ ゴミの情報</h4>
            <b>🏷️ 種類:</b> {row['trash_tags']}<br>
            <b>📍 場所:</b> {row['specific_place']}<br>
            <b>⏰ 時間帯:</b> {row['time_zone']}
        </div>
        """
        folium.Marker(
            [row['lat'], row['lng']],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color='red', icon='trash', prefix='fa')
        ).add_to(m)

    # 2. 💡 【新機能】タップされた瞬間の場所に「青色」の仮ピンを刺す
    if st.session_state.click_pos:
        folium.Marker(
            [st.session_state.click_pos['lat'], st.session_state.click_pos['lng']],
            popup="ここに入力中...",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(m)

    # 地図の描画
    map_data = st_folium(m, width="100%", height=600)

    # 3. 💡 地図がタップされたら、即座に仮ピンの位置を更新して画面を再描画
    clicked_coords = map_data.get('last_clicked')
    if clicked_coords:
        # 前回の位置と違う場合だけ更新（無限ループ防止）
        if st.session_state.click_pos is None or \
           abs(st.session_state.click_pos['lat'] - clicked_coords['lat']) > 1e-5 or \
           abs(st.session_state.click_pos['lng'] - clicked_coords['lng']) > 1e-5:
            st.session_state.click_pos = clicked_coords
            st.rerun()

with col2:
    st.subheader("📝 タグ情報の入力")
    
    # 💡 一時保存されている仮ピンの位置情報を使う
    if st.session_state.click_pos:
        lat = st.session_state.click_pos['lat']
        lng = st.session_state.click_pos['lng']
        st.info(f"📍 選択された位置\n緯度: {lat:.5f} / 経度: {lng:.5f}")
        
        with st.form(key='trash_form', clear_on_submit=True):
            trash_tags = st.multiselect(
                "① ゴミの種類（複数選択可）", 
                ["プラスチック製容器包装","ペットボトル", "空き缶","ビン", "タバコ・吸殻", "新聞紙・雑誌","紙くず "その他"]
            )
            specific_place = st.text_input("② 具体的な場所はどこですか？", placeholder="例：自動販売機の隙間")
            time_zone = st.selectbox("③ 見つけた時間帯", ["早朝 (5:00 ~ 9:00)", "昼間 (9:00 ~ 17:00)", "夕方 (17:00 ~ 20:00)", "夜間・深夜 (20:00 ~ 5:00)"])
            submit_button = st.form_submit_button(label='この場所にピンを刺す')
            
            if submit_button:
                if not trash_tags:
                    st.error("ゴミの種類を1つ以上選択してください。")
                elif not specific_place:
                    st.error("具体的な場所を入力してください。")
                else:
                    tags_str = ", ".join(trash_tags)
                    new_data = pd.DataFrame([{
                        'lat': lat, 'lng': lng, 'trash_tags': tags_str, 'specific_place': specific_place, 'time_zone': time_zone
                    }])
                    st.session_state.trash_data = pd.concat([st.session_state.trash_data, new_data], ignore_index=True)
                    
                    save_to_google_sheets(st.session_state.trash_data)
                    
                    # 💡 登録が完了したら、仮ピン（青）のデータをリセット
                    st.session_state.click_pos = None
                    
                    st.success("Googleスプレッドシートに保存しました！確定ピン（赤）に切り替わります。")
                    st.rerun()
    else:
        st.warning("まずは左の地図上で、ゴミを見つけた場所をクリックしてください。その場所に仮のピンが刺さります。")

st.markdown("---")
st.subheader("📊 収集されたデータ一覧（ここでの編集・削除も即座に同期されます）")

edited_df = st.data_editor(
    st.session_state.trash_data,
    width="stretch",
    num_rows="dynamic",
    column_config={
        "lat": st.column_config.NumberColumn("緯度", disabled=True),
        "lng": st.column_config.NumberColumn("経度", disabled=True),
        "trash_tags": "ゴミの種類",
        "specific_place": "具体的な場所",
        "time_zone": "時間帯"
    }
)

if not edited_df.equals(st.session_state.trash_data):
    st.session_state.trash_data = edited_df
    save_to_google_sheets(st.session_state.trash_data)
    st.rerun()
