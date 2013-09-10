import smtplib
import email.Message
import os.path
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email import Encoders

SPARK_EMAILER = None

class Emailer:
    __slots__ = ("host", "port", "username", "password", "myemail")
    
    def __init__(self, host, port, username, password, myemail):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.myemail = myemail
        global SPARK_EMAILER
        SPARK_EMAILER = self
        
    def getMailServer(self):
        mailServer = smtplib.SMTP(self.host, self.port)
        if self.username != "":
            mailServer.login(self.username, self.password)
        return mailServer
    
    def sendEmail(self, to, cc, bcc, subject, text, attachments):
        message = MIMEMultipart()
        for t in to:
            message["To"] = t
        for c in cc:
            message["Cc"] = c
        for b in bcc:
            message["Bcc"] = b
        message["From"] = self.myemail
        message["Subject"] = subject
        mText = MIMEText(text)
        mText.add_header("Content-Disposition", "inline")
        message.attach(mText)

        for file in attachments:
            part = MIMEBase('application', "octet-stream")
            part.set_payload( open(file,"rb").read() )
            Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="%s"'%os.path.basename(file))
            message.attach(part)


        server = self.getMailServer()
        server.sendmail(self.myemail, to + cc + bcc, message.as_string())
        server.quit()
        
def send_email(to, cc, bcc, subject, text, attachments):
    global SPARK_EMAILER
    if SPARK_EMAILER is None:
        print "ERROR: You have not configured the Email Sender..."
        return None
    SPARK_EMAILER.sendEmail(to, cc, bcc, subject, text, attachments)

