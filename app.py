import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
import pyalex
import requests
from pyalex import Works, Authors
from io import BytesIO
import time

# Constants for Euretos branding
PLATFORM_NAME = "Euretos AI Platform"
PLATFORM_URL = "euretos.com"

# Set the title and description
st.set_page_config(page_title="Email Generator Tool", page_icon="📧", layout="wide")

# Initialize OpenAI client
try:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    if not openai_api_key:
        st.error("OpenAI API key is not set. Please check your environment variables or GitHub Secrets.")
        st.stop()
    client = OpenAI(api_key=openai_api_key)
except Exception as e:
    st.error(f"Error initializing OpenAI client: {str(e)}")
    st.stop()

def validate_openalex_url(url):
    """Validate if the OpenAlex URL is properly formatted"""
    if not url:
        return False
    return True

def fetch_journal_titles_from_openalex(url, size_requested):
    """Fetch data from OpenAlex with improved error handling"""
    try:
        base_url = "https://api.openalex.org/works"
        all_data = []
        params = {
            'page': 1,
            'filter': url
        }
        
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
                        try:
                            abstract = Works()[ID]['abstract'] or "No abstract available"
                        except Exception:
                            abstract = "Abstract not available"
                            
                        work_data = {
                            'id': ID,
                            'Title': work.get('title', 'No title available'),
                            'Journal': work.get('primary_location', {}).get('source', {}).get('display_name', 'No Journal Name'),
                            'Publication Year': work.get('publication_year', 'No Year'),
                            'Publication Date': work.get('publication_date', 'No Date'),
                            'Abstract': abstract,
                            'Authors': ', '.join(a['author']['display_name'] for a in work.get('authorships', [])),
                            'Author IDs': ', '.join(a['author']['id'] for a in work.get('authorships', [])),
                            'Affiliations': ', '.join(
                                a.get('institutions', [{}])[0].get('display_name', 'No Affiliation')
                                if a.get('institutions') else 'No Affiliation'
                                for a in work.get('authorships', [])
                            )
                        }
                        all_data.append(work_data)
                        st.spinner(f'Fetching data from OpenAlex ({len(all_data)}/{size_requested} records)...')
                    except Exception as e:
                        st.warning(f"Error processing work {ID}: {str(e)}")
                        continue
                
                params['page'] += 1
                
        return pd.DataFrame(all_data)
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to OpenAlex API: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

def read_from_file(uploaded_file):
    """Read content from uploaded file with error handling"""
    try:
        content = uploaded_file.read().decode("utf-8")
        return content.strip()
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None

def extract_research_context(abstract):
    """Extract key research elements from abstract"""
    try:
        messages = [
            {
                "role": "system",
                "content": """Extract key research elements in JSON format:
                {
                    "research_area": "main field of study",
                    "key_finding": "main discovery or conclusion",
                    "methodology": "key methods used",
                    "implications": "potential impact"
                }"""
            },
            {"role": "user", "content": abstract}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.3
        )
        
        return eval(response.choices[0].message.content)
    except Exception:
        return {
            "research_area": "the field",
            "key_finding": "your findings",
            "methodology": "the methods",
            "implications": "the implications"
        }

def generate_contextual_email(paper_info, email_type, euretos_info, previous_email=None):
    """Generate contextually relevant emails"""
    title = paper_info['Title']
    abstract = paper_info['Abstract']
    research_context = extract_research_context(abstract)
    
    email_prompts = {
        'initial': f"""
        Create a professional email about the {PLATFORM_NAME} that:
        1. References specific findings from their paper "{title}" about {research_context['key_finding']}
        2. Connects our platform's capabilities to their {research_context['research_area']} research
        3. Mentions how our platform could enhance their specific research methodology
        4. Uses "in your paper" or "in your research" (never "in the abstract")
        5. Offers concrete value proposition based on their work
        
        Their research abstract:
        {abstract}
        
        Platform information:
        {euretos_info}
        """,
        
        'reminder': f"""
        Write a follow-up email that:
        1. References their paper "{title}" and previous communication
        2. Maintains specific context about their research on {research_context['key_finding']}
        3. Adds new value proposition related to their {research_context['research_area']} work
        4. Is concise and professional
        
        Previous email:
        {previous_email}
        
        Research context:
        {abstract}
        """,
        
        'feature': f"""
        Write an email about {PLATFORM_NAME} features that:
        1. Connects our capabilities to their work on {research_context['key_finding']}
        2. Shows how our platform could enhance their {research_context['methodology']}
        3. Explains specific benefits for their research direction
        4. References concrete findings from their paper
        
        Their research:
        {abstract}
        
        Feature information:
        {euretos_info}
        """
    }
    
    try:
        messages = [
            {
                "role": "system",
                "content": f"""You are writing professional emails about the {PLATFORM_NAME}. 
                Maintain consistent branding and specific relevance to the researcher's work.
                Always reference their specific research findings and methodology.
                Use 'in your paper' or 'in your research' instead of 'in the abstract'.
                Be concrete and avoid generic statements."""
            },
            {"role": "user", "content": email_prompts.get(email_type, email_prompts['initial'])}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        
        email_content = response.choices[0].message.content.strip()
        
        # Post-processing
        replacements = {
            "in the abstract": "in your paper",
            "Euretos.com": PLATFORM_NAME,
            "...": ".",
            "!.": "!",
            "  ": " ",
            "etc.": "and similar applications",
            "e.g.,": "such as"
        }
        
        for old, new in replacements.items():
            email_content = email_content.replace(old, new)
        
        return email_content
        
    except Exception as e:
        st.error(f"Error generating email: {str(e)}")
        return "Error generating email content."

def main():
    st.title("📧 AI-Powered Email Generator")
    st.markdown(f"Generate personalized emails based on research papers and {PLATFORM_NAME} features.")

    # File upload with validation
    euretos_file = st.file_uploader("Upload Euretos Information (Text File)", type=["txt"])
    euretos_information = None
    if euretos_file:
        euretos_information = read_from_file(euretos_file)
        if euretos_information:
            st.success(f"✅ {PLATFORM_NAME} Information Uploaded Successfully")

    # Input validation
    openalex_link = st.text_input("Enter OpenAlex Filter Query")
    size_requested = st.number_input("Number of records to fetch", min_value=1, max_value=100, value=10)

    if not all([openalex_link, euretos_information]):
        st.warning(f"Please provide both OpenAlex query and {PLATFORM_NAME} information to proceed.")
        return

    if st.button("Generate Emails", type="primary"):
        if not validate_openalex_url(openalex_link):
            st.error("Invalid OpenAlex query format. Please check your input.")
            return

        data = fetch_journal_titles_from_openalex(openalex_link, size_requested)
        if data is None or len(data) == 0:
            st.error("No data found. Please check your OpenAlex query.")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Generate emails with progress tracking
        email_columns = ['Mail_1', 'Reminder_1', 'Reminder_2', 'Search_mail', 
                        'Analytics_mail', 'KG_mail', 'Portal_mail']
        
        for index, row in data.iterrows():
            progress = (index + 1) / len(data)
            status_text.text(f"Generating emails for paper {index + 1} of {len(data)}...")
            
            # Generate initial email
            data.loc[index, 'Mail_1'] = generate_contextual_email(
                row, 'initial', euretos_information
            )
            
            # Generate reminder emails
            data.loc[index, 'Reminder_1'] = generate_contextual_email(
                row, 'reminder', euretos_information, data.loc[index, 'Mail_1']
            )
            data.loc[index, 'Reminder_2'] = generate_contextual_email(
                row, 'reminder', euretos_information, data.loc[index, 'Reminder_1']
            )
            
            # Generate feature-specific emails
            for feature, col in zip(['search', 'analytics', 'kg', 'portal'], 
                                  ['Search_mail', 'Analytics_mail', 'KG_mail', 'Portal_mail']):
                data.loc[index, col] = generate_contextual_email(
                    row, 'feature', euretos_information
                )
            
            progress_bar.progress(progress)

        progress_bar.progress(100)
        status_text.text("Email generation complete! ✨")

        # Process results
        df_split = (data.assign(Author=data['Authors'].str.split(','),
                              AuthorID=data['Author IDs'].str.split(','))
                   .explode(['Author', 'AuthorID'])
                   .reset_index(drop=True))
        
        df_split.drop(['Authors', 'Author IDs'], axis=1, inplace=True)

        # Export options
        st.success("✅ All emails generated successfully!")
        timestamp = pd.Timestamp.now().strftime('%Y-%m-%d_%H-%M-%S')
        
        col1, col2 = st.columns(2)
        with col1:
            csv = df_split.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"generated_emails_{timestamp}.csv",
                mime="text/csv"
            )
        
        with col2:
            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_split.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Download as Excel",
                data=buffer.getvalue(),
                file_name=f"generated_emails_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
