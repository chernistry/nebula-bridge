#!/usr/bin/env python3
import os
import datetime
import pandas as pd
import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv
import streamlit as st


load_dotenv()

# Environment variables for authentication and backend URL
VALID_USERNAME: str = os.getenv('USERNAME')
VALID_PASSWORD: str = os.getenv('PASSWORD')
BACKEND_URL: str = os.getenv('BACKEND_URL', 'http://localhost:8000')


def authenticate(username: str, password: str) -> bool:
    """
    Validates the provided credentials against stored values.

    Args:
        username (str): The input username.
        password (str): The input password.

    Returns:
        bool: True if both username and password match the valid credentials,
              otherwise False.
    """
    return username == VALID_USERNAME and password == VALID_PASSWORD





def show_login() -> None:
    """
    Renders the login interface and handles user authentication.

    Displays a Streamlit form for user credentials. On successful login,
    updates the session state and refreshes the page.
    """
    st.title('🔐 Login')
    st.write('Please enter your credentials to continue.')

    username: str = st.text_input('Username')
    password: str = st.text_input('Password', type='password')

    if st.button('Login'):
        if authenticate(username, password):
            st.session_state['logged_in'] = True
            st.session_state['login_time'] = datetime.datetime.now().isoformat()
            st.success('Logged in successfully!')
            try:
                st.experimental_rerun()
            except AttributeError:
                st.stop()
        else:
            st.error('Invalid username or password.')





def show_main_app() -> None:
    """
    Displays the main application interface post-authentication.

    Provides interactive sections for ETL operations, character search,
    team salary calculations, OData retrieval, downloading collections, and
    exporting session logs. Also includes a logout option.
    """
    st.title('✨ Streamlit Authenticated App')
    st.write('Welcome! You are successfully logged in.')

    # ==== ETL Section ====
    st.header('1) Run ETL')
    if st.button('Run ETL (Production)'):
        endpoint: str = f"{BACKEND_URL}/run-etl?use_wookiee=false"
        try:
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            st.success('ETL Completed!')
            st.json(response.json())
        except RequestException as ex:
            st.error(f"Failed to run ETL: {ex}")



    # ==== Character Search Section ====
    st.header('2) Search Characters (Grievous)')
    if st.button('Search Characters'):
        endpoint: str = f"{BACKEND_URL}/search-characters-prod?query=Grievous"
        try:
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            st.write("🔍 Raw API Response:", response.text)
            st.write("🔍 Headers:", response.headers)
            try:
                data = response.json()
            except ValueError as e:
                st.error(f"JSON Decoding Error: {e}")
                st.stop()
            if 'characters' in data:
                st.success('Characters found:')
                st.json(data['characters'])
            else:
                st.warning(data.get('message', 'No valid characters found.'))
        except RequestException as ex:
            st.error(f"Failed to search characters: {ex}")



    # ==== Team Salary Calculation Section ====
    st.header('3) Calculate Team Salary')
    if st.button('Calculate Team Salary'):
        endpoint: str = f"{BACKEND_URL}/calculate-team-salary"
        try:
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            salaries = response.json().get('team_salaries', [])
            if salaries:
                st.success('Team salaries retrieved:')
                st.dataframe(pd.DataFrame(salaries))
            else:
                st.info('No salary data returned.')
        except RequestException as ex:
            st.error(f"Failed to calculate team salary: {ex}")



    # ==== OData: Longest Flight Section ====
    st.header('4) OData: Longest Flight')
    use_mock: bool = st.checkbox('Use Mock Data?', value=False)
    if st.button('Get Longest Flight'):
        endpoint: str = f"{BACKEND_URL}/odata-longest-flight?use_mock={str(use_mock).lower()}"
        try:
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            st.success('Longest flight details:')
            st.json(response.json())
        except RequestException as ex:
            st.error(f"Failed to get OData info: {ex}")



    # ==== Postman Collection Download Section ====
    st.header('Download Postman Collection')
    if st.button('Generate & Download Collection'):
        endpoint: str = f"{BACKEND_URL}/generate-postman"
        try:
            response = requests.get(endpoint, timeout=30)
            response.raise_for_status()
            st.download_button(
                label='Download Postman Collection',
                data=response.text,
                file_name='Taboola_Task.postman_collection.json',
                mime='application/json'
            )
        except RequestException as ex:
            st.error(f"Failed to download Postman collection: {ex}")



    # ==== Session Log Export Section ====
    st.header('Export Session Info')
    if st.button('Export Session Log'):
        log_data = {
            'User': [VALID_USERNAME],
            'LoginTime': [st.session_state.get('login_time')],
            'ExportTime': [datetime.datetime.now().isoformat()]
        }
        st.download_button(
            label='Download Session Log CSV',
            data=pd.DataFrame(log_data).to_csv(index=False),
            file_name='session_log.csv',
            mime='text/csv'
        )



    # ==== Logout Section ====
    if st.button('Logout'):
        st.session_state['logged_in'] = False
        try:
            st.experimental_rerun()
        except AttributeError:
            st.stop()





def main() -> None:
    """
    Determines the application flow based on the user's authentication state.

    Initializes the session state for authentication if not already set and
    renders either the login page or the main application interface.
    """
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        show_login()
    else:
        show_main_app()





if __name__ == '__main__':
    main()
