# this application will fetch crypto currency data from coingeko site
# find top 10 to sell 
# find bottom 10 to buy
# send mail to me everyday at 8AM

# task
# 1. download the datasets from the coingeko
# 2. send mail
# 3. schedule task 8am

# importing dependencies
import requests
import pandas as pd
import schedule
import time
import logging
import os
from datetime import datetime
import smtplib


from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
import email.encoders
from dotenv import load_dotenv
from sqlalchemy import create_engine




load_dotenv()
#===================logging info=================#
logging.basicConfig(
    filename='crypto_app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

#====================MYSQL CONNECTION=============#

def get_mysql_engine():
    user = os.getenv("MYSQL_USER")
    password = os.getenv("MYSQL_PASSWORD")
    host = os.getenv("MYSQL_HOST")
    db = os.getenv("MYSQL_DB")

    engine = create_engine(
        f"mysql+pymysql://{user}:{password}@{host}/{db}"
    )

    return engine




#==========================MAIN FUNCTION===============#

def send_mail(subject, body, filename):
    
    # smtp_server = "smpt.google.com"
    sender_mail = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    receiver_mail = "mallikarjunvhvh@gmail.com"
    
    
    # compose the mail
    message = MIMEMultipart()
    message['From'] = sender_mail
    message['To'] = receiver_mail
    message ['Subject'] = subject
    
    # attaching body
    message.attach(MIMEText(body, 'plain'))
    
    
    # attach csv file
    with open(filename, 'rb') as file:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(file.read())
        email.encoders.encode_base64(part)  # This line encodes the file in base64 (optional)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        message.attach(part)
        
        
    # start sever
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls() #secure connection
            server.login(sender_mail, email_password) #login
            
            # sending mail
            server.sendmail(sender_mail, receiver_mail, message.as_string())
            logging.info("Email sent successfully")

        
    except Exception as e:
        logging.error(f"Unable to send email: {e}")


# getting crypto data
def get_crypto_data():
    # API information
    logging.info("Starting crypto data fetch job")

    url = 'https://api.coingecko.com/api/v3/coins/markets'
    param = {
        'vs_currency' : 'usd',
        'order' : 'market_cap_desc',
        'per_page': 250,
        'page': 1
    }

    # sending requests
    response = requests.get(url, params=param)

    if response.status_code == 200:
        logging.info("API connection successful")
        
        # storing the response into data
        data = response.json()
        
        # creating df dataframe
        df = pd.DataFrame(data)
        
        # selecting only columns we need -data cleaning
        df = df[[
            'id','current_price', 'market_cap', 'price_change_percentage_24h',
            'high_24h', 'low_24h','ath', 'atl',
        ]]
    
        #creating new columns
        today =  datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
        df['time_stamp'] = today
        
        # getting top 10
        top_negative_10 = df.nsmallest(10, 'price_change_percentage_24h')
        
        # # positive top
        top_positive_10 = df.nlargest(10, 'price_change_percentage_24h')
        
        # saving the data
        file_name = f'crypto_data {today}.csv'
        df.to_csv(file_name, index=False)
        
        logging.info(f"CSV file saved: {file_name}")
        
        #save to mysql
        
        try:
            engine = get_mysql_engine()
            df.to_sql(
                'crypto_prices',
                con=engine,
                if_exists='append',
                index=False
            )
            logging.info("Data saved to MySQL database")
        except Exception as e:
            logging.error(f"MySQL insert failed: {e}")
        
        # call email function to send the reports
        
        subject = f"Top 10 crypto currency data to invest for {today}"
        body = f"""
        Good Morning!\n\n
        
        Your crypt reports is here!\n\n
        
        Top 10 crypto with highest price increase in last 24 hour!\n
        {top_positive_10}\n\n\n
        
        
        Top 10 crypto with highest price decrease in last 24 hour!\n
        {top_negative_10}\n\n\n
        
        Attached 250 plus crypto currency lattest reports\n
        
        
        Regards!\n
        See you tomorrow!\n
        Your crypto python application    
        """
        
        # sending mail
        send_mail(subject, body, file_name)    
        
    else:
        logging.error(f"API connection failed with status code {response.status_code}")

    
    
    
    
# this get executed only if we run this function
if __name__ == '__main__':
    # call the function
    logging.info("Crypto application started")
    # sheduling the task at 8AM
    # schedule.every().day.at('08:00').do(get_crypto_data)
    schedule.every(20).seconds.do(get_crypto_data)
    
    
    while True:
        logging.info("Waiting for scheduled job...")
        schedule.run_pending()
        time.sleep(5)