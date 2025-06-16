import streamlit as st
import snowflake.connector
import pandas as pd
import numpy as np

@st.cache_resource
def init_connection():
    return snowflake.connector.connect(
        **st.secrets["snowflake"],
        client_session_keep_alive=True 
    )


@st.cache_data(ttl=600)
def run_query(_conn, query):
    with _conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall()

@st.cache_data(ttl=600)
def run_query_df(_conn, query):
    with _conn.cursor() as cur:
        cur.execute(query)
        df = cur.fetch_pandas_all()
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
        query_all_state_data = "SELECT State_UT, Domestic_Visitors_Yr1, Foreign_Visitors_Yr1, Domestic_Visitors_Yr2, Foreign_Visitors_Yr2, Data_Period_Yr1, Data_Period_Yr2 FROM State_Tourism_Visits WHERE State_UT NOT LIKE 'Total%' AND State_UT NOT LIKE 'GRAND TOTAL' AND State_UT IS NOT NULL;"
        df_all_state_data = run_query_df(conn, query_all_state_data)

        if not df_all_state_data.empty:
            visitor_cols_yr1 = ['DOMESTIC_VISITORS_YR1', 'FOREIGN_VISITORS_YR1']
            visitor_cols_yr2 = ['DOMESTIC_VISITORS_YR2', 'FOREIGN_VISITORS_YR2']
            for col in visitor_cols_yr1 + visitor_cols_yr2:
                df_all_state_data[col] = pd.to_numeric(df_all_state_data[col], errors='coerce').fillna(0)

            available_years = sorted(df_all_state_data['DATA_PERIOD_YR2'].astype(str).unique(), reverse=True)
            
            if not available_years:
                st.warning("No years available for selection in State Tourism Data.")
            else:
                col1_home, col2_home = st.columns(2)
                with col1_home:
                    selected_year_home = st.selectbox("Select Year for Top States:", available_years, key="home_year_select")
                with col2_home:
                    visitor_type_home = st.selectbox("View by:", ["Domestic Visitors", "Foreign Visitors"], key="home_visitor_type")

                st.subheader(f"Top 10 States by {visitor_type_home} ({selected_year_home})")
                df_selected_year_home = df_all_state_data[df_all_state_data['DATA_PERIOD_YR2'] == selected_year_home].copy()

                if not df_selected_year_home.empty:
                    sort_column_home = 'DOMESTIC_VISITORS_YR2' if visitor_type_home == "Domestic Visitors" else 'FOREIGN_VISITORS_YR2'
                    display_column_name_home = f"{visitor_type_home} ({selected_year_home})"
                    
                    df_top10_home = df_selected_year_home.sort_values(by=sort_column_home, ascending=False).head(10)
                    df_display_top10_home = df_top10_home[['STATE_UT', sort_column_home]].copy()
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
                df_latest_growth_period = df_all_state_data[df_all_state_data['DATA_PERIOD_YR2'] == latest_report_year_for_growth].copy()
                if not df_latest_growth_period.empty and 'DATA_PERIOD_YR1' in df_latest_growth_period.columns:
                    df_latest_growth_period['TOTAL_VISITORS_YR1'] = df_latest_growth_period['DOMESTIC_VISITORS_YR1'] + df_latest_growth_period['FOREIGN_VISITORS_YR1']
                    df_latest_growth_period['TOTAL_VISITORS_YR2'] = df_latest_growth_period['DOMESTIC_VISITORS_YR2'] + df_latest_growth_period['FOREIGN_VISITORS_YR2']
                    
                    df_latest_growth_period['TOTAL_GROWTH_PCT_CALCULATED'] = df_latest_growth_period.apply(
                        lambda row: calculate_growth(row['TOTAL_VISITORS_YR2'], row['TOTAL_VISITORS_YR1']), axis=1
                    )
                    def growth_to_numeric(growth_str):
                        if isinstance(growth_str, str):
                            if growth_str == "New Growth": return 10000 
                            if growth_str == "N/A" or growth_str == "0.00%": return 0
                            try: 
                                return float(growth_str.replace('%',''))
                            except ValueError:
                                return 0 
                        return float(growth_str) if pd.notna(growth_str) else 0

                    df_latest_growth_period['TOTAL_GROWTH_NUMERIC'] = df_latest_growth_period['TOTAL_GROWTH_PCT_CALCULATED'].apply(growth_to_numeric)

                    top10_latest_year_states_total_visits = df_latest_growth_period.sort_values(by='TOTAL_VISITORS_YR2', ascending=False).head(10)['STATE_UT'].tolist()
                    df_rising_stars = df_latest_growth_period[
                        ~df_latest_growth_period['STATE_UT'].isin(top10_latest_year_states_total_visits) &
                        (df_latest_growth_period['TOTAL_GROWTH_NUMERIC'] > 10) 
                    ].sort_values(by='TOTAL_GROWTH_NUMERIC', ascending=False).head(5)

                    if not df_rising_stars.empty:
                        data_period_yr1_rising = df_rising_stars['DATA_PERIOD_YR1'].iloc[0]
                        data_period_yr2_rising = df_rising_stars['DATA_PERIOD_YR2'].iloc[0]
                        st.write(f"Emerging destinations based on total visitor growth from {data_period_yr1_rising} to {data_period_yr2_rising} (Min. 10% growth, outside Top 10):")
                        for index, row_star in df_rising_stars.iterrows():
                            delta_val = row_star['TOTAL_GROWTH_PCT_CALCULATED']
                            delta_display = delta_val if delta_val not in ["N/A", "0.00%"] else None 
                            st.metric(label=row_star["STATE_UT"], 
                                      value=f"{int(row_star['TOTAL_VISITORS_YR2']):,} visits", 
                                      delta=delta_display)
                        df_rising_display = df_rising_stars[['STATE_UT', 'TOTAL_VISITORS_YR1', 'TOTAL_VISITORS_YR2', 'TOTAL_GROWTH_PCT_CALCULATED']].copy()
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
        df_arts = run_query_df(conn, "SELECT ArtFormName, StateOfOrigin, Category, BriefDescription, ImageURL, ResponsibleConsumptionTip FROM TraditionalArtForms;")
        if not df_arts.empty:
            states = sorted([s for s in df_arts['STATEOFORIGIN'].unique() if pd.notna(s)])
            categories = sorted([c for c in df_arts['CATEGORY'].unique() if pd.notna(c)])

            selected_state_art = st.selectbox("Filter by State:", ["All"] + states, key="art_state")
            selected_category_art = st.selectbox("Filter by Category:", ["All"] + categories, key="art_cat")

            filtered_arts = df_arts.copy()
            if selected_state_art != "All":
                filtered_arts = filtered_arts[filtered_arts['STATEOFORIGIN'] == selected_state_art]
            if selected_category_art != "All":
                filtered_arts = filtered_arts[filtered_arts['CATEGORY'] == selected_category_art]

            if not filtered_arts.empty:
                for index, row in filtered_arts.iterrows():
                    st.subheader(row['ARTFORMNAME'])
                    if pd.notna(row['IMAGEURL']) and row['IMAGEURL'].strip(): 
                        try:
                            st.image(row['IMAGEURL'], width=300, caption=f"{row['ARTFORMNAME']} from {row['STATEOFORIGIN']}")
                        except Exception as img_e:
                            st.caption(f"Image not available for {row['ARTFORMNAME']}")
                    st.markdown(f"**State of Origin:** {row['STATEOFORIGIN']}")
                    st.markdown(f"**Category:** {row['CATEGORY']}")
                    st.write(row['BRIEFDESCRIPTION'])
                    if pd.notna(row['RESPONSIBLECONSUMPTIONTIP']):
                         st.info(f"💡 Responsible Tip: {row['RESPONSIBLECONSUMPTIONTIP']}")
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
            latest_fy_range_df = run_query_df(conn, "SELECT MAX(Financial_Year_Range) AS LATEST_FY FROM All_Monuments_Stats;")
            if not latest_fy_range_df.empty and pd.notna(latest_fy_range_df['LATEST_FY'].iloc[0]):
                latest_fy = latest_fy_range_df['LATEST_FY'].iloc[0]
                
                query_top10_latest_all_types = f"SELECT DISTINCT Monument_Name FROM Top_Monuments WHERE Financial_Year = '{latest_fy}' AND Monument_Name != 'Others';"
                df_top10_latest_names = run_query_df(conn, query_top10_latest_all_types)
                top10_monument_names_list = df_top10_latest_names['MONUMENT_NAME'].tolist() if not df_top10_latest_names.empty else []

                query_monuments_growth = f"SELECT Circle, Monument_Name, Domestic_Visitors_FY_Start, Foreign_Visitors_FY_Start, Domestic_Visitors_FY_End, Foreign_Visitors_FY_End FROM All_Monuments_Stats WHERE Financial_Year_Range = '{latest_fy}' AND Monument_Name NOT LIKE 'Total%' AND Circle NOT LIKE 'Total%';"
                df_monuments_for_growth = run_query_df(conn, query_monuments_growth)

                if not df_monuments_for_growth.empty:
                    num_cols = ['DOMESTIC_VISITORS_FY_START', 'FOREIGN_VISITORS_FY_START', 'DOMESTIC_VISITORS_FY_END', 'FOREIGN_VISITORS_FY_END']
                    for col in num_cols:
                        df_monuments_for_growth[col] = pd.to_numeric(df_monuments_for_growth[col], errors='coerce').fillna(0)

                    df_monuments_for_growth['TOTAL_VISITORS_FY_START'] = df_monuments_for_growth['DOMESTIC_VISITORS_FY_START'] + df_monuments_for_growth['FOREIGN_VISITORS_FY_START']
                    df_monuments_for_growth['TOTAL_VISITORS_FY_END'] = df_monuments_for_growth['DOMESTIC_VISITORS_FY_END'] + df_monuments_for_growth['FOREIGN_VISITORS_FY_END']
                    
                    df_monuments_for_growth['TOTAL_GROWTH_PCT_CALCULATED'] = df_monuments_for_growth.apply(
                        lambda row: calculate_growth(row['TOTAL_VISITORS_FY_END'], row['TOTAL_VISITORS_FY_START']), axis=1
                    )
                    def growth_to_numeric_mon(growth_str):
                        if isinstance(growth_str, str):
                            if growth_str == "New Growth": return 10000 
                            if growth_str == "N/A" or growth_str == "0.00%": return 0
                            try:
                                return float(growth_str.replace('%',''))
                            except ValueError:
                                return 0
                        return float(growth_str) if pd.notna(growth_str) else 0
                    df_monuments_for_growth['TOTAL_GROWTH_NUMERIC'] = df_monuments_for_growth['TOTAL_GROWTH_PCT_CALCULATED'].apply(growth_to_numeric_mon)

                    df_rising_monuments = df_monuments_for_growth[
                        ~df_monuments_for_growth['MONUMENT_NAME'].isin(top10_monument_names_list) &
                        (df_monuments_for_growth['TOTAL_GROWTH_NUMERIC'] > 20) 
                    ].sort_values(by='TOTAL_GROWTH_NUMERIC', ascending=False).head(7)

                    if not df_rising_monuments.empty:
                        st.write(f"Emerging monument destinations based on total visitor growth ({latest_fy.split('-')[0]} to {latest_fy.split('-')[1]}):")
                        
                        rising_mon_visitor_type = st.radio(
                            "Show visitor trends for:", 
                            ("Domestic Visitors", "Foreign Visitors"), 
                            key="rising_mon_visitor_type_global", 
                            horizontal=True
                        )

                        for index, row_mon_star in df_rising_monuments.iterrows():
                            st.markdown(f"#### {row_mon_star['MONUMENT_NAME']} ({row_mon_star['CIRCLE']})")
                            
                            delta_val_mon = row_mon_star['TOTAL_GROWTH_PCT_CALCULATED']
                            delta_display_mon = delta_val_mon if delta_val_mon not in ["N/A", "0.00%"] else None
                                                        
                            st.metric(label=f"Total Visitors ({latest_fy.split('-')[1]})", 
                                      value=f"{int(row_mon_star['TOTAL_VISITORS_FY_END']):,}", 
                                      delta=delta_display_mon)
                            
                            fy_start_label = latest_fy.split('-')[0]
                            fy_end_label = latest_fy.split('-')[1]

                            if rising_mon_visitor_type == "Domestic Visitors":
                                visitors_start = row_mon_star['DOMESTIC_VISITORS_FY_START']
                                visitors_end = row_mon_star['DOMESTIC_VISITORS_FY_END']
                                chart_title = "Domestic Visitors"
                            else: 
                                visitors_start = row_mon_star['FOREIGN_VISITORS_FY_START']
                                visitors_end = row_mon_star['FOREIGN_VISITORS_FY_END']
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
            query_top10_dom_detail = "SELECT Monument_Name, Number_of_Visitors FROM Top_Monuments WHERE Financial_Year = 'FY2022-23' AND Visitor_Type = 'Domestic' AND Monument_Name != 'Others' ORDER BY Data_Rank;"
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
            circles_df = run_query_df(conn, "SELECT DISTINCT Circle FROM All_Monuments_Stats WHERE Circle NOT LIKE 'Total%' AND Circle IS NOT NULL ORDER BY Circle;")
            if not circles_df.empty:
                selected_circle = st.selectbox("Select ASI Circle:", circles_df['CIRCLE'], key="mon_circle_select_detail")
                if selected_circle:
                    monuments_in_circle_df = run_query_df(conn, f"SELECT DISTINCT Monument_Name FROM All_Monuments_Stats WHERE Circle = '{selected_circle}' AND Monument_Name NOT LIKE 'Total%' ORDER BY Monument_Name;")
                    if not monuments_in_circle_df.empty:
                        selected_monument = st.selectbox("Select Monument:", monuments_in_circle_df['MONUMENT_NAME'], key="mon_name_select_detail")
                        if selected_monument:
                            query_monument = f"SELECT Financial_Year_Range, Domestic_Visitors_FY_Start, Foreign_Visitors_FY_Start, Domestic_Visitors_FY_End, Foreign_Visitors_FY_End FROM All_Monuments_Stats WHERE Monument_Name = '{selected_monument}' AND Circle = '{selected_circle}' ORDER BY Financial_Year_Range;"
                            df_monument_detail = run_query_df(conn, query_monument)
                            if not df_monument_detail.empty:
                                st.write(f"Visitor Statistics for {selected_monument}:")
                                for idx, row_detail in df_monument_detail.iterrows():
                                    st.markdown(f"**Data for: {row_detail['FINANCIAL_YEAR_RANGE']}**")
                                    dom_start = pd.to_numeric(row_detail['DOMESTIC_VISITORS_FY_START'], errors='coerce')
                                    dom_end = pd.to_numeric(row_detail['DOMESTIC_VISITORS_FY_END'], errors='coerce')
                                    for_start = pd.to_numeric(row_detail['FOREIGN_VISITORS_FY_START'], errors='coerce')
                                    for_end = pd.to_numeric(row_detail['FOREIGN_VISITORS_FY_END'], errors='coerce')

                                    domestic_growth_calculated = calculate_growth(dom_end, dom_start)
                                    foreign_growth_calculated = calculate_growth(for_end, for_start)
                                    
                                    col1_mon, col2_mon = st.columns(2)
                                    with col1_mon:
                                        st.metric(f"Domestic Visitors ({row_detail['FINANCIAL_YEAR_RANGE'].split('-')[0]})", f"{int(dom_start):,}" if pd.notna(dom_start) else "N/A")
                                        st.metric(f"Domestic Visitors ({row_detail['FINANCIAL_YEAR_RANGE'].split('-')[1]})", f"{int(dom_end):,}" if pd.notna(dom_end) else "N/A", delta=domestic_growth_calculated if domestic_growth_calculated not in ["0.00%", "N/A"] else None)
                                    with col2_mon:
                                        st.metric(f"Foreign Visitors ({row_detail['FINANCIAL_YEAR_RANGE'].split('-')[0]})", f"{int(for_start):,}" if pd.notna(for_start) else "N/A")
                                        st.metric(f"Foreign Visitors ({row_detail['FINANCIAL_YEAR_RANGE'].split('-')[1]})", f"{int(for_end):,}" if pd.notna(for_end) else "N/A", delta=foreign_growth_calculated if foreign_growth_calculated not in ["0.00%", "N/A"] else None)
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

            df_overall_funds = run_query_df(conn, "SELECT Scheme_Name, Funds_2019_20, Funds_2020_21, Funds_2021_22, Funds_2022_23, Funds_2023_24 FROM SchemeWiseFundsReleased WHERE Scheme_Name NOT LIKE 'Total%' AND Scheme_Name NOT LIKE 'Grand Total';")
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
            df_summary = run_query_df(conn, "SELECT SchemeID, SchemeName, AdministeringBody, FocusArea, DataPoint_Example_State_UT, DataPoint_Example_Value, RelevanceToPlatform FROM ArtistSupportSchemeSummary;")
            if not df_summary.empty:
                for index, row in df_summary.iterrows():
                    st.markdown(f"#### {row['SCHEMENAME']}")
                    with st.expander("Details", expanded=False):
                        st.markdown(f"**Administering Body:** {row['ADMINISTERINGBODY']}")
                        st.markdown(f"**Focus Area:** {row['FOCUSAREA']}")
                        if pd.notna(row['DATAPOINT_EXAMPLE_STATE_UT']) and pd.notna(row['DATAPOINT_EXAMPLE_VALUE']):
                            st.markdown(f"**Impact:** {row['DATAPOINT_EXAMPLE_VALUE']} in {row['DATAPOINT_EXAMPLE_STATE_UT']}")
                        st.write(f"**Relevance to Platform:** {row['RELEVANCETOPLATFORM']}")
                    st.markdown("---")
            else: 
                st.write("No data for Artist Support Schemes Overview.")
        except Exception as e:
            st.error(f"Error loading Artist Support Schemes Overview: {e}")

    with tab_explore_grants:
        st.subheader("Explore Specific Scheme Grants & Data")
        specific_scheme_table_map = {
            "Senior/Young Artist Scheme (Beneficiaries)": "SeniorYoungArtistScheme",
            "Building Grants (Studio Theatre)": "BuildingGrantsStudioTheatre",
            "Veteran Artists (Applications Received)": "VeteranArtistsApplications",
            "Guru-Shishya Parampara (Assistance)": "GuruShishyaParamparaAssistance",
            "Cultural Function & Production Grants": "CulturalFunctionProductionGrant",
            "Museum Development Grants": "MuseumGrantSchemeFunds",
            "ASI Monument Preservation Expenditure (National)": "ASIMonumentPreservationExpenditure"
        }
        selected_specific_scheme_display = st.selectbox("Select Specific Scheme/Grant Data:", list(specific_scheme_table_map.keys()), key="specific_scheme_select_tab3")
        selected_specific_table = specific_scheme_table_map[selected_specific_scheme_display]

        try:
            if selected_specific_table == "SeniorYoungArtistScheme":
                st.markdown("##### Senior/Young Artist Scheme Beneficiary Data")
                df_syas = run_query_df(conn, f"SELECT NEW_STATES as State, SUBJECT, GENDER, AGE, PHY_HANDICAPED, SC_ST, USER_ID, FIELD_ID FROM {selected_specific_table} ORDER BY State, AGE;")
                
                if not df_syas.empty:
                    df_syas['SUBJECT_CLEAN'] = df_syas['SUBJECT'].str.strip().str.title()

                    unique_states_syas = sorted([s for s in df_syas['STATE'].unique() if pd.notna(s)])
                    selected_state_syas_tab3 = st.selectbox("Filter by State:", ["All"] + unique_states_syas, key="syas_state_filter_tab3")
                    
                    df_filtered_syas = df_syas.copy()
                    if selected_state_syas_tab3 != "All":
                        df_filtered_syas = df_filtered_syas[df_filtered_syas['STATE'] == selected_state_syas_tab3]

                    display_cols_syas = ['STATE', 'SUBJECT', 'GENDER', 'AGE', 'PHY_HANDICAPED']
                    df_display_table_syas = df_filtered_syas[display_cols_syas].copy()
                    df_display_table_syas.index = np.arange(1, len(df_display_table_syas) + 1)
                    st.dataframe(df_display_table_syas.head(50))
                    
                    if not df_filtered_syas.empty:
                        st.markdown("###### Summary Charts")
                        
                        st.markdown("Distribution of Beneficiaries by State (Selected Filter):")
                        beneficiaries_by_state_filtered = df_filtered_syas.groupby('STATE').size().reset_index(name='Number of Beneficiaries').sort_values(by='Number of Beneficiaries', ascending=False)
                        st.bar_chart(beneficiaries_by_state_filtered.head(15).set_index('STATE'))

                else: 
                    st.write(f"No data available for {selected_specific_scheme_display}.")
            
            elif selected_specific_table == "BuildingGrantsStudioTheatre":
                st.markdown("##### Building Grants including Studio Theatre (Amount in Lakhs)")
                df_data = run_query_df(conn, f"SELECT State_UT, Amount_21_22, Amount_22_23, Amount_Released_Authorized_23_24 FROM {selected_specific_table} WHERE State_UT NOT LIKE 'Total%';")
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

            elif selected_specific_table == "VeteranArtistsApplications":
                st.markdown("##### Applications for Veteran Artists Financial Assistance")
                df_data = run_query_df(conn, f"SELECT State_UT, Apps_2019_20, Apps_2020_21, Apps_2021_22, Apps_2022_23, Apps_2023_24 FROM {selected_specific_table} WHERE State_UT NOT LIKE 'Total%';")
                if not df_data.empty:
                    df_data.columns = ["State/UT", "Apps 19-20", "Apps 20-21", "Apps 21-22", "Apps 22-23", "Apps 23-24"]
                    latest_year_col_vaa = "Apps 23-24" 
                    for col in df_data.columns[1:]: df_data[col] = pd.to_numeric(df_data[col], errors='coerce').fillna(0)
                    st.bar_chart(df_data.sort_values(by=latest_year_col_vaa, ascending=False).head(15).set_index('State/UT')[latest_year_col_vaa])
                    df_data.index = np.arange(1, len(df_data) + 1)
                    st.dataframe(df_data)
                else: st.write(f"No data for {selected_specific_scheme_display}.")
            
            elif selected_specific_table == "GuruShishyaParamparaAssistance":
                st.markdown("##### Guru-Shishya Parampara Assistance (Amount in Lakhs)")
                df_data = run_query_df(conn, f"SELECT State_UT, Amount_21_22, Amount_22_23, Amount_Released_Authorized_23_24 FROM {selected_specific_table} WHERE State_UT NOT LIKE 'Total%' AND State_UT IS NOT NULL;")
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

            elif selected_specific_table == "CulturalFunctionProductionGrant":
                st.markdown("##### Cultural Function & Production Grants (Amount in Lakhs)")
                df_data = run_query_df(conn, f"SELECT State_UT, Amount_21_22, Amount_22_23, Amount_Released_23_24 FROM {selected_specific_table} WHERE State_UT NOT LIKE 'Total%' AND State_UT IS NOT NULL;") 
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

            elif selected_specific_table == "MuseumGrantSchemeFunds":
                st.markdown("##### Museum Development Grants (Funds Released)")
                df_data = run_query_df(conn, f"SELECT State_Name, Organization_Name, Type_of_Museum, Funds_2019_20, Funds_2020_21, Funds_2021_22, Funds_2022_23, Funds_2023_24 FROM {selected_specific_table} WHERE State_Name NOT LIKE 'Total%' AND State_Name IS NOT NULL;")
                if not df_data.empty:
                    fund_cols_map = {'FUNDS_2019_20': '2019-20', 'FUNDS_2020_21': '2020-21', 'FUNDS_2021_22': '2021-22', 'FUNDS_2022_23': '2022-23', 'FUNDS_2023_24': '2023-24'}
                    for col_db_original_case in fund_cols_map.keys():
                        df_data[col_db_original_case] = pd.to_numeric(df_data[col_db_original_case].replace('NA', np.nan), errors='coerce').fillna(0)

                    unique_states_museum = sorted([s for s in df_data['STATE_NAME'].unique() if pd.notna(s)])
                    selected_states_museum = st.multiselect("Select State(s):", unique_states_museum, default=unique_states_museum[:min(3, len(unique_states_museum))], key="museum_state_multiselect_revised")
                    
                    available_years_museum = list(fund_cols_map.values())
                    selected_year_museum_display = st.selectbox("Select Year to View Funds:", available_years_museum, key="museum_year_select_revised")

                    selected_year_db_col_actual_case = [k for k, v in fund_cols_map.items() if v == selected_year_museum_display][0]


                    if selected_states_museum and selected_year_museum_display:
                        df_filtered_museum = df_data[df_data['STATE_NAME'].isin(selected_states_museum)]
                        st.bar_chart(df_filtered_museum.groupby('STATE_NAME')[selected_year_db_col_actual_case].sum())
                    
                    df_data.index = np.arange(1, len(df_data) + 1)
                    st.dataframe(df_data)
                else: st.write(f"No data available for {selected_specific_scheme_display}.")
            
            elif selected_specific_table == "ASIMonumentPreservationExpenditure":
                st.markdown("##### ASI Monument Preservation Expenditure (National Level, Amount in Crores)")
                df_asi_exp = run_query_df(conn, f"SELECT Year, Allocation, Expenditure FROM {selected_specific_table};")
                if not df_asi_exp.empty:
                    df_asi_exp.columns = ["Financial Year", "Allocation (Crores)", "Expenditure (Crores)"]
                    st.line_chart(df_asi_exp.set_index("Financial Year"))
                    df_asi_exp.index = np.arange(1, len(df_asi_exp) + 1)
                    st.dataframe(df_asi_exp)
                else: st.write(f"No data for {selected_specific_scheme_display}.")
            
            else: 
                st.markdown(f"##### Data for: {selected_specific_scheme_display}")
                try:
                    df_generic_scheme = run_query_df(conn, f"SELECT * FROM {selected_specific_table} WHERE (COLUMN_EXISTS('State_UT') AND State_UT NOT LIKE 'Total%') OR (COLUMN_EXISTS('Scheme_Name') AND Scheme_Name NOT LIKE 'Total%') OR (NOT COLUMN_EXISTS('State_UT') AND NOT COLUMN_EXISTS('Scheme_Name')) LIMIT 100;")
                except: 
                     df_generic_scheme = run_query_df(conn, f"SELECT * FROM {selected_specific_table} LIMIT 100;")
                
                if not df_generic_scheme.empty:
                    df_generic_scheme.index = np.arange(1, len(df_generic_scheme) + 1)
                    st.dataframe(df_generic_scheme)
                else:
                    st.write(f"No data available or table structure not fully anticipated for: {selected_specific_scheme_display}.")
        except Exception as e:
            st.error(f"An error occurred while fetching data for {selected_specific_scheme_display}: {e}")


elif st.session_state.app_mode == "📅 Plan Your Visit (Seasonality)":
    st.title("📅 Plan Your Visit: Tourism Seasonality")
    st.markdown("Understand the general flow of tourist arrivals to India throughout the year.")
    
    st.subheader("Foreign Tourist Arrivals (FTAs) Seasonality")
    try:
        query_seasonality_fta = """
        WITH RankedFTAs AS (
            SELECT
                Month_Name,
                Data_Year,
                FTA_Count,
                ROW_NUMBER() OVER (PARTITION BY Month_Name, Data_Year ORDER BY Report_Source_Year DESC) as rn
            FROM FTAMonthly 
        )
        SELECT Month_Name, Data_Year, FTA_Count
        FROM RankedFTAs
        WHERE rn = 1; 
        """ 
        
        df_season_fta = run_query_df(conn, query_seasonality_fta)

        if not df_season_fta.empty:
            month_order = ["January", "February", "March", "April", "May", "June", 
                           "July", "August", "September", "October", "November", "December"]
            
            df_season_fta['MONTH_NAME'] = pd.Categorical(df_season_fta['MONTH_NAME'], categories=month_order, ordered=True)
            df_season_fta = df_season_fta.sort_values(by=['DATA_YEAR', 'MONTH_NAME'])

            available_years_fta = sorted(df_season_fta['DATA_YEAR'].unique(), reverse=True)
            if available_years_fta:
                selected_year_fta = st.selectbox("Select Year to View FTA Seasonality:", available_years_fta, key="fta_year_select")
                
                df_year_season_fta = df_season_fta[df_season_fta['DATA_YEAR'] == selected_year_fta]

                if not df_year_season_fta.empty:
                    st.write(f"Foreign Tourist Arrivals in {selected_year_fta}")
                    st.line_chart(df_year_season_fta.set_index('MONTH_NAME')['FTA_COUNT'])
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
        df_gems = run_query_df(conn, "SELECT GemName, State, Region, Type, CulturalSignificance, WhyPotentiallyUntouched, ResponsibleTravelGuideline, ImageURL FROM UntouchedGems;") 
        
        if not df_gems.empty:
            for index, row in df_gems.iterrows():
                st.subheader(row['GEMNAME'])
                if pd.notna(row['IMAGEURL']) and row['IMAGEURL'].strip():
                    try:
                        st.image(row['IMAGEURL'], caption=row['GEMNAME'], width=400) 
                    except Exception as img_e:
                        st.caption(f"Could not load image for {row['GEMNAME']}.")
                else:
                    st.caption(f"Image not available for {row['GEMNAME']}.")

                st.markdown(f"**State:** {row['STATE']} | **Region:** {row['REGION']} | **Type:** {row['TYPE']}")
                st.write(f"**Cultural Significance:** {row['CULTURALSIGNIFICANCE']}")
                st.info(f"**Why Potentially Untouched?** {row['WHYPOTENTIALLYUNTOUCHED']}")
                st.success(f"🌿 **Responsible Travel Guideline:** {row['RESPONSIBLETRAVELGUIDELINE']}")
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

