import json
import requests


def lambda_handler(event, context):
   
    query_params=event.get('queryStringParameters',{}) or {}
    name=query_params.get('name','world')
    
    try:
        ip=requests.get('http://checkip.amazonaws.com/',timeout=3)
        location=ip.text.replace('\n',"")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching IP:{e}")
        location="unknown"
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": f"hello,{name}!",
            "location":location,
            "request_id":context.aws_request_id if context else "local-development"
        }),
        "headers":{
            "Content-Type":"application/json"
        }
    }
