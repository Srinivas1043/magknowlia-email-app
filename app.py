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
from collections import defaultdict

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
    return bool(url and url.strip())

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

def extract_research_context(abstract, title):
    """Extract key research elements using GPT-4"""
    try:
        messages = [
            {
                "role": "system",
                "content": """Extract key research elements in JSON format:
                {
                    "research_area": "specific field of study",
                    "key_finding": "main discovery or conclusion",
                    "methodology": "key methods used",
                    "impact": "potential applications or implications"
                }"""
            },
            {"role": "user", "content": f"Title: {title}\n\nAbstract: {abstract}"}
        ]
        
        response = client.chat.completions.create(
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
            "methodology": "your research methods",
            "impact": "potential implications"
        }

def format_email_content(template_key, context, research_context, feature_type=None):
    """Format email content with proper context and post-processing"""
    try:
        # Get template from predefined templates
        template = EMAIL_TEMPLATES[template_key]
        
        # Combine all context
        format_context = {
            'title': context.get('title', ''),
            'authors': context.get('authors', ''),
            'research_area': research_context.get('research_area', ''),
            'key_finding': research_context.get('key_finding', ''),
            'methodology': research_context.get('methodology', ''),
            'impact': research_context.get('impact', ''),
            'feature_benefit': FEATURE_BENEFITS.get(feature_type, 'enhance your research')
        }
        
        # Format template
        email = template.format(**format_context)
        
        # Post-processing
        email = (email
                .replace("in the abstract", "in your paper")
                .replace("euretos.com", PLATFORM_NAME)
                .replace("...", ".")
                .replace("!.", "!")
                .strip())
        
        return email
    except Exception as e:
        st.error(f"Error formatting email: {str(e)}")
        return "Error generating email content."

def read_from_file(uploaded_file):
    """Read content from uploaded file with error handling"""
    try:
        content = uploaded_file.read().decode("utf-8")
        return content.strip()
    except Exception as e:
        st.error(f"Error reading file: {str(e)}")
        return None

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

    # Optional template preview
    if st.checkbox("Preview Email Templates"):
        with st.expander("Email Templates"):
            for template_name, template_content in EMAIL_TEMPLATES.items():
                st.subheader(template_name.title())
                st.text_area(
                    f"{template_name} template",
                    value=template_content,
                    height=150,
                    disabled=True
                )

    if not all([openalex_link, euretos_information]):
        st.warning(f"Please provide both OpenAlex query and {PLATFORM_NAME} information to proceed.")
        return

    if st.button("Generate Emails", type="primary"):
        data = fetch_journal_titles_from_openalex(openalex_link, size_requested)
        if data is None or len(data) == 0:
            st.error("No data found. Please check your OpenAlex query.")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        # Generate emails with progress tracking
        for index, row in data.iterrows():
            progress = (index + 1) / len(data)
            status_text.text(f"Generating emails for paper {index + 1} of {len(data)}...")
            
            # Extract research context
            research_context = extract_research_context(row['Abstract'], row['Title'])
            
            # Generate each type of email
            context = {
                'title': row['Title'],
                'authors': row['Authors'],
                'abstract': row['Abstract']
            }
            
            # Initial and reminder emails
            data.loc[index, 'Mail_1'] = format_email_content(
                'initial', context, research_context
            )
            data.loc[index, 'Reminder_1'] = format_email_content(
                'reminder1', context, research_context
            )
            data.loc[index, 'Reminder_2'] = format_email_content(
                'reminder2', context, research_context
            )
            
            # Feature-specific emails
            data.loc[index, 'Search_mail'] = format_email_content(
                'search', context, research_context, 'search'
            )
            data.loc[index, 'Analytics_mail'] = format_email_content(
                'analytics', context, research_context, 'analytics'
            )
            data.loc[index, 'KG_mail'] = format_email_content(
                'kg', context, research_context, 'kg'
            )
            data.loc[index, 'Portal_mail'] = format_email_content(
                'portal', context, research_context, 'portal'
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