import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI
import pyalex
import requests
from pyalex import Works, Authors, Sources, Institutions, Topics, Publishers, Funders
from io import BytesIO

# Set the title and description
st.set_page_config(page_title="Email Generator Tool", page_icon="📧", layout="wide")



# Fetch the OpenAI API key from environment variables
openai_api_key = st.secrets["OPENAI_API_KEY"] #os.getenv('OPENAI_API_KEY')
openai = OpenAI()
# Check if the API key is available
if not openai_api_key:
    raise ValueError("OpenAI API key is not set. Check your environment or GitHub Secrets.")

# Initialize OpenAI API
openai.api_key = openai_api_key


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
    messages = [{"role" : "system", 
                "content": "You are an email assistant for creating body or the paragraphs. Please generate a single or two paragraph body of the email related to the abstract and euretos information provided by the prompt. Ensure the content is in paragraph form without any greetings, numbered sections, or closing remarks and mention the author's work explicitly. Make it more realistic and engaging. Always remember to appreciate the author and mention the abstract title to engage him/her."},
                {"role" : "user", "content": prompt}]

    response = openai.chat.completions.create(
        model="gpt-4o",  # Choose the desired model
        messages=messages
    )
    email = response.choices[0].message.content
    return email

# Streamlit app
def main():
    
    
    st.title("📧 AI-Powered Email Generator")
    st.markdown("This tool helps you generate personalized emails to authors based on research abstracts and Euretos data.")

    # File upload for text information (e.g., Euretos information)
    euretos_file = st.file_uploader("Upload Euretos Information (Text File)", type=["txt"])
    euretos_information = None
    if euretos_file is not None:
        euretos_information = read_from_file(euretos_file)
        st.write("Euretos Information Uploaded Successfully")
        #st.write(euretos_information)

    # Display the form to input OpenAlex link and number of records to fetch
    # Input OpenAlex Link
    openalex_link = st.text_input("Enter OpenAlex Filtered link")
    # Input for the size of data to be fetched
    size_requested = st.number_input("Enter number of records to fetch", min_value=1, value=10, step=1)

    # Input prompts from the user
    prompt_mail_1 = st.text_area("Prompt for First Email")
    prompt_reminder_1 = st.text_area("Prompt for Reminder Email 1")
    prompt_reminder_2 = st.text_area("Prompt for Reminder Email 2")
    prompt_mail_on_search = st.text_area("Prompt for Search Email")
    prompt_mail_on_analytics = st.text_area("Prompt for Analytics Email")
    prompt_mail_on_KG = st.text_area("Prompt for Knowledge Graph Email")
    prompt_mail_on_portal = st.text_area("Prompt for Portal Email")

    if openalex_link and size_requested:
        st.write(f"Fetching {size_requested} records from OpenAlex...")
        fetched_data = fetch_journal_titles_from_openalex(openalex_link, size_requested)
        if len(fetched_data) == 0:
            st.warning("No data found for the given link. Kindly check the link : https://api.openalex.org/works{openalex_link} if there is data showing up!")
        else:
            st.write("Data fetched successfully! Totally fetched records: ", len(fetched_data))
            #st.write(fetched_data)
            euretos_information = euretos_information
            
        # Generate emails based on the abstracts and euretos information
            if euretos_information is not None:
                if st.button("Generate Emails"):
                    st.write("Generating emails... This may take a few minutes  🕒 ")
                    progress_bar = st.progress(0)


                # Loop through each abstract and generate multiple emails
                    for index, row in fetched_data.iterrows():
                        abstract = row['Abstract']
                        authors = row['Authors']

                        mail_1 = generate_email(prompt_mail_1.format(abstract=abstract, euretos_information=euretos_information))
                        
                        mail_1 = generate_email(prompt_mail_1.format(abstract=abstract, euretos_information=euretos_information))
                        
                        # Update progress
                        progress = int((index + 1) / len(fetched_data) * 100)
                        progress_bar.progress(progress)

                        reminder_1 = generate_email(prompt_reminder_1.format(previous_email=mail_1))
                        reminder_2 = generate_email(prompt_reminder_2.format(previous_email=mail_1))
                        search_mail = generate_email(prompt_mail_on_search.format(abstract=abstract))
                        analytics_mail = generate_email(prompt_mail_on_analytics.format(abstract=abstract))
                        KG_mail = generate_email(prompt_mail_on_KG.format(abstract=abstract))
                        portal_mail = generate_email(prompt_mail_on_portal.format(abstract=abstract))

                        reminder_1 = generate_email(prompt_reminder_1.format(previous_email=mail_1))
                        reminder_2 = generate_email(prompt_reminder_2.format(previous_email=mail_1))
                        search_mail = generate_email(prompt_mail_on_search.format(abstract=abstract))
                        analytics_mail = generate_email(prompt_mail_on_analytics.format(abstract=abstract))
                        KG_mail = generate_email(prompt_mail_on_KG.format(abstract=abstract))
                        portal_mail = generate_email(prompt_mail_on_portal.format(abstract=abstract))

                        
                    
               
                        # Show random facts to keep user engaged
                        if index % 3 == 0:
                            st.info("Did you know? You can leverage AI to analyze thousands of research papers in minutes!")
                        # Store generated emails in the dataframe
                        fetched_data.loc[index, 'Mail_1'] = mail_1
                        fetched_data.loc[index, 'Reminder_1'] = reminder_1
                        fetched_data.loc[index, 'Reminder_2'] = reminder_2
                        fetched_data.loc[index, 'Search_mail'] = search_mail
                        fetched_data.loc[index, 'Analytics_mail'] = analytics_mail
                        fetched_data.loc[index, 'KG_mail'] = KG_mail
                        fetched_data.loc[index, 'Portal_mail'] = portal_mail

                    progress_bar.progress(100)
                    st.success("All emails generated successfully!")
                    # load while splitting authors into separate rows
                    st.write("Splitting authors into separate rows...")
                    # splitting the authors and authordids into separate rows for each author
                    df_split = fetched_data.assign(Author=fetched_data['Authors'].str.split(','), 
                                                   AuthorID = fetched_data['Author IDs'].str.split(',')).explode(['Author', 'AuthorID']).reset_index(drop=True)

                    # drop the authors and author ids columns
                    df_split.drop(['Authors', 'Author IDs'], axis=1, inplace=True)
                    # Display the dataframe with generated emails
                    st.write("Generated Emails:")
                    #st.write(df_split)

                    #get today date time and replace : with - to avoid error in file name
                    today = pd.Timestamp.now().strftime('%Y-%m-%d %H-%M-%S')
                    
                    # Allow user to download the result as CSV
                    csv = df_split.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Generated Emails as CSV",
                        data=csv,
                        file_name=f"generated_emails_{today}.csv",
                        mime="text/csv"
                    )

                    # Convert DataFrame to Excel in memory
                    to_excel = BytesIO()
                    with pd.ExcelWriter(to_excel, engine='openpyxl', mode='wb') as writer:
                        df_split.to_excel(writer, index=False)
                    to_excel.seek(0)  # Go back to the start of the stream
                    

                    # Allow user to download the result as Excel
                    st.download_button(
                        label="Download Generated Emails as Excel",
                        data=to_excel.getvalue(),
                        file_name=f"generated_emails_{today}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

if __name__ == "__main__":
    main()

