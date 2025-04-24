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
    # Local development
    logger.info(f"Using local DynamoDB endpoint: {dynamodb_endpoint}")
    dynamodb = boto3.resource('dynamodb', 
                              endpoint_url=dynamodb_endpoint,
                              region_name='local',
                              aws_access_key_id='dummy',
                              aws_secret_access_key='dummy')
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
        return super(DecimalEncoder, self).default(obj)

def test_dynamodb_connection():
    """Test the connection to DynamoDB and return connection status information."""
    try:
        # List tables to verify connection
        logger.info("Testing DynamoDB connection...")
        table_list = dynamodb_client.list_tables(Limit=10)
        tables = table_list.get('TableNames', [])
        
        # Check if our table exists
        table_exists = table_name in tables
        
        # If table exists, try to describe it
        table_details = None
        if table_exists:
            table_info = dynamodb_client.describe_table(TableName=table_name)
            table_details = {
                'name': table_info['Table']['TableName'],
                'status': table_info['Table']['TableStatus'],
                'item_count': table_info['Table'].get('ItemCount', 0),
                'creation_date': str(table_info['Table']['CreationDateTime']),
                'key_schema': table_info['Table']['KeySchema']
            }
        
        return {
            'connection_successful': True,
            'endpoint': dynamodb_endpoint or 'AWS DynamoDB service',
            'tables_found': len(tables),
            'tables': tables,
            'table_exists': table_exists,
            'table_details': table_details if table_exists else None
        }
    except Exception as e:
        logger.error(f"DynamoDB connection test failed: {str(e)}")
        return {
            'connection_successful': False,
            'endpoint': dynamodb_endpoint or 'AWS DynamoDB service',
            'error': str(e)
        }

def lambda_handler(event, context):
    try:
        # Test the DynamoDB connection first
        connection_result = test_dynamodb_connection()
        logger.info(f"DynamoDB connection test: {json.dumps(connection_result)}")
        
        # If connection failed, return error immediately
        if not connection_result['connection_successful']:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Failed to connect to DynamoDB',
                    'details': connection_result
                })
            }
        
        # If table doesn't exist, return error
        if not connection_result.get('table_exists', False):
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': f"Table '{table_name}' does not exist",
                    'available_tables': connection_result.get('tables', []),
                    'connection_details': connection_result
                })
            }
        
        # Log the entire event for debugging
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Get HTTP method from event
        http_method = event.get('httpMethod', '')
        path_parameters = event.get('pathParameters', {}) or {}
        query_parameters = event.get('queryStringParameters', {}) or {}
        
        logger.info(f"HTTP Method: {http_method}")
        logger.info(f"Path Parameters: {path_parameters}")
        logger.info(f"Query Parameters: {query_parameters}")
        
        if http_method == 'GET':
            # Rest of your code remains the same...
            # For brevity, I'm only including a simple scan example
            
            try:
                # Try a sample scan with a very small limit to test access
                logger.info("Performing test scan with limit 1")
                test_scan = table.scan(Limit=1)
                scan_successful = True
                sample_items = test_scan.get('Items', [])
                logger.info(f"Test scan successful, found {len(sample_items)} items")
            except Exception as scan_error:
                logger.error(f"Test scan failed: {str(scan_error)}")
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'error': 'Connected to DynamoDB but failed to scan table',
                        'details': str(scan_error),
                        'connection_details': connection_result
                    })
                }
            
            # Return success with connection details
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'DynamoDB connection successful!',
                    'connection_details': connection_result,
                    'sample_data': sample_items if sample_items else "No items found in table"
                }, cls=DecimalEncoder)
            }
        
        # Default response for unsupported methods
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Unsupported method: {http_method}',
                'connection_details': connection_result
            })
        }
    
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'trace': traceback.format_exc()
            })
        }