import streamlit as st
import pandas as pd
import math
import folium
from streamlit_folium import st_folium
import base64


st.set_page_config(
    page_title="Market Proximity Analyzer",
    page_icon="logo.png",
    layout="wide"
)

st.markdown(
    r"""
    <style>
        div.block-container {
                padding-top: 2.5rem !important;
            }
        .stApp {
            max-width: 100vw;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }
        .stApp > div {
            width: 100%;
        }
        .stAppDeployButton {display:none;};
        .stAppHeader {padding-top: 10px;}
        .streamlit-dataframe thead th {
            font-weight: bold;
            }
    </style>
    """,
    unsafe_allow_html=True,
)


def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Radius of the Earth in km
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad

    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    distance = R * c
    return distance

def get_all_distances_sorted(excel_file, input_market_name):
    try:
        df = pd.read_excel(excel_file)
    except FileNotFoundError:
        st.error(f"Error: Excel file '{excel_file}' not found.")
        return None
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")
        return None

    required_columns = ['Market', 'Latitude', 'Longitude', 'Active MRs','Manager']
    for col in required_columns:
        if col not in df.columns:
            st.error(f"Error: The Excel file must contain a column named '{col}'.")
            return None

    df['Market'] = df['Market'].str.strip()
    df['Latitude'] = df['Latitude'].round(6)
    df['Longitude'] = df['Longitude'].round(6)
    df_unique = df.drop_duplicates(subset=['Market', 'Latitude', 'Longitude'], keep='first').copy()

    input_market_row = df_unique[df_unique['Market'] == input_market_name]

    if input_market_row.empty:
        st.error(f"Error: Market '{input_market_name}' not found in the Excel file.")
        return None

    input_lat = input_market_row['Latitude'].iloc[0]
    input_lon = input_market_row['Longitude'].iloc[0]

    distances = []
    for index, row in df_unique.iterrows():
        current_market = row['Market']
        if current_market != input_market_name:
            distance = calculate_distance(input_lat, input_lon, row['Latitude'], row['Longitude'])
            distance_mile = distance * 0.621371
            active_mrs = row['Active MRs']
            manager= row['Manager']
            distances.append((current_market, distance_mile, row['Latitude'], row['Longitude'], active_mrs, manager))

    sorted_distances = sorted(distances, key=lambda item: item[1])
    return sorted_distances, input_lat, input_lon, df_unique  # Return the unique DataFrame

def get_marker_color(active_mrs):
    if active_mrs > 2:
        return 'green'
    if active_mrs > 1:
        return 'blue'
    elif active_mrs == 1:
        return 'lightred'
    else:
        return 'red'

def generate_map(top_markets, input_market_name, input_lat, input_lon, manager):
    if not top_markets:
        st.warning("No markets to display on the map.")
        return None
    m = folium.Map(location=[input_lat, input_lon], zoom_start=5.5)

    folium.Marker(
        [input_lat, input_lon],
        popup=f"<b>{input_market_name}</b>",
        icon=folium.Icon(color='purple', icon_color='white', icon='radio', prefix='fa')
    ).add_to(m)

    for rank, (market, distance, lat, lon, active_mrs, manager) in enumerate(top_markets, start=1):
        marker_color = get_marker_color(active_mrs)
        popup_html = f"""
                        <div style="width: 120px; white-space: normal !important;">
                            <b>{market}</b><br><br>
                             <b>Distance:</b> {distance:.2f} mi<br>
                             <b>Active MRs:</b> {active_mrs}<br>
                             <b>Manager:</b> {manager}
                        </div>
                    """
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=marker_color, icon_color='white', icon=str(rank), prefix='fa')
        ).add_to(m)
        folium.PolyLine(locations=[(input_lat, input_lon), (lat, lon)], color='black', weight=2, opacity=0.5).add_to(m)

    return m

def generate_all_markets_map(all_markets_df):
    if all_markets_df.empty:
        st.warning("No market data available to display on the map.")
        return None

    # Calculate the center of all markets for initial map view
    center_lat = all_markets_df['Latitude'].mean()
    center_lon = all_markets_df['Longitude'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=4)  # Adjust zoom level as needed

    for index, row in all_markets_df.iterrows():
        market_name = row['Market']
        lat = row['Latitude']
        lon = row['Longitude']
        active_mrs = row['Active MRs']
        manager = row['Manager']
        marker_color = get_marker_color(active_mrs)

        popup_html = f"""
                            <div style="width: 120px; white-space: normal !important;">
                                <b>{market_name}</b><br><br>
                                 <b>Manager:</b> {manager}
                            </div>
                        """
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color=marker_color, icon_color='white',icon=str(active_mrs), prefix='fa')
        ).add_to(m)

    return m

def generate_map_for_two_markets(market1_data, market2_data, distance_miles):
    market1_lat = market1_data['Latitude']
    market1_lon = market1_data['Longitude']
    market2_lat = market2_data['Latitude']
    market2_lon = market2_data['Longitude']
    market1_name = market1_data['Market']
    market2_name = market2_data['Market']

    # Calculate the center point for the map
    map_center_lat = (market1_lat + market2_lat) / 2
    map_center_lon = (market1_lon + market2_lon) / 2

    m = folium.Map(location=[map_center_lat, map_center_lon], zoom_start=8)  # Adjust zoom level as needed

    # Add markers for both markets
    folium.Marker(
        [market1_lat, market1_lon],
        popup=f"<b>{market1_name}</b>",
        icon=folium.Icon(color='blue', icon_color='white', icon=None)
    ).add_to(m)

    folium.Marker(
        [market2_lat, market2_lon],
        popup=f"<b>{market2_name}</b>",
        icon=folium.Icon(color='green', icon_color='white', icon=None)
    ).add_to(m)

    # Add a line connecting the two markets
    folium.PolyLine(
        locations=[(market1_lat, market1_lon), (market2_lat, market2_lon)],
        color='black',
        weight=2,
        opacity=0.7
    ).add_to(m)

    # Add the distance text to the map.
    folium.Popup(
        f"Distance: {distance_miles:.2f} miles",
        location=[(market1_lat + market2_lat) / 2, (market1_lon + market2_lon) / 2], # position the popup in the middle
        parse_html=True,
        max_width=300
    ).add_to(m)

    return m

def color_rows(row):
    active_mrs = row['Active MRs']
    if active_mrs > 1:
        return ['background-color: lightgreen'] * len(row)
    elif active_mrs == 1 :
        return ['background-color: #FFCCCB'] * len(row)
    else:
        return ['background-color: lightcoral'] * len(row)

def main():
    st.title("Market Proximtiy Analyzer")

    excel_file_path = "Market LatLong.xlsx"

    with st.sidebar:
        st.image('logo_name.png', width=350)
        st.title("Analyzer Controls")
        if excel_file_path is not None:
            all_markets_df = None
            all_markets_list = []
            try:
                all_markets_df = pd.read_excel(excel_file_path)
                if 'Market' in all_markets_df.columns:
                    all_markets_list = sorted(all_markets_df['Market'].unique())
                else:
                    st.error("The Excel file must contain a column named 'Market' in the sidebar.")
                    return
            except FileNotFoundError:
                st.error(f"Error: Excel file '{excel_file_path}' not found in the sidebar.")
                return
            except Exception as e:
                st.error(f"Error reading Excel file in the sidebar: {e}")
                return

            if all_markets_list:
                input_market = st.selectbox("Select a market:", all_markets_list)
                num_top_markets = st.number_input("Number of top markets to show:", min_value=1, max_value=10, value=5)

            else:
                st.warning("No markets found in the Excel file to populate the dropdown.")
                return
        else:
            st.error("Excel file path is not defined.")
            return

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Map View", "Table View", "All Markets Map", "Update MRs", "Compare Markets"])

    with tab4:
        st.subheader("Update active MRs for all markets")
        col1, col2 = st.columns([3,2])
        mrs_input_str = col1.text_input("Enter Active MRs for all markets (in alphabetical order, copy from sheet):")
        save = col1.button("Save")
        selected_market_df = all_markets_df[all_markets_df['Market'] == input_market]
        if not selected_market_df.empty:
            current_mrs = selected_market_df['Active MRs'].iloc[0]
            new_mrs = col2.number_input(f"Update Active MRs for {input_market}:", min_value=0, value=int(current_mrs))
            update_button = col2.button(f"Update MRs for {input_market}")

            if update_button:
                try:
                    all_markets_df.loc[all_markets_df['Market'] == input_market, 'Active MRs'] = new_mrs
                    all_markets_df.to_excel(excel_file_path, index=False)
                    st.success(f"Active MRs for '{input_market}' updated to {new_mrs} and saved!")
                except Exception as e:
                    st.error(f"Error saving to Excel file: {e}")
        else:
            st.warning(f"Market '{input_market}' not found in the data for updating MRs.")
        if save:
            if all_markets_df is not None and mrs_input_str:
                mr_list_str = mrs_input_str.strip().split()
                num_markets = len(all_markets_df)
                num_input_mrs = len(mr_list_str)
                if num_markets ==num_input_mrs:
                    try:
                        all_markets_df['Active MRs'] = [int(mr) for mr in mr_list_str]
                        all_markets_df.to_excel(excel_file_path, index=False)
                        st.success(f"Active MRs for all {num_markets} markets updated and saved to '{excel_file_path}'")
                    except ValueError:
                        st.error("Error: Please enter only numbers separated by spaces in the Active MRs string.")
                    except Exception as e:
                        st.error(f"Error saving to Excel file: {e}")
                else:
                    st.error(f"Error: The number of MRs entered ({num_input_mrs}) must match the number of markets ({num_markets}).")
            elif not mrs_input_str:
                st.warning("Please enter the Active MRs string.")
            
                

    if 'input_market' in locals() and all_markets_df is not None:
        results = get_all_distances_sorted(excel_file_path, input_market)

        if results:
            sorted_distances, input_lat, input_lon, manager = results 
            top_n_markets = sorted_distances[:num_top_markets]

            with tab1:
                st.subheader(f"Top {num_top_markets} Closest Markets to {input_market}:")
                market_map = generate_map(top_n_markets, input_market, input_lat, input_lon,manager)
                if market_map:
                    st_folium(market_map, width=1200, height=550)

            with tab2:
                st.subheader(f"Distances from {input_market}:")
                distances_df = pd.DataFrame(top_n_markets, columns=['Market', 'Distance (miles)', 'Latitude', 'Longitude', 'Active MRs', 'Manager'])
                styled_df = distances_df[['Market', 'Distance (miles)', 'Active MRs', 'Manager']].style.apply(color_rows, axis=1)
                st.dataframe(styled_df, hide_index=True)

    with tab5:
        st.subheader("Compare Markets")
        col1, col2 = st.columns(2)
        market1 = col1.selectbox("Select the first market:", all_markets_list,
                               key="market1")
        market2 = col2.selectbox("Select the second market:", all_markets_list,
                               key="market2")

        if market1 == market2:
            st.warning("Please select two different markets.")
        else:
            market1_data = all_markets_df[all_markets_df['Market'] == market1].iloc[0].to_dict()
            market2_data = all_markets_df[all_markets_df['Market'] == market2].iloc[0].to_dict()

            if not market1_data or not market2_data:
                st.error(
                    "One or both markets not found. Please check the market names.")
            else:
                market1_lat = market1_data['Latitude']
                market1_lon = market1_data['Longitude']
                market2_lat = market2_data['Latitude']
                market2_lon = market2_data['Longitude']
                market1_name = market1_data['Market']
                market2_name = market2_data['Market']
                market1_mrs = market1_data['Active MRs']
                market2_mrs = market2_data['Active MRs']
                market1_manager= market1_data['Manager']
                market2_manager= market2_data['Manager']

                distance_km = calculate_distance(market1_lat, market1_lon,
                                                    market2_lat, market2_lon)
                distance_miles = distance_km * 0.621371

                st.write(f"**Distance:** {distance_miles:.2f} miles")
                st.write(f"**{market1_name}:** {market1_mrs} MR(s), **{market1_manager}**")
                st.write(f"**{market2_name}:** {market2_mrs} MR(s), **{market2_manager}**")
    with tab3:
        st.subheader("All Markets")
        if all_markets_df is not None and not all_markets_df.empty:
            all_markets_map = generate_all_markets_map(all_markets_df)
            if all_markets_map:
                st_folium(all_markets_map, width=1200, height=600)
            else:
                st.warning("Could not generate the map of all markets.")
        else:
            st.warning("No market data available to display.")
                

if __name__ == "__main__":
    main()