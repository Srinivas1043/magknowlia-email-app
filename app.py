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
    # Add your URL validation logic here
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
                        # Fetch abstract with error handling
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

def generate_email(prompt, retries=3):
    """Generate email content using OpenAI with retry mechanism"""
    for attempt in range(retries):
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an email assistant for creating professional email body content. 
                    Generate a concise, engaging paragraph related to the abstract and information provided. 
                    Focus on the author's work and maintain a professional tone. 
                    Do not include greetings or closings."""
                },
                {"role": "user", "content": prompt}
            ]
            
            response = client.chat.completions.create(
                model="gpt-4",  # Corrected model name
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            if attempt == retries - 1:
                st.error(f"Failed to generate email after {retries} attempts: {str(e)}")
                return "Error generating email content."
            time.sleep(1)  # Wait before retrying

def main():
    st.title("📧 AI-Powered Email Generator")
    st.markdown("Generate personalized emails based on research abstracts and Euretos data.")

    # File upload with validation
    euretos_file = st.file_uploader("Upload Euretos Information (Text File)", type=["txt"])
    euretos_information = None
    if euretos_file:
        euretos_information = read_from_file(euretos_file)
        if euretos_information:
            st.success("✅ Euretos Information Uploaded Successfully")

    # Input validation
    openalex_link = st.text_input("Enter OpenAlex Filter Query")
    size_requested = st.number_input("Number of records to fetch", min_value=1, max_value=100, value=10)

    # Prompt inputs with clear labels
    with st.expander("Email Templates"):
        prompts = {
            'initial': st.text_area("Initial Email Template", 
                                  "Based on your paper titled '{title}', I wanted to discuss {abstract}..."),
            'reminder1': st.text_area("First Reminder Template"),
            'reminder2': st.text_area("Second Reminder Template"),
            'search': st.text_area("Search Feature Email Template"),
            'analytics': st.text_area("Analytics Feature Email Template"),
            'kg': st.text_area("Knowledge Graph Email Template"),
            'portal': st.text_area("Portal Feature Email Template")
        }

    if not all([openalex_link, euretos_information]):
        st.warning("Please provide both OpenAlex query and Euretos information to proceed.")
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
            
            # Format prompts with actual data
            context = {
                'title': row['Title'],
                'abstract': row['Abstract'],
                'authors': row['Authors'],
                'euretos': euretos_information
            }
            
            # Generate each type of email
            for col, prompt_key in zip(email_columns, prompts.keys()):
                if prompts[prompt_key]:  # Only generate if prompt template is provided
                    formatted_prompt = prompts[prompt_key].format(**context)
                    data.loc[index, col] = generate_email(formatted_prompt)
            
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