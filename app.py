import streamlit as st
import pandas as pd
import os
from dotenv import load_dotenv
from openai import OpenAI

# set openai api key
os.environ['OPENAI_API_KEY'] = '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'
# Load environment variables from .env file
load_dotenv()
openai = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
# Initialize OpenAI API
# openai_api_key = os.getenv('OPEN_AI_KEY')
# openai.api_key = openai_api_key

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

    # File upload for Excel (containing abstracts and other research details)
    excel_file = st.file_uploader("Upload Research Data (Excel File)", type=["xlsx", "csv"])
    if excel_file is not None:
        if excel_file.name.endswith('.csv'):
            scopus_df = pd.read_csv(excel_file)
        else:
            scopus_df = pd.read_excel(excel_file)
        
        final_df = scopus_df[['Authors', 'Author full names', 'Abstract']]
        st.write("Excel Data Uploaded Successfully")
        st.write(final_df)

        # Generate emails based on the abstracts and euretos information
        if euretos_information is not None:
            if st.button("Generate Emails"):
                st.write("Generating emails...")

                # Loop through each abstract and generate multiple emails
                for index, row in final_df.iterrows():
                    abstract = row['Abstract']
                    authors = row['Authors']

                    # First mail prompt
                    prompt_mail_1 = f"""
                    Below are two pieces of text. The first is the abstract of an article written by {authors} 
                    on Alzheimer. The second is information about www.euretos.com, a platform providing data-driven 
                    insights and their capabilities when it comes to Alzheimer's disease. Please highlight the capabilities 
                    of Euretos in helping their research specifically and provide only the core content as output.
                    
                    Abstract:
                    {abstract}
                    
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
