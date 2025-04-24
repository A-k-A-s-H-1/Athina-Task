import json
import datetime


def lambda_handler(event,context):
    
    current_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    query_params=event.get('queryStringParameters',{}) or {}
    
    timezone=query_params.get("timezone","UTC")
    
    return {
        "statusCode":200,
        "body":json.dumps({
            "time":current_time,
            "timezone":timezone,
            "request_id":context.aws_request_id if context else "local-development"
        }),
        "headers":{
            "Content-Type":"application/json"
        }
    }