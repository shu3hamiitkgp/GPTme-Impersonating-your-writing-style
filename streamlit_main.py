import streamlit as st
import pandas as pd
import os
import openai
import re


st.title("GPTme - Impersonating your writing style")

uploaded_file = st.file_uploader("Upload the text file", type="txt")
openai.api_key = ""

def startsWithDate(s):
    pattern = '^\[([0-2][0-9]|(3)[0-1])(\/)(((0)[0-9])|((1)[0-2]))(\/)(\d{2}|\d{4}), ([0-9][0-9]):([0-9][0-9]):([0-9][0-9])\] '
    result = re.match(pattern, s)
    if result:
        return True
    return False

def startsWithAuthor(s):
    patterns = [
        '([\w]+):',                        # First Name
        '([\w]+[\s]+[\w]+):',              # First Name + Last Name
        '^([\w]+[\s]+\(+[\w]+\)+):',       # First Name + Bracket + Last name + Bracket
        '([\w]+[\s]+[\w]+[\s]+\([\w]+\)):',    # First Name + Middle Name + Last Name
        '([+]\d{2} \d{5} \d{5}):',         # Mobile Number (India)
        '([+]\d{2} \d{3} \d{3} \d{4}):',   # Mobile Number (US)
        '([+]\d{2} \d{4} \d{7})'           # Mobile Number (Europe)
    ]
    pattern = '^' + '|'.join(patterns)
    result = re.match(pattern, s)
    if result:
        return True
    return False

def getDataPoint(line):
    # line = 18/06/17, 22:47 - Loki: Why do you have 2 numbers, Banner?
    
    splitLine = line.split('] ') # splitLine = ['18/06/17, 22:47', 'Loki: Why do you have 2 numbers, Banner?']
    
    dateTime = splitLine[0].split('[')[1] # dateTime = '18/06/17, 22:47'
    
    date, time = dateTime.split(', ') # date = '18/06/17'; time = '22:47'
    
    message = ' '.join(splitLine[1:]) # message = 'Loki: Why do you have 2 numbers, Banner?'
    
    if startsWithAuthor(message): # True
        splitMessage = message.split(': ') # splitMessage = ['Loki', 'Why do you have 2 numbers, Banner?']
        author = splitMessage[0] # author = 'Loki'
        message = ' '.join(splitMessage[1:]) # message = 'Why do you have 2 numbers, Banner?'
    else:
        author = None
    return date, time, author, message


def chat(inp, message_history, role="user"):

        # Append the input message to the message history
        message_history.append({"role": role, "content": f"{inp}"})

        # Generate a chat response using the OpenAI API
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message_history
        )

        # Grab just the text from the API completion response
        reply_content = completion.choices[0].message.content

        # Append the generated response to the message history
        message_history.append({"role": "assistant", "content": f"{reply_content}"})

        # Return the generated response and the updated message history
        return reply_content, message_history


    
if uploaded_file is None:
    st.error("Please upload a text file.")
else:
    parsedData = [] # List to keep track of data so it can be used by a Pandas dataframe
    file_contents = uploaded_file.read().decode("utf-8")
    file_string = str(file_contents)            
    messageBuffer = [] # Buffer to capture intermediate output for multi-line messages
    date, time, author = None, None, None # Intermediate variables to keep track of the current message being processed

    for line in file_string.split("\n"): # Loop through each line in the file
        line = line.strip() # Guarding against erroneous leading and trailing whitespaces
        if startsWithDate(line): # If a line starts with a Date Time pattern, then this indicates the beginning of a new message
            if len(messageBuffer) > 0: # Check if the message buffer contains characters from previous iterations
                parsedData.append([date, time, author, ' '.join(messageBuffer)]) # Save the tokens from the previous message in parsedData
            messageBuffer.clear() # Clear the message buffer so that it can be used for the next message
            date, time, author, message = getDataPoint(line) # Identify and extract tokens from the line
            messageBuffer.append(message) # Append message to buffer
        else:
            messageBuffer.append(line) # If a line doesn't start with a Date Time pattern, then it is part of a multi-line message. So, just append to buffer

    df = pd.DataFrame(parsedData, columns=['Date', 'Time', 'Author', 'Message'])
    df['concatenated']= df['Author'] + ': ' + df['Message']
    conversation = df.iloc[5:, 4]
    conversation_upd = '\n'.join(conversation)

    message_history=[]

    if conversation_upd: # Check if conversation_upd is not empty
        qn = st. text_input("Enter the question")
        impersonate = st.selectbox("Impersonate", df['Author'].unique())
        asker = st.selectbox("Ask as", df['Author'].unique())
        type = st.selectbox( "Type", ["Sarcastic", "Normal",  "Anaology"])
        if st.button("Ask"):
            reply, message_history = chat(conversation_upd[1:1000] + '\n' + asker + ": " + qn + " \n Can you create a response in " + impersonate + "'s writing style In " + type + "format?", message_history)
            st.write(reply)