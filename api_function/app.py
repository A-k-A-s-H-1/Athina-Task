import json
import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get environment variables
dynamodb_endpoint = os.environ.get('DYNAMODB_ENDPOINT')
aws_region_name = os.environ.get('AWS_REGION_NAME')
aws_access_key_id = os.environ.get('AWS_ACCESS_KEY_ID')   
aws_secret_access_key = os.environ.get('AWS_SECRET_ACCESS_KEY')

# Configure DynamoDB connection
if dynamodb_endpoint:
    # Local development configuration
    logger.info(f"Using local DynamoDB endpoint: {dynamodb_endpoint}")
    dynamodb = boto3.resource('dynamodb', 
                              endpoint_url=dynamodb_endpoint,
                              region_name=aws_region_name,
                              aws_access_key_id=aws_access_key_id,
                              aws_secret_access_key=aws_secret_access_key,
                              config=boto3.session.Config(
                                  signature_version='v4',
                                  retries={'max_attempts': 0},
                                  connect_timeout=1,
                                  read_timeout=1
                              ))
else:
    # Production AWS configuration
    logger.info("Using AWS DynamoDB service")
    dynamodb = boto3.resource('dynamodb')

table_name = 'ClassroomSessions'  # Table with composite key: ClassRoomID_Date
table = dynamodb.Table(table_name)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

def format_response(status_code, body):
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body, cls=DecimalEncoder)
    }

def get_session_by_classroom_and_date(classroom_id, date):
    """Get all sessions for a specific classroom and date using composite key"""
    try:
        # Create the composite key format: classroomID_date
        composite_key = f"{classroom_id}_{date}"
        
        # Query directly using the composite key as partition key
        response = table.query(
            KeyConditionExpression=Key('ClassRoomID_Date').eq(composite_key)
        )
        
        items = response.get('Items', [])
        
        if not items:
            return format_response(404, {"message": "No session found for this date"})
            
        # Return all items from the query
        return format_response(200, items)
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        return format_response(500, {"error": str(e)})

def lambda_handler(event, context):
    try:
        http_method = event.get('httpMethod')
        path = event.get('path')
        path_params = event.get('pathParameters', {})
        query_params = event.get('queryStringParameters', {})
        
        logger.info(f"Received request: {http_method} {path}")
        
        # Only handle the /institutes endpoint
        if http_method == 'GET' and path.startswith('/institutes/'):
            classroom_id = path_params.get('classroom_id')
            date = query_params.get('date')
            
            if not classroom_id or not date:
                return format_response(400, {"error": "Classroom ID and date are required"})
                
            return get_session_by_classroom_and_date(classroom_id, date)
        
        return format_response(404, {"error": "Not found"})
        
    except Exception as e:
        logger.error(f"Error in lambda handler: {str(e)}")
        return format_response(500, {"error": "Internal server error"})