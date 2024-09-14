import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
import pyalex
import requests
from pyalex import Works, Authors, Sources, Institutions, Topics, Publishers, Funders

# set openai api key
os.environ['OPENAI_API_KEY'] = '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'
# Load environment variables from .env file
load_dotenv()
openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# Initialize OpenAI API
# openai_api_key = os.getenv('OPEN_AI_KEY')
# openai.api_key = openai_api_key


# Function to fetch journal titles and other details from OpenAlex API
def fetch_journal_titles_from_openalex(url, size_requested):
    base_url = "https://api.openalex.org/works"
    all_data = []  # Initialize an empty list to store each row of data
    params = {
        'page': 1,
        'filter': url  # Adjust this to filter based on the OpenAlex link
    }

    while len(all_data) < size_requested:
        response = requests.get(base_url, params=params)
        if response.status_code != 200:
            st.error("Error fetching data from OpenAlex API.")
            return None

        data = response.json()
        if not data['results']:
            break

        # Process each work in the results
        for work in data['results']:
            if len(all_data) >= size_requested:
                break

            ID = work.get('id', 'No ID')
            title = work.get('title', 'No title available')
            journal_name = work.get('primary_location', {}).get('source', {}).get('display_name', 'No Journal Name')
            publication_year = work.get('publication_year', 'No Year')
            publication_date = work.get('publication_date', 'No Date')

            abstract = Works()[ID]['abstract']
            authors = ', '.join([authorship['author']['display_name'] for authorship in work.get('authorships', [])])
            author_ids = ', '.join([authorship['author']['id'] for authorship in work.get('authorships', [])])
            affiliations = ', '.join([
                authorship.get('institutions', [{}])[0].get('display_name', 'No Affiliation') 
                if authorship.get('institutions') else 'No Affiliation' 
                for authorship in work.get('authorships', [])
            ])

            all_data.append({
                'id': ID,
                'Title': title,
                'Journal': journal_name,
                'Publication Year': publication_year,
                'Publication Date': publication_date,
                'Abstract': abstract,
                'Authors': authors,
                'Author IDs': author_ids,
                'Affiliations': affiliations
            })

        params['page'] += 1

    return pd.DataFrame(all_data)

# Function to read content from a text file
def read_from_file(uploaded_file):
    try:
        content = uploaded_file.read().decode("utf-8")
        return content
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return None

# Function to generate email content using OpenAI GPT
def generate_email(prompt):
    messages = [{"role" : "system", "content":"You are a message assistant. Please generate only the body of the email based on publishing industry requirements."}
                ,{"role" : "user", "content":prompt}]

    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # Choose the desired model
        messages=messages
    )
    email = response.choices[0].message.content
    return email

# Streamlit app
def main():
    st.title("Email Generator App")

    # File upload for text information (e.g., Euretos information)
    euretos_file = st.file_uploader("Upload Euretos Information (Text File)", type=["txt"])
    euretos_information = None
    if euretos_file is not None:
        euretos_information = read_from_file(euretos_file)
        st.write("Euretos Information Uploaded Successfully")
        st.write(euretos_information)

    # Input OpenAlex Link
    openalex_link = st.text_input("Enter OpenAlex Filtered link")
    # Input for the size of data to be fetched
    size_requested = st.number_input("Enter number of records to fetch", min_value=1, value=10, step=1)
    if openalex_link and size_requested:
        st.write(f"Fetching {size_requested} records from OpenAlex...")
        fetched_data = fetch_journal_titles_from_openalex(openalex_link, size_requested)
        if fetched_data is not None:
            st.write("Data fetched successfully!")
            st.write(fetched_data)
            euretos_information = euretos_information
            
        # Generate emails based on the abstracts and euretos information
            if euretos_information is not None:
                if st.button("Generate Emails"):
                    st.write("Generating emails...")

                # Loop through each abstract and generate multiple emails
                    for index, row in fetched_data.iterrows():
                        abstract = row['Abstract']
                        authors = row['Authors']

                    # First mail prompt
                        # First mail prompt
                        prompt_mail_1 = prompt_mail_1 = f"""
                        Below are two pieces of text. The first is the abstract of an article written by {authors}. 
                        The second is the capabilities of Euretos in aiding their research. 

                        Please generate only the core content of the body of an email without any salutations or subject,
                        with the following structure:

                        1. Abstract Information - Understanding - Summary: 
                        Summarize the abstract information provided below, highlighting the key points and relevance of the research.

                        Abstract:
                        {abstract}

                        2. Company Information + Abstract Information - How Euretos Helps the Research:
                        Explain how Euretos can specifically help in advancing the research, drawing on the details provided below. 
                        Focus on how Euretos's capabilities align with the research needs.

                        Euretos Information:
                        {euretos_information}
                        """
                        mail_1 = generate_email(prompt_mail_1)

                    # Reminder 1
                        prompt_reminder_1 = f""" 
                        Based on the previous message sent regarding the capabilities of Euretos in helping their research,
                        please write only the body of the email without salutations based on a shortened version of the previous email.
                    
                        Previous Email:
                        {mail_1}
                        """
                        reminder_1 = generate_email(prompt_reminder_1)

                        # Reminder 2
                        prompt_reminder_2 = f""" 
                        Based on the previous message, please write a shorter version of the previous email focusing more on the research 
                        and less on Euretos capabilities.
                    
                        Previous Email:
                        {mail_1}
                        """
                        reminder_2 = generate_email(prompt_reminder_2)

                        # Search mail
                        prompt_mail_on_search = f"""
                        Please go to https://www.euretos.com/search and describe the search capabilities of Euretos
                        related to the research described in the abstract.
                    
                        Abstract:
                        {abstract}
                        """
                        search_mail = generate_email(prompt_mail_on_search)

                        # Analytics mail
                        prompt_mail_on_analytics = f""" 
                        Please go to https://www.euretos.com/euretos-analytics and describe the analytical capabilities of Euretos.
                        Refer to the research described in the abstract.
                    
                        Abstract:
                        {abstract}
                        """
                        analytics_mail = generate_email(prompt_mail_on_analytics)

                        # Knowledge Graph mail
                        prompt_mail_on_KG = f"""
                        Please go to https://www.euretos.com/knowledge-graph and describe how the knowledge graphs provided by Euretos 
                        can be of use for the research described in the abstract.
                    
                        Abstract:
                        {abstract}
                        """
                        KG_mail = generate_email(prompt_mail_on_KG)

                        # Portal mail
                        prompt_mail_on_portal = f"""
                        Please go to https://www.euretos.com/portal and describe the capabilities of the Euretos portal
                        in relation to the research described in the abstract.
                    
                        Abstract:
                        {abstract}
                        """
                        portal_mail = generate_email(prompt_mail_on_portal)

                        # Store generated emails in the dataframe
                        final_df.loc[index, 'Mail_1'] = mail_1
                        final_df.loc[index, 'Reminder_1'] = reminder_1
                        final_df.loc[index, 'Reminder_2'] = reminder_2
                        final_df.loc[index, 'Search_mail'] = search_mail
                        final_df.loc[index, 'Analytics_mail'] = analytics_mail
                        final_df.loc[index, 'KG_mail'] = KG_mail
                        final_df.loc[index, 'Portal_mail'] = portal_mail

                    # Display the dataframe with generated emails
                    st.write("Generated Emails:")
                    st.write(final_df)

                    # split the Authors column into individual authors per row 
                    final_df_split = final_df['Authors'].str.split(';', expand=True)

                    # Remove any leading/trailing whitespaces and empty strings
                    final_df_split = final_df_split.applymap(lambda x: x.strip() if isinstance(x, str) else x)
                    final_df_split = final_df_split.replace('', None) 

                    # Allow user to download the result as CSV
                    csv = final_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Generated Emails as CSV",
                        data=csv,
                        file_name="generated_emails.csv",
                        mime="text/csv"
                    )

if __name__ == "__main__":
    main()

