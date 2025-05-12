from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Dict, List, Any
import base64
from email.mime.text import MIMEText
import json

class GmailAnalytics:
    def __init__(self, credentials):
        self.service = build('gmail', 'v1', credentials=credentials)

    def get_email_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get email metrics for the specified number of days"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = f'after:{start_date.strftime("%Y/%m/%d")} before:{end_date.strftime("%Y/%m/%d")}'
        
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=500
            ).execute()
            
            messages = results.get('messages', [])
            
            metrics = {
                'total_emails': len(messages),
                'senders': {},
                'subjects': {},
                'time_distribution': {},
                'email_size_distribution': {
                    'small': 0,  # < 1MB
                    'medium': 0,  # 1MB - 5MB
                    'large': 0   # > 5MB
                }
            }
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me',
                    id=message['id'],
                    format='metadata'
                ).execute()
                
                headers = msg['payload']['headers']
                date = None
                sender = None
                subject = None
                
                for header in headers:
                    if header['name'] == 'From':
                        sender = header['value']
                    elif header['name'] == 'Subject':
                        subject = header['value']
                    elif header['name'] == 'Date':
                        date = header['value']
                
                if sender:
                    metrics['senders'][sender] = metrics['senders'].get(sender, 0) + 1
                
                if subject:
                    metrics['subjects'][subject] = metrics['subjects'].get(subject, 0) + 1
                
                if date:
                    try:
                        hour = datetime.strptime(date, '%a, %d %b %Y %H:%M:%S %z').hour
                        metrics['time_distribution'][hour] = metrics['time_distribution'].get(hour, 0) + 1
                    except ValueError:
                        # Handle different date formats
                        pass
                
                # Estimate size based on payload size
                size = msg.get('sizeEstimate', 0)
                if size < 1024 * 1024:  # < 1MB
                    metrics['email_size_distribution']['small'] += 1
                elif size < 5 * 1024 * 1024:  # 1MB - 5MB
                    metrics['email_size_distribution']['medium'] += 1
                else:  # > 5MB
                    metrics['email_size_distribution']['large'] += 1
            
            return metrics
            
        except Exception as e:
            raise Exception(f"Error fetching email metrics: {str(e)}")

    def get_top_senders(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get top email senders for the specified number of days"""
        metrics = self.get_email_metrics(days)
        senders = metrics['senders']
        return [
            {'sender': sender, 'count': count}
            for sender, count in sorted(
                senders.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        ]

    def get_time_distribution(self, days: int = 30) -> Dict[str, int]:
        """Get email distribution by hour of the day"""
        metrics = self.get_email_metrics(days)
        return metrics['time_distribution']
    
    def send_email(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """Send an email"""
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            message_body = {'raw': raw_message}
            
            send_message = self.service.users().messages().send(
                userId='me',
                body=message_body
            ).execute()
            
            return {"message_id": send_message['id'], "status": "sent"}
            
        except Exception as e:
            raise Exception(f"Error sending email: {str(e)}")

    def reply_to_email(self, message_id: str, reply_body: str) -> Dict[str, Any]:
        """Reply to an existing email"""
        try:
            # Get the original message
            original = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='metadata'
            ).execute()
            
            headers = original['payload']['headers']
            to = None
            subject = None
            original_subject = None
            
            for header in headers:
                if header['name'] == 'From':
                    to = header['value']
                elif header['name'] == 'Subject':
                    original_subject = header['value']
                    if not original_subject.startswith('Re: '):
                        subject = f"Re: {original_subject}"
                    else:
                        subject = original_subject
            
            if not to or not subject:
                raise Exception("Could not determine recipient or subject")
            
            return self.send_email(to, subject, reply_body)
            
        except Exception as e:
            raise Exception(f"Error replying to email: {str(e)}")