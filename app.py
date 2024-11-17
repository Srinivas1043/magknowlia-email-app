import streamlit as st
import pandas as pd
import os
import openai
import pyalex
import requests
from pyalex import Works, Authors
from io import BytesIO
from dotenv import load_dotenv
import time

# Constants for Euretos branding and configuration
PLATFORM_NAME = "Euretos AI Platform"
FEATURE_BENEFITS = {
    'search': "discover relevant research connections and patterns",
    'analytics': "gain deeper insights from research data",
    'kg': "uncover hidden relationships in scientific literature",
    'portal': "streamline your research workflow"
}

# Predefined email templates
EMAIL_TEMPLATES = {
    'initial': """I read your paper "{title}" with great interest. Your research in {research_area}, particularly your findings regarding {key_finding}, aligns well with the capabilities of the """ + PLATFORM_NAME + """. 

Our platform could enhance your research by providing advanced tools for {research_area}. Would you be interested in exploring how our platform could support your work? I'd be happy to provide you with a free account.""",

    'reminder1': """I wanted to follow up regarding your paper "{title}" and how the """ + PLATFORM_NAME + """ could support your {research_area} research.

Given your important findings about {key_finding}, I believe our platform's capabilities could be particularly valuable for your work.""",

    'reminder2': """I hope you don't mind one final follow-up regarding your research on {key_finding}. Your work in {research_area} could significantly benefit from our platform's capabilities.""",

    'search': """Based on your research in "{title}", our search capabilities could help you {feature_benefit}, which seems particularly relevant given your focus on {research_area}.""",

    'analytics': """Your work on {key_finding} could benefit from our analytics tools that help researchers {feature_benefit}. This could provide valuable insights for your {research_area} research.""",

    'kg': """Given your research on {key_finding}, our Knowledge Graph could help you {feature_benefit}. This could be particularly valuable for your work in {research_area}.""",

    'portal': """Your research in {research_area} could benefit from our Research Portal, which helps researchers {feature_benefit}. This could be especially valuable for extending your work on {key_finding}."""
}

# Initialize Streamlit app
st.set_page_config(page_title="Email Generator Tool", page_icon="📧", layout="wide")

# Load OpenAI API key
try:
    openai_api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    if not openai_api_key:
        st.error("OpenAI API key is not set. Please check your environment variables or GitHub Secrets.")
        st.stop()
    openai.api_key = openai_api_key
except Exception as e:
    st.error(f"Error initializing OpenAI client: {str(e)}")
    st.stop()

def fetch_journal_titles_from_openalex(url, size_requested):
    """Fetch data from OpenAlex API."""
    try:
        base_url = "https://api.openalex.org/works"
        all_data = []
        params = {'page': 1, 'filter': url}

        with st.spinner(f'Fetching data from OpenAlex (0/{size_requested} records)...'):
            while len(all_data) < size_requested:
                response = requests.get(base_url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data.get('results'):
                    break

                for work in data['results']:
                    if len(all_data) >= size_requested:
                        break

                    try:
                        ID = work.get('id', 'No ID')
                        abstract = Works()[ID].get('abstract', 'Abstract not available')
                        work_data = {
                            'id': ID,
                            'Title': work.get('title', 'No title available'),
                            'Journal': work.get('primary_location', {}).get('source', {}).get('display_name', 'No Journal Name'),
                            'Publication Year': work.get('publication_year', 'No Year'),
                            'Abstract': abstract,
                            'Authors': ', '.join(a['author']['display_name'] for a in work.get('authorships', []))
                        }
                        all_data.append(work_data)
                    except Exception as e:
                        st.warning(f"Error processing work {ID}: {str(e)}")
                        continue

                params['page'] += 1

        return pd.DataFrame(all_data)
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to OpenAlex API: {str(e)}")
        return None

def extract_research_context(abstract, title):
    """Extract detailed research elements using OpenAI."""
    try:
        messages = [
            {"role": "system", "content": """Extract key research elements:
            {
                "research_area": "specific field of study",
                "key_finding": "main discovery or conclusion",
                "potential_application": "how the findings could be applied",
                "suggested_platform_feature": "best Euretos feature for this research"
            }"""},
            {"role": "user", "content": f"Title: {title}\n\nAbstract: {abstract}"}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0.3
        )
        context = eval(response.choices[0].message.content)
        return context
    except Exception:
        return {
            "research_area": "your field",
            "key_finding": "your research findings",
            "potential_application": "potential use cases",
            "suggested_platform_feature": "general features"
        }

def format_email_content(template_key, context, research_context):
    """Format the email content with research context."""
    feature_type = research_context.get('suggested_platform_feature', 'enhance your research')
    template = EMAIL_TEMPLATES.get(template_key, EMAIL_TEMPLATES['initial'])

    format_context = {
        'title': context.get('title', ''),
        'authors': context.get('authors', ''),
        'research_area': research_context.get('research_area', ''),
        'key_finding': research_context.get('key_finding', ''),
        'potential_application': research_context.get('potential_application', ''),
        'feature_benefit': FEATURE_BENEFITS.get(feature_type, 'enhance your research')
    }

    return template.format(**format_context).strip()

def main():
    st.title("📧 AI-Powered Email Generator")
    euretos_file = st.file_uploader("Upload Euretos Information (Text File)", type=["txt"])
    euretos_info = read_from_file(euretos_file) if euretos_file else None

    openalex_link = st.text_input("Enter OpenAlex Filter Query")
    size_requested = st.number_input("Number of records to fetch", min_value=1, max_value=100, value=10)

    if st.button("Generate Emails"):
        data = fetch_journal_titles_from_openalex(openalex_link, size_requested)
        if data is None or data.empty:
            st.error("No data found.")
            return

        for index, row in data.iterrows():
            research_context = extract_research_context(row['Abstract'], row['Title'])
            context = {'title': row['Title'], 'authors': row['Authors']}

            for email_type in ['initial', 'reminder1', 'reminder2', 'search', 'analytics', 'kg', 'portal']:
                data.loc[index, f'{email_type}_email'] = format_email_content(email_type, context, research_context)

        st.success("Emails generated successfully!")
        st.dataframe(data)

if __name__ == "__main__":
    main()
