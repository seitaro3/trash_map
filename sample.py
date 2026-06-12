import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import requests
import json

# ページの初期設定
st.set_page_config(page_title="ゴミマップ・コレクション", layout="wide")

# 🔴 【重要】ここに先ほどコピーしたGoogleのウェブアプリURLを貼り付けてください！
GAS_URL = "https://script.google.com/macros/s/AKfycbzt_EtBmvvtMUojg--G6eLylj_3EPCZThskFkNnaJRoiYdbRyOf50mcceG00YV_S0Mm/exec"


# データの読み込み機能（Googleスプレッドシートから取得）
if 'trash_data' not in st.session_state:
    try:
        response = requests.get(GAS_URL)
        data = response.json()
        if len(data) > 0:
            # 1行目をヘッダー、2行目以降をデータとして読み込む
            st.session_state.trash_data = pd.DataFrame(data[1:], columns=data[0])
            # 緯度経度を数値型に戻す
            st.session_state.trash_data['lat'] = pd.to_numeric(st.session_state.trash_data['lat'])
            st.session_state.trash_data['lng'] = pd.to_numeric(st.session_state.trash_data['lng'])
        else:
            raise Exception("空のデータ")
    except Exception as e:
        # スプレッドシートが空の場合の初期化
        st.session_state.trash_data = pd.DataFrame(columns=[
            'lat', 'lng', 'trash_tags', 'specific_place', 'time_zone'
        ])

# スプレッドシートへ保存する関数
def save_to_google_sheets(df):
    # ヘッダーとデータをまとめてリストにする
    header = [df.columns.tolist()]
    values = df.values.tolist()
    all_data = header + values
    # GASに送信
    requests.post(GAS_URL, data=json.dumps(all_data))

st.title("🗑️ ポイ捨てゴミ マップ情報収集アプリ (共有版)")
st.write("地図をクリックしてピンを刺すと、**全員のGoogleスプレッドシートにリアルタイムで保存**されます！")

# マップの初期位置設定（熊本駅周辺）
START_LAT, START_LNG = 32.7898, 130.6892

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("🗺️ マップ")
    m = folium.Map(location=[START_LAT, START_LNG], zoom_start=14, tiles="https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}", attr="Google"
)

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

    map_data = st_folium(m, width="100%", height=600)

with col2:
    st.subheader("📝 タグ情報の入力")
    clicked_coords = map_data.get('last_clicked')

    if clicked_coords:
        lat = clicked_coords['lat']
        lng = clicked_coords['lng']
        st.info(f"📍 選択された位置\n緯度: {lat:.5f} / 経度: {lng:.5f}")
        
        with st.form(key='trash_form', clear_on_submit=True):
            trash_tags = st.multiselect(
                "① ゴミの種類（複数選択可）", 
                ["プラスチック・ペットボトル", "缶・ビン", "タバコ・吸殻", "空き弁当・紙類", "その他"]
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
                    
                    # Googleスプレッドシートへ保存！
                    save_to_google_sheets(st.session_state.trash_data)
                    st.success("Googleスプレッドシートに保存しました！")
                    st.rerun()
    else:
        st.warning("まずは左の地図上で、ゴミを見つけた場所をクリックしてください。")

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
    # 変更があったらGoogleスプレッドシートへ上書き保存！
    save_to_google_sheets(st.session_state.trash_data)
    st.rerun()