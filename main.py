import streamlit as st
from langchain_groq import ChatGroq
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from sqlalchemy import create_engine, text
import pandas as pd
import base64
import os
import pymysql
from dotenv import load_dotenv

# --- Load Environment Variables ---
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

st.set_page_config(
    page_title="QueryLab",
    page_icon="img/Logo.png",
)

# --- Load Font ---
def load_font(font_path):
    with open(font_path, "rb") as f:
        font_data = base64.b64encode(f.read()).decode()
    return font_data

font_data = load_font("fonts/LUFGABOLD.TTF")

# --- Load Images ---
with open("img/logo(1).png", "rb") as f:
    logo_data = base64.b64encode(f.read()).decode()

with open("img/setting.png", "rb") as f:
    settings_icon = base64.b64encode(f.read()).decode()

# --- Styling ---
st.markdown(f"""
    <style>
    @font-face {{
        font-family: 'Lufga';
        src: url(data:font/truetype;base64,{font_data}) format('truetype');
        font-weight: bold;
    }}

    html, body, [class*="css"], [class*="st-"], .stApp,
    .stApp p, .stApp div, .stApp label,
    .stApp input, .stApp textarea, .stApp button,
    [data-testid="stSidebar"] * {{
        font-family: 'Lufga', sans-serif !important;
    }}

    .stApp p span, .stMarkdown span {{
        font-family: 'Lufga', sans-serif !important;
    }}

    /* Hide broken expander icons */
    [data-testid="stExpander"] details summary span:first-child {{
        font-size: 0 !important;
    }}
    [data-testid="stExpander"] details summary span:first-child::after {{
        content: '▶';
        font-size: 14px !important;
        font-family: 'Lufga', sans-serif !important;
    }}

    /* Hide broken sidebar collapse button */
    [data-testid="stSidebarCollapseButton"] {{
        display: none !important;
    }}

    /* Primary buttons - dark grey */
    .stButton > button[kind="primary"] {{
        background-color: #2d2d2d !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 980px !important;
        padding: 12px 28px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
        width: 100% !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background-color: #1a1a1a !important;
    }}

    [data-testid="stSidebar"] .stVerticalBlock {{
        padding-top: 0px !important;
        margin-top: -50px !important;
    }}
    </style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown(f"""
    <div style='display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 20px;'>
        <img src='data:image/png;base64,{logo_data}' width='125' style='border-radius: 12px;'/>
        <h1 style='font-size: 64px; font-weight: 700; color: #1d1d1f; letter-spacing: -2px; font-family: Lufga, sans-serif; margin: 0;'>QueryLab</h1>
    </div>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.markdown(f"""
    <div style='display: flex; align-items: center; gap: 10px;'>
        <img src='data:image/png;base64,{settings_icon}' width='24'/>
        <h2 style='text-decoration: underline; margin: 0; font-family: Lufga, sans-serif;'>Configuration</h2>
    </div>
""", unsafe_allow_html=True)

with st.sidebar:
    db_host = st.text_input("Host:", value="localhost")
    db_port = st.text_input("Port:", value="3306")
    db_user = st.text_input("Username:", value="root")
    db_password = st.text_input("Password:", type="password")
    db_name = st.text_input("Database Name:", value="classicmodels")
    connect_button = st.button("Connect")

# --- Main Area ---
if connect_button:
    if not all([db_host, db_port, db_user, db_password, db_name]):
        st.error("⚠️ Please fill in all database configuration fields!")
    else:
        try:
            connection_string = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

            with st.spinner("Connecting to database"):
                db = SQLDatabase.from_uri(connection_string)
                st.session_state['db'] = db
                st.session_state['connection_string'] = connection_string
                st.session_state['db_host'] = db_host
                st.session_state['db_port'] = db_port
                st.session_state['db_user'] = db_user
                st.session_state['db_password'] = db_password
                st.session_state['db_name'] = db_name

            st.success("Successfully connected.")
            tables = db.get_usable_table_names()
            st.info(f"Available tables: {', '.join(tables) if tables else 'No tables found'}")

        except Exception as e:
            st.error(f"Connection failed: {str(e)}")

# --- Query Interface ---
if 'db' in st.session_state:
    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        groq_api_key=GROQ_API_KEY,
        temperature=0
    )

    agent_executor = create_sql_agent(
        llm=llm,
        db=st.session_state['db'],
        agent_type="openai-tools",
        verbose=True
    )

    user_query = st.text_area("", height=100)

    col1, col2, col3 = st.columns([2, 1, 2])
    with col2:
        execute_button = st.button("Execute", type="primary")

    if execute_button and user_query:
        with st.spinner("Querying.."):
            try:
                response = agent_executor.invoke({"input": user_query})
                st.success("Executed Successfully!")
                st.write("**Answer:**")
                st.write(response["output"])
            except Exception as e:
                st.error(f"Error: {str(e)}")

    # --- Database Explorer ---
    with st.expander("Database Explorer"):
        tables = st.session_state['db'].get_usable_table_names()
        if tables:
            selected_table = st.selectbox("Select a table to preview:", tables)
            if st.button("Show Table Data"):
                try:
                    conn = pymysql.connect(
                        host=st.session_state['db_host'],
                        port=int(st.session_state['db_port']),
                        user=st.session_state['db_user'],
                        password=st.session_state['db_password'],
                        database=st.session_state['db_name'],
                        autocommit=True
                    )
                    df = pd.read_sql(f"SELECT * FROM {selected_table} LIMIT 100", conn)
                    conn.close()
                    st.dataframe(df, use_container_width=True)
                    st.caption(f"Showing up to 100 rows from {selected_table}")
                except Exception as e:
                    st.error(f"Error fetching data: {str(e)}")
        else:
            st.warning("No tables found in the database.")

    # --- Schema Information ---
    with st.expander("Database Schema"):
        if st.button("Get Schema Info"):
            try:
                schema_info = st.session_state['db'].get_table_info()
                st.code(schema_info, language="sql")
            except Exception as e:
                st.error(f"Error getting schema: {str(e)}")

    # --- Database Editor ---
    with st.expander("Database Editor"):
        st.warning("⚠️ Be careful - changes are permanent!")
        tables = st.session_state['db'].get_usable_table_names()
        selected_table = st.selectbox("Select a table to edit:", tables, key="edit_table")

        if selected_table:
            try:
                conn = pymysql.connect(
                    host=st.session_state['db_host'],
                    port=int(st.session_state['db_port']),
                    user=st.session_state['db_user'],
                    password=st.session_state['db_password'],
                    database=st.session_state['db_name'],
                    autocommit=True
                )
                df = pd.read_sql(f"SELECT * FROM {selected_table} LIMIT 100", conn)
                conn.close()

                st.caption(f"Editing: {selected_table} (showing up to 100 rows)")

                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="data_editor"
                )

                # Store edited df and table name in session state
                st.session_state['edited_df'] = edited_df
                st.session_state['edit_table_name'] = selected_table

                # Step 1: Save Changes button
                if st.button("Save Changes", type="primary"):
                    st.session_state['confirm_save'] = True

                # Step 2: Confirmation dialog
                if st.session_state.get('confirm_save'):
                    st.warning("Are you sure you want to save these changes? This will overwrite the existing data.")
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("Yes, Save", type="primary"):
                            try:
                                conn = pymysql.connect(
                                    host=st.session_state['db_host'],
                                    port=int(st.session_state['db_port']),
                                    user=st.session_state['db_user'],
                                    password=st.session_state['db_password'],
                                    database=st.session_state['db_name'],
                                    autocommit=True
                                )
                                cursor = conn.cursor()
                                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                                cursor.execute(f"DELETE FROM {st.session_state['edit_table_name']}")

                                save_df = st.session_state['edited_df']
                                for _, row in save_df.iterrows():
                                    cols = ', '.join(save_df.columns)
                                    placeholders = ', '.join(['%s'] * len(save_df.columns))
                                    values = tuple(row)
                                    cursor.execute(
                                        f"INSERT INTO {st.session_state['edit_table_name']} ({cols}) VALUES ({placeholders})",
                                        values
                                    )

                                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
                                cursor.close()
                                conn.close()
                                st.session_state['confirm_save'] = False
                                st.success("Changes saved successfully!")
                                st.rerun()

                            except Exception as e:
                                st.error(f"Error saving: {str(e)}")
                                st.code(str(e))

                    with col2:
                        if st.button("Cancel"):
                            st.session_state['confirm_save'] = False
                            st.rerun()

            except Exception as e:
                st.error(f"Error loading table: {str(e)}")

else:
    st.markdown(f"""
        <div style='display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 40vh;'>
            <p style='color: #6e6e73; font-size: 18px; margin-bottom: 16px; font-family: Lufga, sans-serif;'>
                Query and Edit your Database at Ease.
            </p>
            <div style='background-color: #dbeafe; border-radius: 10px; padding: 16px; text-align: center; width: 60%;'>
                <p style='color: #1e40af; font-size: 16px; margin: 0; font-family: Lufga, sans-serif;'>
                    Please configure and connect to your database using the sidebar.
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)