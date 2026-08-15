import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

# ── Database connection ──────────────────────────────────────────────────────
conn = sqlite3.connect('food_waste_management.db', check_same_thread=False)

# ── Helper: load any table from DB ──────────────────────────────────────────
def load_table(table_name):
    return pd.read_sql_query(f"SELECT * FROM {table_name}", conn)

# ── Table name map (display name → SQL table name) ──────────────────────────
TABLE_MAP = {
    "Receivers":     "receivers",
    "Providers":     "providers",
    "Food Listings": "food_listings",
    "Claims":        "claims",
}

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Local Food Waste Management System", layout="wide")

# ── Sidebar navigation ───────────────────────────────────────────────────────
st.sidebar.title("Navigation")
section = st.sidebar.radio("Go to", [
    "Project Introduction",
    "CRUD Operations",
    "View Tables",
    "SQL Queries and Visualizations",
    "Learned SQL Queries",
    "User Introduction",
])

# ════════════════════════════════════════════════════════════════════════════
# 1. PROJECT INTRODUCTION
# ════════════════════════════════════════════════════════════════════════════
if section == "Project Introduction":
    st.title("🌱 Local Food Waste Management System")
    st.markdown("""
    This application helps **reduce food wastage** by connecting surplus food providers
    with individuals and organisations in need.

    **What this system does:**
    - Restaurants and individuals can **list surplus food**
    - NGOs or individuals in need can **claim the food**
    - All data is stored in a **SQL database**
    - A Streamlit interface enables **filtering, CRUD operations, and analysis**

    **Datasets used:**
    | Dataset | Description |
    |---|---|
    | Providers | Restaurants, grocery stores, supermarkets listing surplus food |
    | Receivers | NGOs, community centres, individuals claiming food |
    | Food Listings | Available food items with quantity, expiry, location |
    | Claims | Records of food claimed by receivers |

    Use the **sidebar** to navigate between sections.
    """)

# ════════════════════════════════════════════════════════════════════════════
# 2. CRUD OPERATIONS
# ════════════════════════════════════════════════════════════════════════════
elif section == "CRUD Operations":
    st.title("CRUD Operations")

    # Initialise session state from DB (not CSVs)
    if 'tables' not in st.session_state:
        st.session_state['tables'] = {
            display: load_table(sql)
            for display, sql in TABLE_MAP.items()
        }

    # Table selector
    selected_display = st.selectbox("Select a Table to Modify:", list(TABLE_MAP.keys()))
    selected_sql     = TABLE_MAP[selected_display]
    df               = st.session_state['tables'][selected_display]

    crud_action = st.radio(
        "Select Operation:",
        ["Create (Add Row)", "Read (View Table)", "Update (Edit Row)", "Delete (Remove Row)"]
    )

    # ── CREATE ───────────────────────────────────────────────────────────────
    if crud_action == "Create (Add Row)":
        st.subheader("Add a new row")
        new_data = {}
        for col in df.columns:
            new_data[col] = st.text_input(f"Enter {col}")

        if st.button("Add Row"):
            new_row = pd.DataFrame([new_data])
            new_row.to_sql(selected_sql, conn, if_exists='append', index=False)
            # Reload from DB so every section stays in sync
            st.session_state['tables'][selected_display] = load_table(selected_sql)
            st.success("Row added and saved to database ✅")
            st.dataframe(st.session_state['tables'][selected_display])

    # ── READ ─────────────────────────────────────────────────────────────────
    elif crud_action == "Read (View Table)":
        st.subheader(f"{selected_display} table")
        st.dataframe(df)
        st.write(f"Total rows: **{len(df)}**")

    # ── UPDATE ───────────────────────────────────────────────────────────────
    elif crud_action == "Update (Edit Row)":
        st.subheader("Edit an existing row")
        row_idx      = st.number_input("Row index to update", min_value=0, max_value=len(df)-1, step=1)
        selected_row = df.iloc[int(row_idx)].to_dict()

        updated_data = {}
        for col, val in selected_row.items():
            updated_data[col] = st.text_input(f"{col}", value=str(val))

        if st.button("Update Row"):
            new_df = df.copy()
            for col, val in updated_data.items():
                new_df.at[int(row_idx), col] = val
            new_df.to_sql(selected_sql, conn, if_exists='replace', index=False)
            st.session_state['tables'][selected_display] = load_table(selected_sql)
            st.success("Row updated and saved to database ✅")
            st.dataframe(st.session_state['tables'][selected_display])

    # ── DELETE ───────────────────────────────────────────────────────────────
    elif crud_action == "Delete (Remove Row)":
        st.subheader("Remove a row")
        st.dataframe(df)
        row_idx = st.number_input("Row index to delete", min_value=0, max_value=len(df)-1, step=1)

        if st.button("Delete Row"):
            new_df = df.drop(int(row_idx)).reset_index(drop=True)
            new_df.to_sql(selected_sql, conn, if_exists='replace', index=False)
            st.session_state['tables'][selected_display] = load_table(selected_sql)
            st.success("Row deleted and saved to database ✅")
            st.dataframe(st.session_state['tables'][selected_display])

# ════════════════════════════════════════════════════════════════════════════
# 3. VIEW TABLES  (reads from DB — always reflects latest CRUD changes)
# ════════════════════════════════════════════════════════════════════════════
elif section == "View Tables":
    st.title("View Tables")

    table_option = st.selectbox("Choose Table", list(TABLE_MAP.keys()))
    df = load_table(TABLE_MAP[table_option])   # always fresh from DB

    st.subheader(f"{table_option} Table")
    st.write(f"Total rows: **{len(df)}**")

    # Dynamic filters
    filter_columns = st.multiselect("Select columns to filter by:", options=df.columns.tolist(), default=[])
    filtered_df = df.copy()

    for col in filter_columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            min_val, max_val = float(df[col].min()), float(df[col].max())
            selected_range = st.slider(f"Filter {col}:", min_val, max_val, (min_val, max_val))
            filtered_df = filtered_df[
                (filtered_df[col] >= selected_range[0]) & (filtered_df[col] <= selected_range[1])
            ]
        else:
            unique_vals   = df[col].dropna().unique().tolist()
            selected_vals = st.multiselect(f"Filter {col}:", unique_vals, default=unique_vals)
            filtered_df   = filtered_df[filtered_df[col].isin(selected_vals)]

    st.dataframe(filtered_df)
    st.write(f"Rows shown: **{len(filtered_df)}**")

# ════════════════════════════════════════════════════════════════════════════
# 4. SQL QUERIES AND VISUALIZATIONS
# ════════════════════════════════════════════════════════════════════════════
elif section == "SQL Queries and Visualizations":
    st.title("SQL Analysis")

    def run_sql(query, params=None):
        if params:
            return pd.read_sql_query(query, conn, params=params)
        return pd.read_sql_query(query, conn)

    sql_questions = {
        "Q1 — How many food providers and receivers are there in each city?": {
            "query": """
                SELECT p.City,
                       COUNT(DISTINCT p.Provider_ID) AS provider_count,
                       COUNT(DISTINCT r.Receiver_ID) AS receiver_count
                FROM providers p
                LEFT JOIN receivers r ON p.City = r.City
                GROUP BY p.City
                ORDER BY provider_count DESC
            """,
            "chart": "bar", "x": "City", "y": "provider_count"
        },
        "Q2 — Which provider type contributes the most food?": {
            "query": """
                SELECT Provider_Type, SUM(Quantity) AS Total_Quantity
                FROM food_listings
                GROUP BY Provider_Type
                ORDER BY Total_Quantity DESC
            """,
            "chart": "bar", "x": "Provider_Type", "y": "Total_Quantity"
        },
        "Q3 — Contact information of food providers in a specific city": {
            "query": "SELECT Name, Contact FROM providers WHERE City = ?",
            "chart": None, "city_param": True
        },
        "Q4 — Which receivers have claimed the most food?": {
            "query": """
                SELECT receivers.Name, SUM(food_listings.Quantity) AS total_claimed
                FROM claims
                JOIN receivers ON claims.Receiver_ID = receivers.Receiver_ID
                JOIN food_listings ON claims.Food_ID = food_listings.Food_ID
                WHERE claims.Status = 'Completed'
                GROUP BY receivers.Name
                ORDER BY total_claimed DESC
            """,
            "chart": "bar", "x": "Name", "y": "total_claimed"
        },
        "Q5 — Total quantity of food available from all providers": {
            "query": "SELECT SUM(Quantity) AS Total_Quantity FROM food_listings",
            "chart": None
        },
        "Q6 — Which city has the highest number of food listings?": {
            "query": """
                SELECT Location, COUNT(*) AS total_count
                FROM food_listings
                GROUP BY Location
                ORDER BY total_count DESC
                LIMIT 1
            """,
            "chart": None
        },
        "Q7 — Most commonly available food types": {
            "query": """
                SELECT Food_Type, COUNT(*) AS Count
                FROM food_listings
                GROUP BY Food_Type
                ORDER BY Count DESC
            """,
            "chart": "pie", "x": "Food_Type", "y": "Count"
        },
        "Q8 — How many food claims have been made for each food item?": {
            "query": """
                SELECT food_listings.Food_Name, COUNT(claims.Claim_ID) AS No_of_Claims
                FROM food_listings
                LEFT JOIN claims ON food_listings.Food_ID = claims.Food_ID
                GROUP BY food_listings.Food_Name
                ORDER BY No_of_Claims DESC
            """,
            "chart": "bar", "x": "Food_Name", "y": "No_of_Claims"
        },
        "Q9 — Provider with the highest number of successful food claims": {
            "query": """
                SELECT providers.Name, COUNT(*) AS Successful_Claims
                FROM claims
                JOIN food_listings ON claims.Food_ID = food_listings.Food_ID
                JOIN providers ON food_listings.Provider_ID = providers.Provider_ID
                WHERE claims.Status = 'Completed'
                GROUP BY providers.Provider_ID
                ORDER BY Successful_Claims DESC
                LIMIT 1
            """,
            "chart": None
        },
        "Q10 — Percentage of claims: Completed vs Pending vs Cancelled": {
            "query": """
                SELECT Status,
                       COUNT(*) * 100.0 / (SELECT COUNT(*) FROM claims) AS Percentage
                FROM claims
                GROUP BY Status
            """,
            "chart": "pie", "x": "Status", "y": "Percentage"
        },
        "Q11 — Average quantity of food claimed per receiver": {
            "query": """
                SELECT receivers.Name,
                       ROUND(AVG(food_listings.Quantity), 2) AS Average_Quantity
                FROM claims
                JOIN receivers ON claims.Receiver_ID = receivers.Receiver_ID
                JOIN food_listings ON claims.Food_ID = food_listings.Food_ID
                GROUP BY receivers.Receiver_ID, receivers.Name
                ORDER BY Average_Quantity DESC
            """,
            "chart": "bar", "x": "Name", "y": "Average_Quantity"
        },
        "Q12 — Which meal type is claimed the most?": {
            "query": """
                SELECT food_listings.Meal_Type, COUNT(*) AS most_claimed
                FROM claims
                JOIN food_listings ON claims.Food_ID = food_listings.Food_ID
                GROUP BY Meal_Type
                ORDER BY most_claimed DESC
                LIMIT 1
            """,
            "chart": None
        },
        "Q13 — Total quantity of food donated by each provider": {
            "query": """
                SELECT providers.Name, SUM(food_listings.Quantity) AS Total_Quantity
                FROM food_listings
                JOIN providers ON providers.Provider_ID = food_listings.Provider_ID
                GROUP BY providers.Provider_ID, providers.Name
                ORDER BY Total_Quantity DESC
            """,
            "chart": "bar", "x": "Name", "y": "Total_Quantity"
        },
    }

    selected_question = st.selectbox("Choose a Query", list(sql_questions.keys()))
    q = sql_questions[selected_question]

    # Handle city parameter query
    if q.get("city_param"):
        city_input = st.text_input("Enter city name (e.g. Chennai):")
        if city_input:
            result_df = run_sql(q["query"], params=(city_input,))
        else:
            st.info("Enter a city name above to see results.")
            st.stop()
    else:
        result_df = run_sql(q["query"])

    st.dataframe(result_df)

    # Chart
    if q.get("chart") == "bar" and not result_df.empty:
        fig = px.bar(result_df, x=q["x"], y=q["y"], title=selected_question)
        st.plotly_chart(fig, use_container_width=True)
    elif q.get("chart") == "pie" and not result_df.empty:
        fig = px.pie(result_df, names=q["x"], values=q["y"], title=selected_question)
        st.plotly_chart(fig, use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# 5. LEARNED SQL QUERIES
# ════════════════════════════════════════════════════════════════════════════
elif section == "Learned SQL Queries":
    st.title("Learners SQL Analysis")

    def run_sql(query):
        return pd.read_sql_query(query, conn)

    sql_questions = {
        "Q14 — Which city has the highest number of different provider types?": """
            SELECT City, COUNT(DISTINCT Type) AS Different_Types
            FROM providers
            GROUP BY City
            ORDER BY Different_Types DESC
            LIMIT 1
        """,
        "Q15 — Top 5 food items with the largest total quantity listed": """
            SELECT Food_Name, SUM(Quantity) AS Total_Quantity
            FROM food_listings
            GROUP BY Food_Name
            ORDER BY Total_Quantity DESC
            LIMIT 5
        """,
        "Q16 — Providers who have never listed any food": """
            SELECT providers.Provider_ID, providers.Name
            FROM providers
            LEFT JOIN food_listings ON food_listings.Provider_ID = providers.Provider_ID
            WHERE food_listings.Provider_ID IS NULL
        """,
        "Q17 — Receiver type with the most completed claims": """
            SELECT receivers.Type, COUNT(*) AS high_claim
            FROM receivers
            JOIN claims ON receivers.Receiver_ID = claims.Receiver_ID
            WHERE claims.Status = 'Completed'
            GROUP BY receivers.Type
            ORDER BY high_claim DESC
            LIMIT 1
        """,
        "Q18 — Average quantity of food listed per provider": """
            SELECT providers.Name, ROUND(AVG(food_listings.Quantity), 2) AS Average
            FROM food_listings
            JOIN providers ON food_listings.Provider_ID = providers.Provider_ID
            GROUP BY food_listings.Provider_ID
            ORDER BY Average DESC
        """,
        "Q19 — Which food type is claimed the most?": """
            SELECT food_listings.Food_Type, COUNT(*) AS Most_Claimed
            FROM claims
            JOIN food_listings ON food_listings.Food_ID = claims.Food_ID
            GROUP BY food_listings.Food_Type
            ORDER BY Most_Claimed DESC
            LIMIT 1
        """,
        "Q20 — Food listings that have never been claimed": """
            SELECT food_listings.Food_Name
            FROM food_listings
            LEFT JOIN claims ON food_listings.Food_ID = claims.Food_ID
            WHERE claims.Food_ID IS NULL
            GROUP BY food_listings.Food_Name
        """,
    }

    selected_question = st.selectbox("Choose a Query", list(sql_questions.keys()))
    result_df = run_sql(sql_questions[selected_question])
    st.dataframe(result_df)

# ════════════════════════════════════════════════════════════════════════════
# 6. USER INTRODUCTION
# ════════════════════════════════════════════════════════════════════════════
elif section == "User Introduction":
    st.title("About")
    st.markdown("""
    **Project:** Local Food Waste Management System  
    **Built with:** Python · SQLite · Streamlit · Plotly  
    **Course:** GUVI Master Data Science Program  

    In this project i have demonstrated end-to-end data engineering — from raw CSV ingestion
    and SQL database design to an interactive Streamlit dashboard with live CRUD operations
    and analytical visualizations.
    """)