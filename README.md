# Sanskriti Setu: Bridging Art, Culture, and Tourism with Tech

**Sanskriti Setu** is an interactive Streamlit application designed to showcase India's rich traditional art forms, help users uncover diverse cultural experiences (including popular destinations and emerging trends), explore government support schemes for arts and culture, and promote responsible tourism practices. This project leverages a data-first approach, utilizing diverse datasets processed and stored in Snowflake to power its insights and visualizations.

**Hackathon Theme:** Art, Culture and Tourism: Bridging art, culture and tourism with tech.

---

## Core Features

* **🏠 Home & Tourism Overview:** Provides a dynamic snapshot of India's tourism landscape. Users can select a year and view the Top 10 states by either domestic or foreign visitor arrivals. It also highlights "States with Rising Tourism Popularity" – states not in the Top 10 but showing significant overall visitor growth.
* **🎨 Traditional Art Forms Explorer:** Allows users to discover and learn about various Indian traditional arts, filterable by state and category. Each art form is presented with its description, state of origin, category, materials used, key identifying features, an image, and a responsible consumption tip.
* **🏛️ Explore Cultural Destinations:**
    * **Rising Popularity - Monuments Tab:** Identifies monuments (outside the absolute Top 10 for the latest financial year) that have shown significant percentage growth in total visitors. Users can toggle between domestic and foreign visitor trends for these rising monuments, displayed in bar charts.
    * **Iconic Monuments (Detailed Trends) Tab:** Offers a detailed look at visitor statistics for specific ASI-protected monuments. Users can select an ASI Circle and then a monument to see year-on-year visitor trends (domestic vs. foreign) with dynamically calculated percentage growth.
* **💰 Government Support & Schemes:** A dedicated section with three tabs:
    * **Overall Scheme Funding (National):** Visualizes funding trends for major national cultural schemes over multiple years using a line chart (worm graph), allowing users to select specific schemes for comparison.
    * **Artist Support Schemes Overview:** Presents a descriptive summary (as a table) of various schemes aimed at supporting artists, detailing their administering body, focus area, and illustrative impact.
    * **Explore Specific Scheme Grants:** Allows users to delve into detailed data for specific grant programs like the Senior/Young Artist Scheme (with state filters and consolidated subject analysis), Building Grants, Veteran Artists Applications, Guru-Shishya Parampara Assistance (with state-selected trend graphs), Cultural Function & Production Grants (with state-selected trend graphs), Museum Development Grants (with state and year selection for fund display), and ASI Monument Preservation Expenditure.
* **📅 Plan Your Visit (Seasonality):** Shows monthly trends for Foreign Tourist Arrivals (FTAs) for user-selected years, helping to understand peak and lean tourism seasons.
* **💎 Untouched Cultural Gems:** Features a curated list of lesser-known destinations with rich cultural value, complete with images, descriptions of their significance, reasons for being "untouched," and specific responsible travel guidelines.
* **🌿 Responsible Tourism:** Provides key principles and actionable tips for travellers to engage with India's heritage responsibly.

---

## Live Demo

Experience Sanskriti Setu live:
**[https://sanskriti-setu-lxhny3ysgrasnhtkwwmbzd.streamlit.app/](https://sanskriti-setu-lxhny3ysgrasnhtkwwmbzd.streamlit.app/)**

---

## Tech Stack

* **Frontend & Application Logic:** Streamlit (Python)
* **Data Storage & Warehousing:** Snowflake
* **Data Analysis & Manipulation (in Streamlit):** Pandas, NumPy
* **Key Python Libraries:** `streamlit`, `snowflake-connector-python`, `pandas`, `numpy`

---

## Snowflake Integration Details

Snowflake serves as the central data warehouse for संस्कृति सेतु, enabling efficient storage, management, and querying of diverse datasets related to tourism, art forms, and government schemes.

* **Data Sources:**
    * Official "India Tourism Statistics" PDF reports (2022, 2023) from the Ministry of Tourism: Relevant tables were manually extracted into CSVs (e.g., state-wise visits, monument-wise visits, monthly FTAs, top monuments).
    * Various datasets from `data.gov.in` concerning government schemes, financial assistance to artists, grants, and cultural programs. These were provided as multiple CSV files and one JSON file (`Senior_Young_Artist_Scheme.json`).
    * Manually curated CSVs for "Traditional Art Forms," "Untouched Cultural Gems," and a summary of "Artist Support Schemes."
* **Data Loading & Transformation in Snowflake:**
    * All CSV and JSON files were uploaded to Snowflake internal stages.
    * Custom `FILE FORMAT` objects were created in Snowflake to handle standard CSVs, pipe-delimited CSVs (`ArtistSupportSchemeData_Summary.csv`), and JSON data (using `TYPE = JSON STRIP_OUTER_ARRAY = TRUE` and `MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE` for `Senior_Young_Artist_Scheme.json`).
    * `COPY INTO` commands were used to load data into structured tables within a dedicated `TOURISM_DATA` schema in the `INDIA_CULTURE_TOURISM_DB` database.
    * **Data Normalization:** For monthly Foreign Tourist Arrival (FTA) data, which was originally in a wide format (years as columns), Snowflake SQL's `UNPIVOT` function was used to transform it into a long, normalized format (`FTAMonthly` table) suitable for time-series analysis and charting in Streamlit.
    * Data cleaning (e.g., handling 'NA' values, standardizing column names, ensuring correct data types) was performed partly during CSV preparation and partly via SQL transformations or data type definitions during table creation in Snowflake.
* **Key Snowflake Tables Used:**
    * `State_Tourism_Visits`: State-wise domestic and foreign visitor data across different years.
    * `All_Monuments_Stats`: Detailed monument-wise visitor statistics for multiple financial year ranges.
    * `Top_Monuments`: Lists of top 10 monuments by domestic/foreign visitors for specific financial years.
    * `FTAMonthly`: Normalized monthly foreign tourist arrival data.
    * `TraditionalArtForms`: Curated list of art forms with descriptions, origins, categories, and image URLs.
    * `UntouchedGems`: Curated list of lesser-known cultural destinations with details and image URLs.
    * `ArtistSupportSchemeSummary`: Overview of various artist support schemes.
    * `SeniorYoungArtistScheme`: Detailed beneficiary data for this scheme.
    * `BuildingGrantsStudioTheatre`, `VeteranArtistsApplications`, `GuruShishyaParamparaAssistance`, `CulturalFunctionProductionGrant`, `SchemeWiseFundsReleased`, `MuseumGrantSchemeFunds`, `ASIMonumentPreservationExpenditure`: Tables storing data for specific government schemes and expenditures.
* **Querying from Streamlit:** The Streamlit application connects to Snowflake using the `snowflake-connector-python`. All dynamic data displayed in the app is fetched via SQL queries executed against these Snowflake tables. Streamlit's caching (`@st.cache_resource` for connections, `@st.cache_data` for query results) is employed to optimize performance and reduce redundant database calls.

---

## Setup and Installation (for Local Execution)

1.  **Clone the Repository:**

2.  **Create a Python Virtual Environment:**
    ```bash
    python -m venv .venv
    # On Windows:
    .venv\Scripts\activate
    # On macOS/Linux:
    source .venv/bin/activate
    ```
3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure Snowflake Credentials:**
    * Create a directory named `.streamlit` in the project root if it doesn't exist.
    * Inside `.streamlit`, create a file named `secrets.toml`.
    * Add your Snowflake credentials to `secrets.toml` as follows (replace placeholders):
        ```toml
        [snowflake]
        user = "YOUR_SNOWFLAKE_USERNAME"
        password = "YOUR_SNOWFLAKE_PASSWORD"
        account = "YOUR_SNOWFLAKE_ACCOUNT_IDENTIFIER"
        warehouse = "HACKATHON_WH" 
        database = "YOUR_DB" 
        schema = "TOURISM_DATA" 
        # role = "YOUR_SNOWFLAKE_ROLE" # Optional: specify a role
        ```
    * **IMPORTANT:** Do not commit your actual `secrets.toml` file to a public Git repository. Add `.streamlit/secrets.toml` to your `.gitignore` file. You can provide a `secrets.example.toml` with placeholders as a template.
5.  **Run the Streamlit Application:**
    ```bash
    streamlit run app.py
    ```

