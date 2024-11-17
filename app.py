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
PLATFORM_NAME = "Euretos"
PLATFORM_DESCRIPTION = {
    'general': "a platform designed to accelerate molecular research through advanced data integration and analytics",
    'search': "advanced search functionality, designed to help you quickly locate relevant molecular and biomedical data",
    'analytics': "powerful tools to help researchers analyze molecular data, visualize disease pathways, and identify potential biomarkers and drug targets",
    'kg': "designed to help you visualize complex molecular interactions, disease pathways, and genetic relationships",
    'portal': "a centralized research hub, enabling easy access to powerful tools for data analysis, knowledge exploration, and research management"
}

# Enhanced email templates matching the example format
EMAIL_TEMPLATES = {
    'initial': """Congratulations on your recent study, "{title}"! Your findings on {key_finding} are not only impressive but also significant for advancing {research_area}.

We'd like to introduce you to {platform_name}, {platform_description}. {platform_name} offers tools specifically tailored for {potential_applications}—all features that could extend and enhance your ongoing work on {research_focus}.

With {platform_name}, you can {specific_benefit}. We'd be delighted to offer you a free account to trial the platform and see how it might support your {research_area} research further.""",

    'reminder1': """Just a quick follow-up on our previous email about {platform_name} and its potential to support your {research_area} research. Given your recent work on {key_finding}, we believe the platform could offer valuable insights and tools for {potential_applications}.

Feel free to reach out if you'd like to discuss this further or take advantage of a free trial account to explore {platform_name} for yourself!""",

    'reminder2': """We know how busy you must be, so we'll keep this brief. We previously reached out about {platform_name}, a platform that could add valuable dimensions to your {research_area} research by allowing deeper exploration of {potential_applications} relevant to your recent findings on {key_finding}.

Apologies if this email is a little intrusive—we just didn't want you to miss out on the opportunity to test {platform_name} through a free account. If you have a moment to explore, we'd love to support your next steps in {research_area} research.""",

    'search': """If you're looking to enhance your {research_area} research, our {platform_name} platform could be a valuable resource. {platform_name} offers {platform_description}. With the ability to search for specific {search_focus}, {platform_name} enables researchers to retrieve detailed, structured insights that could complement your work on {key_finding}.

Feel free to explore {platform_name}'s search capabilities with a free account. We believe it could significantly support your {research_area} study by giving you easy access to data that could propel your research further.""",

    'analytics': """In your work on {research_focus} like {key_finding}, the ability to perform in-depth data analysis is crucial. {platform_name} Analytics provides {platform_description}. With {platform_name}, you can access structured analytics specifically designed for advanced research needs, allowing for a more comprehensive investigation into complex biological data.

If you'd like to experience the benefits of {platform_name} Analytics in your {research_area} research, we'd be happy to set you up with a free account to try it out.""",

    'kg': """In {research_area} research, understanding the broader molecular context can make all the difference. The {platform_name} Knowledge Graph is {platform_description}. For a study like yours, focused on {research_focus}, the Knowledge Graph could enable a more holistic approach to investigating {potential_applications}.

With a free trial, you can explore how the {platform_name} Knowledge Graph might enrich your research on {research_area}. We'd be delighted to support your exploration of these tools.""",

    'portal': """For {research_area} researchers like yourself, keeping all relevant data and tools accessible in one place can streamline workflows. The {platform_name} Portal offers {platform_description}. Designed to simplify complex research, the portal could serve as a valuable resource as you continue exploring {research_focus} like {key_finding}.

If you're interested, we'd be happy to provide you with a free trial account to experience how the {platform_name} Portal can support your ongoing {research_area} research."""
}

def extract_research_context(abstract, title):
    """Extract deeper research elements with enhanced prompt for GPT."""
    try:
        messages = [
            {
                "role": "system",
                "content": """You are an expert in analyzing scientific research papers. Extract detailed elements of the research paper, focusing on molecular and biomedical aspects. Provide output in the following JSON format:
                {
                    "research_area": "specific field of study (e.g., Alzheimer's research, cancer research)",
                    "key_finding": "main discovery or biomarker/molecular finding",
                    "research_focus": "specific focus area (e.g., biomarkers, molecular pathways)",
                    "potential_applications": "specific ways the research could be extended using molecular analysis",
                    "search_focus": "specific entities that researchers might want to search for",
                    "specific_benefit": "concrete benefit of using the platform for this research"
                }
                
                Be specific and technical in your extraction, focusing on molecular and biomedical aspects that would be relevant for a data analytics platform."""
            },
            {"role": "user", "content": f"Title: {title}\n\nAbstract: {abstract}"}
        ]
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.25
        )
        context = eval(response.choices[0].message.content)
        return context
    except Exception as e:
        st.error(f"Error in context extraction: {str(e)}")
        return {
            "research_area": "molecular research",
            "key_finding": "your recent findings",
            "research_focus": "molecular mechanisms",
            "potential_applications": "investigating molecular interactions and pathways",
            "search_focus": "interactions, pathways, and molecular entities",
            "specific_benefit": "explore molecular interactions and pathways relevant to your research"
        }

def format_email_content(template_key, paper_context, research_context):
    """Format email content with enhanced context."""
    template = EMAIL_TEMPLATES.get(template_key, EMAIL_TEMPLATES['initial'])
    
    format_context = {
        'platform_name': PLATFORM_NAME,
        'platform_description': PLATFORM_DESCRIPTION.get(template_key, PLATFORM_DESCRIPTION['general']),
        'title': paper_context.get('title', ''),
        'authors': paper_context.get('authors', ''),
        'research_area': research_context.get('research_area', ''),
        'key_finding': research_context.get('key_finding', ''),
        'research_focus': research_context.get('research_focus', ''),
        'potential_applications': research_context.get('potential_applications', ''),
        'search_focus': research_context.get('search_focus', ''),
        'specific_benefit': research_context.get('specific_benefit', '')
    }
    
    return template.format(**format_context)
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