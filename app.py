# --- START OF FILE app.py ---

import streamlit as st
import psycopg2 # Changed from snowflake.connector
import pandas as pd
import numpy as np

@st.cache_resource
def init_connection():
    # Connect to PostgreSQL instead of Snowflake
    return psycopg2.connect(**st.secrets["postgres_neon"])

@st.cache_data(ttl=600)
def run_query(_conn, query, params=None):
    with _conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()

@st.cache_data(ttl=600)
def run_query_df(_conn, query, params=None):
    # psycopg2 doesn't have fetch_pandas_all(), so we build the DataFrame manually
    with _conn.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        df = pd.DataFrame(rows, columns=colnames)
    return df

def calculate_growth(current, previous):
    if previous is None or pd.isna(previous) or current is None or pd.isna(current):
        return "N/A"
    
    current = pd.to_numeric(current, errors='coerce')
    previous = pd.to_numeric(previous, errors='coerce')

    if pd.isna(current) or pd.isna(previous): 
        return "N/A"
    
    if previous == 0:
        if current > 0:
            return "New Growth" 
        else:
            return "0.00%" 
            
    growth = ((current - previous) / previous) * 100
    return f"{growth:.2f}%"

# Consolidated growth to numeric function
def growth_to_numeric(growth_str):
    if isinstance(growth_str, str):
        if growth_str == "New Growth": return 10000 
        if growth_str == "N/A" or growth_str == "0.00%": return 0
        try: 
            return float(growth_str.replace('%',''))
        except ValueError:
            return 0 
    return float(growth_str) if pd.notna(growth_str) else 0


st.set_page_config(layout="wide", page_title="Sanskriti Setu", page_icon="🕌")

conn = init_connection()

st.sidebar.title("📜 Sanskriti Setu") 
st.sidebar.markdown("---") 

chapters = [
    "🏠 Home & Tourism Overview",
    "🎨 Traditional Art Forms",
    "🏛️ Explore Cultural Destinations",
    "💰 Government Support & Schemes", 
    "📅 Plan Your Visit (Seasonality)",
    "💎 Untouched Cultural Gems",
    "🌿 Responsible Tourism"
]

if 'app_mode' not in st.session_state:
    st.session_state.app_mode = chapters[0]


for chapter_name in chapters:
    if st.sidebar.button(chapter_name, key=f"btn_{chapter_name.replace(' ', '_').replace('&','and').replace('/','_')}", use_container_width=True):
        st.session_state.app_mode = chapter_name

st.sidebar.markdown("---")
st.sidebar.info("Sanskriti Setu")


if st.session_state.app_mode == "🏠 Home & Tourism Overview":
    st.title("Welcome to Sanskriti Setu!")
    st.markdown("Your smart gateway to India's rich cultural tapestry. Discover traditional arts, explore vibrant cultural experiences, and learn about responsible tourism.")
    st.markdown("---")
    st.header("India Tourism Snapshot")

    try:
        # Updated query for PostgreSQL schema and to avoid SQL injection
        query_all_state_data = """
            SELECT state_ut, domestic_visitors_yr1, foreign_visitors_yr1, 
                   domestic_visitors_yr2, foreign_visitors_yr2, 
                   data_period_yr1, data_period_yr2 
            FROM tourism_data.state_tourism_visits 
            WHERE state_ut NOT LIKE 'Total%%' 
              AND state_ut NOT LIKE 'GRAND TOTAL' 
              AND state_ut IS NOT NULL;
        """
        df_all_state_data = run_query_df(conn, query_all_state_data)

        if not df_all_state_data.empty:
            visitor_cols_yr1 = ['domestic_visitors_yr1', 'foreign_visitors_yr1']
            visitor_cols_yr2 = ['domestic_visitors_yr2', 'foreign_visitors_yr2']
            for col in visitor_cols_yr1 + visitor_cols_yr2:
                df_all_state_data[col] = pd.to_numeric(df_all_state_data[col], errors='coerce').fillna(0)

            available_years = sorted(df_all_state_data['data_period_yr2'].astype(str).unique(), reverse=True)
            
            if not available_years:
                st.warning("No years available for selection in State Tourism Data.")
            else:
                col1_home, col2_home = st.columns(2)
                with col1_home:
                    selected_year_home = st.selectbox("Select Year for Top States:", available_years, key="home_year_select")
                with col2_home:
                    visitor_type_home = st.selectbox("View by:", ["Domestic Visitors", "Foreign Visitors"], key="home_visitor_type")

                st.subheader(f"Top 10 States by {visitor_type_home} ({selected_year_home})")
                df_selected_year_home = df_all_state_data[df_all_state_data['data_period_yr2'] == selected_year_home].copy()

                if not df_selected_year_home.empty:
                    sort_column_home = 'domestic_visitors_yr2' if visitor_type_home == "Domestic Visitors" else 'foreign_visitors_yr2'
                    display_column_name_home = f"{visitor_type_home} ({selected_year_home})"
                    
                    df_top10_home = df_selected_year_home.sort_values(by=sort_column_home, ascending=False).head(10)
                    df_display_top10_home = df_top10_home[['state_ut', sort_column_home]].copy()
                    df_display_top10_home.columns = ["State/UT", display_column_name_home]
                    df_display_top10_home.index = np.arange(1, len(df_display_top10_home) + 1) 
                    st.dataframe(df_display_top10_home)
                    st.bar_chart(df_display_top10_home.set_index("State/UT")[display_column_name_home])
                else:
                    st.write(f"No data available for the year {selected_year_home}.")

            st.markdown("---")
            st.header("States with Rising Tourism Popularity")
            st.markdown("Highlighting states (not in the latest year's Top 10 by total visits) showing significant overall growth in total visitors.")

            latest_report_year_for_growth = available_years[0] if available_years else None
            if latest_report_year_for_growth:
                df_latest_growth_period = df_all_state_data[df_all_state_data['data_period_yr2'] == latest_report_year_for_growth].copy()
                if not df_latest_growth_period.empty and 'data_period_yr1' in df_latest_growth_period.columns:
                    df_latest_growth_period['total_visitors_yr1'] = df_latest_growth_period['domestic_visitors_yr1'] + df_latest_growth_period['foreign_visitors_yr1']
                    df_latest_growth_period['total_visitors_yr2'] = df_latest_growth_period['domestic_visitors_yr2'] + df_latest_growth_period['foreign_visitors_yr2']
                    
                    df_latest_growth_period['total_growth_pct_calculated'] = df_latest_growth_period.apply(
                        lambda row: calculate_growth(row['total_visitors_yr2'], row['total_visitors_yr1']), axis=1
                    )
                    
                    df_latest_growth_period['total_growth_numeric'] = df_latest_growth_period['total_growth_pct_calculated'].apply(growth_to_numeric)

                    top10_latest_year_states_total_visits = df_latest_growth_period.sort_values(by='total_visitors_yr2', ascending=False).head(10)['state_ut'].tolist()
                    df_rising_stars = df_latest_growth_period[
                        ~df_latest_growth_period['state_ut'].isin(top10_latest_year_states_total_visits) &
                        (df_latest_growth_period['total_growth_numeric'] > 10) 
                    ].sort_values(by='total_growth_numeric', ascending=False).head(5)

                    if not df_rising_stars.empty:
                        data_period_yr1_rising = df_rising_stars['data_period_yr1'].iloc[0]
                        data_period_yr2_rising = df_rising_stars['data_period_yr2'].iloc[0]
                        st.write(f"Emerging destinations based on total visitor growth from {data_period_yr1_rising} to {data_period_yr2_rising} (Min. 10% growth, outside Top 10):")
                        for index, row_star in df_rising_stars.iterrows():
                            delta_val = row_star['total_growth_pct_calculated']
                            delta_display = delta_val if delta_val not in ["N/A", "0.00%"] else None 
                            st.metric(label=row_star["state_ut"], 
                                      value=f"{int(row_star['total_visitors_yr2']):,} visits", 
                                      delta=delta_display)
                        df_rising_display = df_rising_stars[['state_ut', 'total_visitors_yr1', 'total_visitors_yr2', 'total_growth_pct_calculated']].copy()
                        df_rising_display.columns = ["State/UT", f"Total Visits ({data_period_yr1_rising})", f"Total Visits ({data_period_yr2_rising})", "Overall Growth"]
                        df_rising_display.index = np.arange(1, len(df_rising_display) + 1)
                        st.dataframe(df_rising_display)
                    else:
                        st.write("Could not identify significant rising stars (with >10% growth) outside the top 10, or data insufficient.")
                else:
                    st.write("Insufficient data for year-on-year growth comparison for rising popularity.")
            else:
                st.write("Latest year data not available for rising popularity analysis.")
        else:
            st.write("State tourism data could not be loaded.")
    except Exception as e:
        st.error(f"An error occurred while fetching and processing state tourism data: {e}")

elif st.session_state.app_mode == "🎨 Traditional Art Forms":
    st.title("🎨 Discover India's Traditional Art Forms")
    st.markdown("India's artistic heritage is a vibrant mosaic of myriad art forms, each telling a unique story of its region, culture, and people.")
    try:
        query = "SELECT artformname, stateoforigin, category, briefdescription, imageurl, responsibleconsumptiontip FROM tourism_data.traditionalartforms;"
        df_arts = run_query_df(conn, query)
        
        if not df_arts.empty:
            states = sorted([s for s in df_arts['stateoforigin'].unique() if pd.notna(s)])
            categories = sorted([c for c in df_arts['category'].unique() if pd.notna(c)])

            selected_state_art = st.selectbox("Filter by State:", ["All"] + states, key="art_state")
            selected_category_art = st.selectbox("Filter by Category:", ["All"] + categories, key="art_cat")

            filtered_arts = df_arts.copy()
            if selected_state_art != "All":
                filtered_arts = filtered_arts[filtered_arts['stateoforigin'] == selected_state_art]
            if selected_category_art != "All":
                filtered_arts = filtered_arts[filtered_arts['category'] == selected_category_art]

            if not filtered_arts.empty:
                for index, row in filtered_arts.iterrows():
                    st.subheader(row['artformname'])
                    if pd.notna(row['imageurl']) and row['imageurl'].strip(): 
                        try:
                            st.image(row['imageurl'], width=300, caption=f"{row['artformname']} from {row['stateoforigin']}")
                        except Exception as img_e:
                            st.caption(f"Image not available for {row['artformname']}")
                    st.markdown(f"**State of Origin:** {row['stateoforigin']}")
                    st.markdown(f"**Category:** {row['category']}")
                    st.write(row['briefdescription'])
                    if pd.notna(row['responsibleconsumptiontip']):
                         st.info(f"💡 Responsible Tip: {row['responsibleconsumptiontip']}")
                    st.markdown("---")
            else:
                st.write("No art forms match your current filter.")
        else:
            st.write("No art form data available.")
    except Exception as e:
        st.error(f"Error loading art forms: {e}")


elif st.session_state.app_mode == "🏛️ Explore Cultural Destinations":
    st.title("🏛️ Explore Cultural Destinations")
    st.markdown("From ancient monuments to vibrant states, discover India's key cultural hotspots.")
    
    tab1, tab2 = st.tabs(["Rising Popularity - Monuments", "Iconic Monuments (Detailed Trends)"])

    with tab1: 
        st.subheader("Monuments with Rising Visitor Interest")
        st.markdown("Identifying monuments (not in the absolute Top 10 of the latest year) showing significant growth in total visitors.")
        try:
            latest_fy_range_df = run_query_df(conn, "SELECT MAX(financial_year_range) AS latest_fy FROM tourism_data.all_monuments_stats;")
            if not latest_fy_range_df.empty and pd.notna(latest_fy_range_df['latest_fy'].iloc[0]):
                latest_fy = latest_fy_range_df['latest_fy'].iloc[0]
                
                query_top10_latest_all_types = "SELECT DISTINCT monument_name FROM tourism_data.top_monuments WHERE financial_year = %s AND monument_name != 'Others';"
                df_top10_latest_names = run_query_df(conn, query_top10_latest_all_types, (latest_fy,))
                top10_monument_names_list = df_top10_latest_names['monument_name'].tolist() if not df_top10_latest_names.empty else []

                query_monuments_growth = """
                    SELECT circle, monument_name, domestic_visitors_fy_start, foreign_visitors_fy_start, 
                           domestic_visitors_fy_end, foreign_visitors_fy_end 
                    FROM tourism_data.all_monuments_stats 
                    WHERE financial_year_range = %s 
                      AND monument_name NOT LIKE 'Total%%' AND circle NOT LIKE 'Total%%';
                """
                df_monuments_for_growth = run_query_df(conn, query_monuments_growth, (latest_fy,))

                if not df_monuments_for_growth.empty:
                    num_cols = ['domestic_visitors_fy_start', 'foreign_visitors_fy_start', 'domestic_visitors_fy_end', 'foreign_visitors_fy_end']
                    for col in num_cols:
                        df_monuments_for_growth[col] = pd.to_numeric(df_monuments_for_growth[col], errors='coerce').fillna(0)

                    df_monuments_for_growth['total_visitors_fy_start'] = df_monuments_for_growth['domestic_visitors_fy_start'] + df_monuments_for_growth['foreign_visitors_fy_start']
                    df_monuments_for_growth['total_visitors_fy_end'] = df_monuments_for_growth['domestic_visitors_fy_end'] + df_monuments_for_growth['foreign_visitors_fy_end']
                    
                    df_monuments_for_growth['total_growth_pct_calculated'] = df_monuments_for_growth.apply(
                        lambda row: calculate_growth(row['total_visitors_fy_end'], row['total_visitors_fy_start']), axis=1
                    )
                    
                    df_monuments_for_growth['total_growth_numeric'] = df_monuments_for_growth['total_growth_pct_calculated'].apply(growth_to_numeric)

                    df_rising_monuments = df_monuments_for_growth[
                        ~df_monuments_for_growth['monument_name'].isin(top10_monument_names_list) &
                        (df_monuments_for_growth['total_growth_numeric'] > 20) 
                    ].sort_values(by='total_growth_numeric', ascending=False).head(7)

                    if not df_rising_monuments.empty:
                        st.write(f"Emerging monument destinations based on total visitor growth ({latest_fy.split('-')[0]} to {latest_fy.split('-')[1]}):")
                        
                        rising_mon_visitor_type = st.radio(
                            "Show visitor trends for:", 
                            ("Domestic Visitors", "Foreign Visitors"), 
                            key="rising_mon_visitor_type_global", 
                            horizontal=True
                        )

                        for index, row_mon_star in df_rising_monuments.iterrows():
                            st.markdown(f"#### {row_mon_star['monument_name']} ({row_mon_star['circle']})")
                            
                            delta_val_mon = row_mon_star['total_growth_pct_calculated']
                            delta_display_mon = delta_val_mon if delta_val_mon not in ["N/A", "0.00%"] else None
                                                        
                            st.metric(label=f"Total Visitors ({latest_fy.split('-')[1]})", 
                                      value=f"{int(row_mon_star['total_visitors_fy_end']):,}", 
                                      delta=delta_display_mon)
                            
                            fy_start_label = latest_fy.split('-')[0]
                            fy_end_label = latest_fy.split('-')[1]

                            if rising_mon_visitor_type == "Domestic Visitors":
                                visitors_start = row_mon_star['domestic_visitors_fy_start']
                                visitors_end = row_mon_star['domestic_visitors_fy_end']
                                chart_title = "Domestic Visitors"
                            else: 
                                visitors_start = row_mon_star['foreign_visitors_fy_start']
                                visitors_end = row_mon_star['foreign_visitors_fy_end']
                                chart_title = "Foreign Visitors"
                            
                            chart_data_mon = pd.DataFrame({
                                'Financial Year': [fy_start_label, fy_end_label],
                                chart_title: [visitors_start, visitors_end]
                            })
                            st.bar_chart(chart_data_mon.set_index('Financial Year')[chart_title], use_container_width=True)
                            st.caption(f"Data for chart: {chart_title} - {fy_start_label}: {int(visitors_start):,}, {fy_end_label}: {int(visitors_end):,}")
                            st.markdown("---")
                    else:
                        st.write("Could not identify significant rising monuments (with >20% growth) outside the Top 10 for the latest period.")
                else:
                    st.write("Monument visitor data for growth calculation not available.")
            else:
                st.write("Latest financial year for monuments not determined.")
        except Exception as e:
            st.error(f"Error loading rising popularity for monuments: {e}")

    with tab2:
        st.subheader("Iconic Monuments & Detailed Visitor Trends")
        try:
            query_top10_dom_detail = """
                SELECT monument_name, number_of_visitors 
                FROM tourism_data.top_monuments 
                WHERE financial_year = 'FY2022-23' 
                  AND visitor_type = 'Domestic' 
                  AND monument_name != 'Others' 
                ORDER BY data_rank;
            """
            df_top10_dom_detail = run_query_df(conn, query_top10_dom_detail)
            if not df_top10_dom_detail.empty:
                df_top10_dom_detail.index = np.arange(1, len(df_top10_dom_detail) + 1)
                st.write("Top ASI Monuments by Domestic Visitors (FY 2022-23):")
                st.dataframe(df_top10_dom_detail)
            else:
                st.write("Top 10 domestic monument data for FY2022-23 not available.")
        except Exception as e:
            st.error(f"Error loading top 10 monuments data: {e}")

        st.markdown("---")
        st.subheader("Detailed Monument Visitor Trends (Year-on-Year)")
        try:
            circles_query = "SELECT DISTINCT circle FROM tourism_data.all_monuments_stats WHERE circle NOT LIKE 'Total%%' AND circle IS NOT NULL ORDER BY circle;"
            circles_df = run_query_df(conn, circles_query)
            if not circles_df.empty:
                selected_circle = st.selectbox("Select ASI Circle:", circles_df['circle'], key="mon_circle_select_detail")
                if selected_circle:
                    monuments_in_circle_query = "SELECT DISTINCT monument_name FROM tourism_data.all_monuments_stats WHERE circle = %s AND monument_name NOT LIKE 'Total%%' ORDER BY monument_name;"
                    monuments_in_circle_df = run_query_df(conn, monuments_in_circle_query, (selected_circle,))
                    if not monuments_in_circle_df.empty:
                        selected_monument = st.selectbox("Select Monument:", monuments_in_circle_df['monument_name'], key="mon_name_select_detail")
                        if selected_monument:
                            query_monument = """
                                SELECT financial_year_range, domestic_visitors_fy_start, foreign_visitors_fy_start, 
                                       domestic_visitors_fy_end, foreign_visitors_fy_end 
                                FROM tourism_data.all_monuments_stats 
                                WHERE monument_name = %s AND circle = %s 
                                ORDER BY financial_year_range;
                            """
                            df_monument_detail = run_query_df(conn, query_monument, (selected_monument, selected_circle))
                            if not df_monument_detail.empty:
                                st.write(f"Visitor Statistics for {selected_monument}:")
                                for idx, row_detail in df_monument_detail.iterrows():
                                    st.markdown(f"**Data for: {row_detail['financial_year_range']}**")
                                    dom_start = pd.to_numeric(row_detail['domestic_visitors_fy_start'], errors='coerce')
                                    dom_end = pd.to_numeric(row_detail['domestic_visitors_fy_end'], errors='coerce')
                                    for_start = pd.to_numeric(row_detail['foreign_visitors_fy_start'], errors='coerce')
                                    for_end = pd.to_numeric(row_detail['foreign_visitors_fy_end'], errors='coerce')

                                    domestic_growth_calculated = calculate_growth(dom_end, dom_start)
                                    foreign_growth_calculated = calculate_growth(for_end, for_start)
                                    
                                    col1_mon, col2_mon = st.columns(2)
                                    with col1_mon:
                                        st.metric(f"Domestic Visitors ({row_detail['financial_year_range'].split('-')[0]})", f"{int(dom_start):,}" if pd.notna(dom_start) else "N/A")
                                        st.metric(f"Domestic Visitors ({row_detail['financial_year_range'].split('-')[1]})", f"{int(dom_end):,}" if pd.notna(dom_end) else "N/A", delta=domestic_growth_calculated if domestic_growth_calculated not in ["0.00%", "N/A"] else None)
                                    with col2_mon:
                                        st.metric(f"Foreign Visitors ({row_detail['financial_year_range'].split('-')[0]})", f"{int(for_start):,}" if pd.notna(for_start) else "N/A")
                                        st.metric(f"Foreign Visitors ({row_detail['financial_year_range'].split('-')[1]})", f"{int(for_end):,}" if pd.notna(for_end) else "N/A", delta=foreign_growth_calculated if foreign_growth_calculated not in ["0.00%", "N/A"] else None)
                                    st.caption("Growth calculated based on start and end year figures. 'New Growth' indicates start year was zero.")
                                    st.markdown("---")
                            else:
                                 st.write(f"No detailed trend data found for {selected_monument}.")
                    else:
                        st.write(f"No monuments found for circle: {selected_circle}")
            else:
                st.write("No ASI circles found in the data.")
        except Exception as e:
            st.error(f"Error loading detailed monument data: {e}")

elif st.session_state.app_mode == "💰 Government Support & Schemes":
    st.title("💰 Government Support for Arts & Culture")
    st.markdown("Explore various schemes and financial assistance provided by the government to promote and preserve India's cultural heritage and support its artists.")

    tab_overall_funding, tab_artist_overview, tab_explore_grants = st.tabs([
        "Overall Scheme Funding (National)", 
        "Artist Support Schemes Overview", 
        "Explore Specific Scheme Grants"
    ])

    with tab_overall_funding:
        st.subheader("Overall Scheme-wise Funds Released (National Level)")
        st.markdown("Funding trends for major cultural schemes over the years (Amounts in Crores).")
        try:
            query = """
                SELECT scheme_name, funds_2019_20, funds_2020_21, funds_2021_22, funds_2022_23, funds_2023_24 
                FROM tourism_data.schemewisefundsreleased 
                WHERE scheme_name NOT LIKE 'Total%%' AND scheme_name NOT LIKE 'Grand Total';
            """
            df_overall_funds = run_query_df(conn, query)
            if not df_overall_funds.empty:

                df_overall_funds.columns = ["Scheme Name", "2019-20", "2020-21", "2021-22", "2022-23", "2023-24"]
                for col in df_overall_funds.columns[1:]:
                    df_overall_funds[col] = pd.to_numeric(df_overall_funds[col], errors='coerce').fillna(0)
                
                df_melted_overall_funds = df_overall_funds.melt(id_vars=['Scheme Name'], var_name='Financial Year', value_name='Funds Released (Crores)')
                
                if not df_melted_overall_funds.empty:
                    all_schemes = sorted(df_melted_overall_funds['Scheme Name'].unique())
                    selected_schemes_plot = st.multiselect("Select schemes to plot:", all_schemes, default=all_schemes[:min(5, len(all_schemes))], key="worm_plot_schemes")

                    if selected_schemes_plot:
                        df_plot_funds = df_melted_overall_funds[df_melted_overall_funds['Scheme Name'].isin(selected_schemes_plot)]
                        st.line_chart(df_plot_funds.pivot_table(index='Financial Year', columns='Scheme Name', values='Funds Released (Crores)', aggfunc='sum').fillna(0))
                    else:
                        st.info("Select one or more schemes to display the trend chart.")
                
                df_overall_funds.index = np.arange(1, len(df_overall_funds) + 1)
                st.dataframe(df_overall_funds)
            else:
                st.write("No data available for Overall Scheme Funding.")
        except Exception as e:
            st.error(f"Error loading Overall Scheme Funding data: {e}")

    with tab_artist_overview:
        st.subheader("Artist Support Schemes Overview")
        st.markdown("Descriptive overview of various schemes aimed at supporting artists and cultural practices.")
        try:
            query = """
                SELECT schemeid, schemename, administeringbody, focusarea, 
                       datapoint_example_state_ut, datapoint_example_value, relevancetoplatform 
                FROM tourism_data.artistsupportschemesummary;
            """
            df_summary = run_query_df(conn, query)
            if not df_summary.empty:
                for index, row in df_summary.iterrows():
                    st.markdown(f"#### {row['schemename']}")
                    with st.expander("Details", expanded=False):
                        st.markdown(f"**Administering Body:** {row['administeringbody']}")
                        st.markdown(f"**Focus Area:** {row['focusarea']}")
                        if pd.notna(row['datapoint_example_state_ut']) and pd.notna(row['datapoint_example_value']):
                            st.markdown(f"**Impact:** {row['datapoint_example_value']} in {row['datapoint_example_state_ut']}")
                        st.write(f"**Relevance to Platform:** {row['relevancetoplatform']}")
                    st.markdown("---")
            else: 
                st.write("No data for Artist Support Schemes Overview.")
        except Exception as e:
            st.error(f"Error loading Artist Support Schemes Overview: {e}")

    with tab_explore_grants:
        st.subheader("Explore Specific Scheme Grants & Data")
        # Lowercase table names for PostgreSQL
        specific_scheme_table_map = {
            "Senior/Young Artist Scheme (Beneficiaries)": "senioryoungartistscheme",
            "Building Grants (Studio Theatre)": "buildinggrantsstudiotheatre",
            "Veteran Artists (Applications Received)": "veteranartistsapplications",
            "Guru-Shishya Parampara (Assistance)": "gurushishyaparamparaassistance",
            "Cultural Function & Production Grants": "culturalfunctionproductiongrant",
            "Museum Development Grants": "museumgrantschemefunds",
            "ASI Monument Preservation Expenditure (National)": "asimonumentpreservationexpenditure"
        }
        selected_specific_scheme_display = st.selectbox("Select Specific Scheme/Grant Data:", list(specific_scheme_table_map.keys()), key="specific_scheme_select_tab3")
        selected_specific_table = specific_scheme_table_map[selected_specific_scheme_display]

        try:
            full_table_name = f"tourism_data.{selected_specific_table}"

            if selected_specific_table == "senioryoungartistscheme":
                st.markdown("##### Senior/Young Artist Scheme Beneficiary Data")
                query = f"SELECT new_states as state, subject, gender, age, phy_handicaped, sc_st, user_id, field_id FROM {full_table_name} ORDER BY state, age;"
                df_syas = run_query_df(conn, query)
                
                if not df_syas.empty:
                    df_syas['subject_clean'] = df_syas['subject'].str.strip().str.title()

                    unique_states_syas = sorted([s for s in df_syas['state'].unique() if pd.notna(s)])
                    selected_state_syas_tab3 = st.selectbox("Filter by State:", ["All"] + unique_states_syas, key="syas_state_filter_tab3")
                    
                    df_filtered_syas = df_syas.copy()
                    if selected_state_syas_tab3 != "All":
                        df_filtered_syas = df_filtered_syas[df_filtered_syas['state'] == selected_state_syas_tab3]

                    display_cols_syas = ['state', 'subject', 'gender', 'age', 'phy_handicaped']
                    df_display_table_syas = df_filtered_syas[display_cols_syas].copy()
                    df_display_table_syas.index = np.arange(1, len(df_display_table_syas) + 1)
                    st.dataframe(df_display_table_syas.head(50))
                    
                    if not df_filtered_syas.empty:
                        st.markdown("###### Summary Charts")
                        
                        st.markdown("Distribution of Beneficiaries by State (Selected Filter):")
                        beneficiaries_by_state_filtered = df_filtered_syas.groupby('state').size().reset_index(name='Number of Beneficiaries').sort_values(by='Number of Beneficiaries', ascending=False)
                        st.bar_chart(beneficiaries_by_state_filtered.head(15).set_index('state'))

                else: 
                    st.write(f"No data available for {selected_specific_scheme_display}.")
            
            elif selected_specific_table == "buildinggrantsstudiotheatre":
                st.markdown("##### Building Grants including Studio Theatre (Amount in Lakhs)")
                query = f"SELECT state_ut, amount_21_22, amount_22_23, amount_released_authorized_23_24 FROM {full_table_name} WHERE state_ut NOT LIKE 'Total%%';"
                df_data = run_query_df(conn, query)
                if not df_data.empty:
                    df_data.columns = ["State/UT", "Amount 21-22", "Amount 22-23", "Amount 23-24"]
                    for col in ["Amount 21-22", "Amount 22-23", "Amount 23-24"]:
                        df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)
                    df_melted = df_data.melt(id_vars=['State/UT'], var_name='Financial Year', value_name='Amount (Lakhs)')
                    pivot_data = df_melted.pivot_table(index='State/UT', columns='Financial Year', values='Amount (Lakhs)', aggfunc='sum').fillna(0)
                    st.bar_chart(pivot_data)
                    df_data.index = np.arange(1, len(df_data) + 1)
                    st.dataframe(df_data)
                else: st.write(f"No data available for {selected_specific_scheme_display}.")

            elif selected_specific_table == "veteranartistsapplications":
                st.markdown("##### Applications for Veteran Artists Financial Assistance")
                query = f"SELECT state_ut, apps_2019_20, apps_2020_21, apps_2021_22, apps_2022_23, apps_2023_24 FROM {full_table_name} WHERE state_ut NOT LIKE 'Total%%';"
                df_data = run_query_df(conn, query)
                if not df_data.empty:
                    df_data.columns = ["State/UT", "Apps 19-20", "Apps 20-21", "Apps 21-22", "Apps 22-23", "Apps 23-24"]
                    latest_year_col_vaa = "Apps 23-24" 
                    for col in df_data.columns[1:]: df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)
                    st.bar_chart(df_data.sort_values(by=latest_year_col_vaa, ascending=False).head(15).set_index('State/UT')[latest_year_col_vaa])
                    df_data.index = np.arange(1, len(df_data) + 1)
                    st.dataframe(df_data)
                else: st.write(f"No data for {selected_specific_scheme_display}.")
            
            elif selected_specific_table == "gurushishyaparamparaassistance":
                st.markdown("##### Guru-Shishya Parampara Assistance (Amount in Lakhs)")
                query = f"SELECT state_ut, amount_21_22, amount_22_23, amount_released_authorized_23_24 FROM {full_table_name} WHERE state_ut NOT LIKE 'Total%%' AND state_ut IS NOT NULL;"
                df_data = run_query_df(conn, query)
                if not df_data.empty:
                    df_data.columns = ["State/UT", "Amount 21-22", "Amount 22-23", "Amount 23-24 (Released/Authorized)"]
                    amount_cols = ["Amount 21-22", "Amount 22-23", "Amount 23-24 (Released/Authorized)"]
                    for col in amount_cols: df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)
                    
                    unique_states_gsp = sorted([s for s in df_data['State/UT'].unique() if pd.notna(s)])
                    selected_states_gsp = st.multiselect("Select State(s) to view trend:", unique_states_gsp, default=unique_states_gsp[:min(3, len(unique_states_gsp))], key="gsp_state_multiselect_revised")

                    if selected_states_gsp:
                        df_filtered_gsp = df_data[df_data['State/UT'].isin(selected_states_gsp)]
                        df_melted_gsp = df_filtered_gsp.melt(id_vars=['State/UT'], value_vars=amount_cols, var_name='Financial Year Period', value_name='Amount (Lakhs)')
                        df_melted_gsp['Financial Year Period'] = df_melted_gsp['Financial Year Period'].str.replace("Amount ", "").str.replace(" (Released/Authorized)", "").str.replace(" (Auth/Rel)", "") 
                        st.line_chart(df_melted_gsp.pivot_table(index='Financial Year Period', columns='State/UT', values='Amount (Lakhs)', aggfunc='sum').fillna(0))
                    else:
                        st.info("Select one or more states to display the trend chart.")
                    df_data.index = np.arange(1, len(df_data) + 1)
                    st.dataframe(df_data)
                else: st.write(f"No data available for {selected_specific_scheme_display}.")

            elif selected_specific_table == "culturalfunctionproductiongrant":
                st.markdown("##### Cultural Function & Production Grants (Amount in Lakhs)")
                query = f"SELECT state_ut, amount_21_22, amount_22_23, amount_released_23_24 FROM {full_table_name} WHERE state_ut NOT LIKE 'Total%%' AND state_ut IS NOT NULL;" 
                df_data = run_query_df(conn, query)
                if not df_data.empty:
                    df_data.columns = ["State/UT", "Amount 21-22", "Amount 22-23", "Amount 23-24 (Released)"]
                    amount_cols_cfp = ["Amount 21-22", "Amount 22-23", "Amount 23-24 (Released)"]
                    for col in amount_cols_cfp: df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)

                    unique_states_cfp = sorted([s for s in df_data['State/UT'].unique() if pd.notna(s)])
                    selected_states_cfp = st.multiselect("Select State(s) to view trend:", unique_states_cfp, default=unique_states_cfp[:min(3, len(unique_states_cfp))], key="cfp_state_multiselect_revised")

                    if selected_states_cfp:
                        df_filtered_cfp = df_data[df_data['State/UT'].isin(selected_states_cfp)]
                        df_melted_cfp = df_filtered_cfp.melt(id_vars=['State/UT'], value_vars=amount_cols_cfp, var_name='Financial Year Period', value_name='Amount (Lakhs)')
                        df_melted_cfp['Financial Year Period'] = df_melted_cfp['Financial Year Period'].str.replace("Amount ", "").str.replace(" (Released)", "")
                        st.line_chart(df_melted_cfp.pivot_table(index='Financial Year Period', columns='State/UT', values='Amount (Lakhs)', aggfunc='sum').fillna(0))
                    else:
                        st.info("Select one or more states to display the trend chart.")
                    df_data.index = np.arange(1, len(df_data) + 1)
                    st.dataframe(df_data)
                else: st.write(f"No data available for {selected_specific_scheme_display}.")

            elif selected_specific_table == "museumgrantschemefunds":
                st.markdown("##### Museum Development Grants (Funds Released)")
                query = f"SELECT state_name, organization_name, type_of_museum, funds_2019_20, funds_2020_21, funds_2021_22, funds_2022_23, funds_2023_24 FROM {full_table_name} WHERE state_name NOT LIKE 'Total%%' AND state_name IS NOT NULL;"
                df_data = run_query_df(conn, query)
                if not df_data.empty:
                    fund_cols_db = ['funds_2019_20', 'funds_2020_21', 'funds_2021_22', 'funds_2022_23', 'funds_2023_24']
                    fund_cols_display = ['2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
                    fund_cols_map = dict(zip(fund_cols_db, fund_cols_display))

                    for col_db in fund_cols_db:
                        df_data[col_db] = pd.to_numeric(df_data[col_db], errors='coerce').fillna(0)

                    unique_states_museum = sorted([s for s in df_data['state_name'].unique() if pd.notna(s)])
                    selected_states_museum = st.multiselect("Select State(s):", unique_states_museum, default=unique_states_museum[:min(3, len(unique_states_museum))], key="museum_state_multiselect_revised")
                    
                    selected_year_museum_display = st.selectbox("Select Year to View Funds:", fund_cols_display, key="museum_year_select_revised")

                    selected_year_db_col = [k for k, v in fund_cols_map.items() if v == selected_year_museum_display][0]

                    if selected_states_museum and selected_year_museum_display:
                        df_filtered_museum = df_data[df_data['state_name'].isin(selected_states_museum)]
                        st.bar_chart(df_filtered_museum.groupby('state_name')[selected_year_db_col].sum())
                    
                    df_data.index = np.arange(1, len(df_data) + 1)
                    st.dataframe(df_data)
                else: st.write(f"No data available for {selected_specific_scheme_display}.")
            
            elif selected_specific_table == "asimonumentpreservationexpenditure":
                st.markdown("##### ASI Monument Preservation Expenditure (National Level, Amount in Crores)")
                query = f"SELECT year, allocation, expenditure FROM {full_table_name};"
                df_asi_exp = run_query_df(conn, query)
                if not df_asi_exp.empty:
                    df_asi_exp.columns = ["Financial Year", "Allocation (Crores)", "Expenditure (Crores)"]
                    st.line_chart(df_asi_exp.set_index("Financial Year"))
                    df_asi_exp.index = np.arange(1, len(df_asi_exp) + 1)
                    st.dataframe(df_asi_exp)
                else: st.write(f"No data for {selected_specific_scheme_display}.")
            
            else: # Fallback for any other table
                st.markdown(f"##### Data for: {selected_specific_scheme_display}")
                try:
                    # Generic, safe query
                    query = f"SELECT * FROM {full_table_name} LIMIT 200;"
                    df_generic_scheme = run_query_df(conn, query)
                    
                    if not df_generic_scheme.empty:
                        # Post-filter in pandas if columns exist
                        if 'state_ut' in df_generic_scheme.columns:
                            df_generic_scheme = df_generic_scheme[~df_generic_scheme['state_ut'].astype(str).str.contains('Total', na=False, case=False)]
                        elif 'scheme_name' in df_generic_scheme.columns:
                             df_generic_scheme = df_generic_scheme[~df_generic_scheme['scheme_name'].astype(str).str.contains('Total', na=False, case=False)]

                        df_generic_scheme.index = np.arange(1, len(df_generic_scheme) + 1)
                        st.dataframe(df_generic_scheme)
                    else:
                        st.write(f"No data available for: {selected_specific_scheme_display}.")
                except Exception as e:
                    st.error(f"An error occurred while fetching generic data for {selected_specific_scheme_display}: {e}")

        except Exception as e:
            st.error(f"An error occurred while fetching data for {selected_specific_scheme_display}: {e}")


elif st.session_state.app_mode == "📅 Plan Your Visit (Seasonality)":
    st.title("📅 Plan Your Visit: Tourism Seasonality")
    st.markdown("Understand the general flow of tourist arrivals to India throughout the year.")
    
    st.subheader("Foreign Tourist Arrivals (FTAs) Seasonality")
    try:
        # Using a window function to get the latest data for each month/year combo
        query_seasonality_fta = """
        WITH RankedFTAs AS (
            SELECT
                month_name,
                data_year,
                fta_count,
                ROW_NUMBER() OVER (PARTITION BY month_name, data_year ORDER BY report_source_year DESC) as rn
            FROM tourism_data.ftamonthly 
        )
        SELECT month_name, data_year, fta_count
        FROM RankedFTAs
        WHERE rn = 1; 
        """ 
        df_season_fta = run_query_df(conn, query_seasonality_fta)

        if not df_season_fta.empty:
            month_order = ["January", "February", "March", "April", "May", "June", 
                           "July", "August", "September", "October", "November", "December"]
            
            df_season_fta['month_name'] = pd.Categorical(df_season_fta['month_name'], categories=month_order, ordered=True)
            df_season_fta = df_season_fta.sort_values(by=['data_year', 'month_name'])

            available_years_fta = sorted(df_season_fta['data_year'].unique(), reverse=True)
            if available_years_fta:
                selected_year_fta = st.selectbox("Select Year to View FTA Seasonality:", available_years_fta, key="fta_year_select")
                
                df_year_season_fta = df_season_fta[df_season_fta['data_year'] == selected_year_fta]

                if not df_year_season_fta.empty:
                    st.write(f"Foreign Tourist Arrivals in {selected_year_fta}")
                    st.line_chart(df_year_season_fta.set_index('month_name')['fta_count'])
                    st.caption("Data reflects overall foreign tourist arrivals and can indicate peak and lean seasons for international visitors.")
                else:
                    st.write(f"No FTA data for {selected_year_fta}.")
            else:
                st.write("No years available for FTA seasonality.")
        else:
            st.write("Foreign Tourist Arrival seasonality data not available.")
    except Exception as e:
        st.error(f"Error loading FTA seasonality data: {e}")


elif st.session_state.app_mode == "💎 Untouched Cultural Gems":
    st.title("💎 Discover Untouched Cultural Gems")
    st.markdown("Explore some of India's lesser-known destinations that offer rich cultural experiences, and learn how to visit them responsibly.")
    try:
        query = """
            SELECT gemname, state, region, type, culturalsignificance, 
                   whypotentiallyuntouched, responsibletravelguideline, imageurl 
            FROM tourism_data.untouchedgems;
        """
        df_gems = run_query_df(conn, query) 
        
        if not df_gems.empty:
            for index, row in df_gems.iterrows():
                st.subheader(row['gemname'])
                if pd.notna(row['imageurl']) and row['imageurl'].strip():
                    try:
                        st.image(row['imageurl'], caption=row['gemname'], width=400) 
                    except Exception as img_e:
                        st.caption(f"Could not load image for {row['gemname']}.")
                else:
                    st.caption(f"Image not available for {row['gemname']}.")

                st.markdown(f"**State:** {row['state']} | **Region:** {row['region']} | **Type:** {row['type']}")
                st.write(f"**Cultural Significance:** {row['culturalsignificance']}")
                st.info(f"**Why Potentially Untouched?** {row['whypotentiallyuntouched']}")
                st.success(f"🌿 **Responsible Travel Guideline:** {row['responsibletravelguideline']}")
                st.markdown("---")
        else:
            st.write("No untouched gems data available.")
    except Exception as e:
        st.error(f"Error loading untouched gems: {e}")

elif st.session_state.app_mode == "🌿 Responsible Tourism":
    st.title("🌿 Travel Responsibly, Preserve Our Heritage")
    st.markdown("""
    Responsible tourism is about making better places for people to live in and better places for people to visit. It focuses on minimizing negative environmental, social, and economic impacts while generating greater economic benefits for local people and enhancing the well-being of host communities.
    """)
    st.subheader("Key Principles for Responsible Travellers in India:")
    st.markdown("""
    * **Respect Local Culture & Traditions:** Learn a few basic phrases, dress modestly especially when visiting religious sites, and always ask for permission before taking photographs of people or their property.
    * **Support Local Economies:** Buy authentic souvenirs directly from artisans, eat at local restaurants, and use local guides. Ensure your spending benefits the host community.
    * **Protect Heritage Sites:** Do not deface, damage, or remove anything from historical monuments or natural sites. Follow designated paths and respect entry restrictions.
    * **Minimize Environmental Impact:** Reduce plastic use (carry reusable water bottles/bags), dispose of waste properly, conserve water and electricity. Choose eco-friendly accommodations and transport where possible.
    * **Be Mindful of Wildlife:** Do not feed wild animals, maintain a safe distance, and avoid disturbing their natural habitat. Opt for ethical wildlife tourism operators.
    * **Reduce Overcrowding:** Consider visiting popular sites during off-peak seasons or times. Explore lesser-known destinations to help distribute tourist flow.
    * **Stay Informed:** Research your destination, understand local sensitivities, and be aware of any specific guidelines for visitors.
    * **Provide Constructive Feedback:** If you encounter practices that are not responsible, provide polite feedback to the concerned authorities or businesses.
    """)