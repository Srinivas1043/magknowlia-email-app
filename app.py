import streamlit as st
import pandas as pd
import os
import openai
import pyalex
import requests
from pyalex import Works
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

# Set the title and description
st.set_page_config(page_title="Email Generator Tool", page_icon="📧", layout="wide")

# Initialize OpenAI client
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
    """Extract detailed research elements with an enhanced prompt for GPT-4."""
    try:
        messages = [
            {
                "role": "system",
                "content": """You are a professional assistant helping to create personalized outreach emails for researchers based on their abstracts. Extract the following details in a conversational style:
                - A brief summary of the research focus and its significance.
                - The key findings or discoveries from the research.
                - How the findings could be applied in practical scenarios or extended further.
                - A suggested feature from Euretos (e.g., Analytics, Knowledge Graph, Search) that would be most beneficial for this research.
                - An engaging and conversational sentence highlighting why the Euretos platform could be valuable for this research.
                Provide the output in a structured JSON format with the following fields:
                {
                    "research_summary": "A brief summary of the research",
                    "key_finding": "Main discovery or conclusion",
                    "potential_application": "How the findings could be applied",
                    "suggested_platform_feature": "Recommended Euretos feature",
                    "engaging_sentence": "A sentence introducing Euretos as a valuable tool for this research"
                }
                """
            },
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
            "research_summary": "A study exploring an important area of research.",
            "key_finding": "Significant findings related to the research topic.",
            "potential_application": "Potential ways the findings can be applied.",
            "suggested_platform_feature": "general features",
            "engaging_sentence": "Euretos could be a valuable resource to support your research goals."
        }

def generate_flexible_email(context, research_context):
    """Create a free-form, conversational email based on the research context."""
    try:
        title = context.get('title', 'your recent study')
        authors = context.get('authors', 'Researcher')
        research_summary = research_context.get('research_summary', 'This study focuses on an important research area.')
        key_finding = research_context.get('key_finding', 'There are notable findings in this research.')
        potential_application = research_context.get('potential_application', 'The findings have potential applications.')
        suggested_feature = research_context.get('suggested_platform_feature', 'features of the Euretos platform')
        engaging_sentence = research_context.get('engaging_sentence', 'Euretos could be a valuable addition to your research toolkit.')

        email_body = (
            f"Dear {authors},\n\n"
            f"Congratulations on your recent study, \"{title}\"! Your research on {research_summary} "
            f"is quite impressive, especially your findings regarding {key_finding}.\n\n"
            f"We believe the Euretos platform could offer valuable tools to help you further explore and apply these findings. "
            f"For instance, our {suggested_feature} could be particularly beneficial for {potential_application}. "
            f"{engaging_sentence}\n\n"
            f"I’d be happy to set up a free account for you to explore these features and see how they might support your ongoing research. "
            f"Please let me know if you’d be interested in discussing this further.\n\n"
            f"Best regards,\n[Your Name]\nEuretos AI Team"
        )

        return email_body
    except Exception as e:
        st.error(f"Error generating email content: {str(e)}")
        return "An error occurred while generating the email content."

def main():
    st.title("📧 AI-Powered Email Generator")
    euretos_file = st.file_uploader("Upload Euretos Information (Text File)", type=["txt"])
    openalex_link = st.text_input("Enter OpenAlex Filter Query")
    size_requested = st.number_input("Number of records to fetch", min_value=1, max_value=100, value=10)

    if st.button("Generate Emails"):
        data = fetch_journal_titles_from_openalex(openalex_link, size_requested)
        if data is None or len(data) == 0:
            st.error("No data found. Please check your OpenAlex query.")
            return

        progress_bar = st.progress(0)
        for index, row in data.iterrows():
            progress = (index + 1) / len(data)
            research_context = extract_research_context(row['Abstract'], row['Title'])
            context = {'title': row['Title'], 'authors': row['Authors']}
            data.loc[index, 'Personalized_Email'] = generate_flexible_email(context, research_context)
            progress_bar.progress(progress)

        progress_bar.progress(100)
        st.success("✅ All emails generated successfully!")
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')

        csv = data.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download as CSV", data=csv, file_name=f"generated_emails_{timestamp}.csv", mime="text/csv")

if __name__ == "__main__":
    main()
