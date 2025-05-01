import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
from decimal import Decimal
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Get environment variables
dynamodb_endpoint = os.environ.get('DYNAMODB_ENDPOINT')

# Configure DynamoDB connection
if dynamodb_endpoint:
    # Local development - more explicit credential disabling
    logger.info(f"Using local DynamoDB endpoint: {dynamodb_endpoint}")
    dynamodb = boto3.resource('dynamodb', 
                              endpoint_url=dynamodb_endpoint,
                              region_name='local',
                              aws_access_key_id='dummy',
                              aws_secret_access_key='dummy',
                              aws_session_token='dummy',
                              config=boto3.session.Config(
                                  signature_version='v4',
                                  retries={'max_attempts': 0},
                                  connect_timeout=1,
                                  read_timeout=1
                              ))
    # Make sure client has the same config
    dynamodb_client = boto3.client('dynamodb',
                              endpoint_url=dynamodb_endpoint,
                              region_name='local', 
                              aws_access_key_id='dummy',
                              aws_secret_access_key='dummy',
                              aws_session_token='dummy')
else:
    # Production AWS
    logger.info("Using AWS DynamoDB service")
    dynamodb = boto3.resource('dynamodb')

# Get DynamoDB client for connection testing
dynamodb_client = boto3.client('dynamodb', 
                              endpoint_url=dynamodb_endpoint,
                              region_name='local',
                              aws_access_key_id='dummy',
                              aws_secret_access_key='dummy') if dynamodb_endpoint else boto3.client('dynamodb')

table_name = 'ClassroomSessions'
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

def get_sessions_by_date(date):
    """Get all sessions for a specific date across all classrooms"""
    try:
        response = table.query(
            IndexName='DateIndex',
            KeyConditionExpression=Key('Date').eq(date)
        )
        items = response.get('Items', [])
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.query(
                IndexName='DateIndex',
                KeyConditionExpression=Key('Date').eq(date),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))
            
        return format_response(200, items)
    except Exception as e:
        logger.error(f"Error getting sessions by date: {str(e)}")
        return format_response(500, {"error": str(e)})

def get_session_by_classroom_and_date(classroom_id, date):
    """Get all sessions for a specific classroom and date"""
    try:
        # First get all sessions for the classroom
        response = table.query(
            KeyConditionExpression=Key('ClassRoomID').eq(classroom_id)
        )
        
        items = response.get('Items', [])
        
        # Filter by date
        filtered_items = [item for item in items if item.get('Date') == date]
        
        if not filtered_items:
            return format_response(404, {"message": "No session found for this date"})
            
        # Return all filtered items instead of just the first one
        return format_response(200, filtered_items)
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        return format_response(500, {"error": str(e)})

def get_classroom_sessions(classroom_id):
    """Get all sessions for a specific classroom"""
    try:
        response = table.query(
            KeyConditionExpression=Key('ClassRoomID').eq(classroom_id)
        )
        items = response.get('Items', [])
        
        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.query(
                KeyConditionExpression=Key('ClassRoomID').eq(classroom_id),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))
            
        return format_response(200, items)
    except Exception as e:
        logger.error(f"Error getting classroom sessions: {str(e)}")
        return format_response(500, {"error": str(e)})

def get_session_by_id(session_id):
    """Get a specific session by its ID"""
    try:
        # This scan is inefficient for large tables - consider adding a GSI for SessionID if needed
        response = table.scan(
            FilterExpression=Key('SessionID').eq(session_id)
        )
        items = response.get('Items', [])
        
        if not items:
            return format_response(404, {"message": "Session not found"})
            
        return format_response(200, items[0])
    except Exception as e:
        logger.error(f"Error getting session by ID: {str(e)}")
        return format_response(500, {"error": str(e)})

def lambda_handler(event, context):
    try:
        http_method = event.get('httpMethod')
        path = event.get('path')
        path_params = event.get('pathParameters', {})
        query_params = event.get('queryStringParameters', {})
        
        logger.info(f"Received request: {http_method} {path}")
        
        # Route the request
        if http_method == 'GET':
            if path == '/sessions/date':
                date = query_params.get('date')
                if not date:
                    return format_response(400, {"error": "Date parameter is required"})
                return get_sessions_by_date(date)
                
            elif path.startswith('/classroom/') and '/sessions' in path:
                classroom_id = path_params.get('classroom_id')
                if not classroom_id:
                    return format_response(400, {"error": "Classroom ID is required"})
                return get_classroom_sessions(classroom_id)
                
            elif path.startswith('/institutes/'):
                classroom_id = path_params.get('classroom_id')
                date = query_params.get('date')
                if not classroom_id or not date:
                    return format_response(400, {"error": "Classroom ID and date are required"})
                return get_session_by_classroom_and_date(classroom_id, date)
                
            elif path.startswith('/session/'):
                session_id = path_params.get('session_id')
                if not session_id:
                    return format_response(400, {"error": "Session ID is required"})
                return get_session_by_id(session_id)
        
        return format_response(404, {"error": "Not found"})
        
    except Exception as e:
        logger.error(f"Error in lambda handler: {str(e)}")
        return format_response(500, {"error": "Internal server error"})