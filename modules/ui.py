import streamlit as st


def hide_ft_style():
    hide_ft_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """
    st.markdown(hide_ft_style, unsafe_allow_html=True)

