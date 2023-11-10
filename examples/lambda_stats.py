"""This file powers the AWS Lambda serverless function for accepting
   anonymous TRD statistics. It requires an AWS DynamoDB table to
   store all of the data. Logs are generated automatically and stored
   in AWS CloudWatch.
"""

import boto3
import logging
import json
import traceback
from base64 import b64decode
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, And
from decimal import Decimal

db = boto3.resource("dynamodb")

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    getpost = event["requestContext"]["http"]["method"].lower()

    # check if POST
    if getpost == "post":
        try:
            # Parse POST data
            logger.info("BODY: {}".format(event["body"]))
            jData = json.loads(event["body"], parse_float=Decimal)

            # Safety checking
            jDataKeys = jData.keys()
            if not ("uuid" in jDataKeys and "cycle" in jDataKeys):
                return {"statusCode": 400, "body": "Missing required parameters"}

            # Convert stats dictionary to "row" for DB
            row = {}
            row["uuid"] = jData["uuid"]
            row["cycle"] = int(jData["cycle"])

            for k in jDataKeys:
                if k == "uuid" or k == "cycle":
                    continue
                row[k] = jData[k]

            # Save to dynamodb
            table = db.Table("trd_statistics")
            table.put_item(Item=row)

            logger.info("Saved stats for {}".format(row["uuid"]))

            return {"statusCode": 200, "body": "OK"}

        except ClientError as e:
            logger.error("Client Error: {}".format(str(e)))

        except Exception as e:
            tb = traceback.format_exc()
            logger.error("Generic Exception: {}".format(str(e)))
            logger.error("Generic Exception Trace: {}".format(tb))

        # Only exceptions make it here
        return {"statusCode": 500, "body": "Generic Error\n"}

    # else GET, display stats
    elif getpost == "get":
        try:
            table = db.Table("trd_statistics")
            results = []
            scan_kwargs = {}
            filter = ""

            # Get URL parameters, if provided
            if "queryStringParameters" in event.keys():
                ks = event["queryStringParameters"].keys()

                # Required
                if "network" in ks:
                    network = event["queryStringParameters"]["network"]
                    filter = Key("network").eq(network)
                else:
                    return {"statusCode": "500", "body": "Missing Network"}

                # Optional
                if "cycle" in ks:
                    cycle = event["queryStringParameters"]["cycle"]
                    filter = filter & Key("cycle").eq(Decimal(cycle))

                scan_kwargs["FilterExpression"] = filter

            else:
                return {"statusCode": "500", "body": "Missing Network"}

            # Must paginate through results received from dynamo
            done = False
            start_key = None

            while not done:
                if start_key:
                    scan_kwargs["ExclusiveStartKey"] = start_key
                response = table.scan(**scan_kwargs)
                results.extend(response.get("Items", []))
                start_key = response.get("LastEvaluatedKey", None)
                done = start_key is None

            # Convert 'Decimal' to actual JSON number
            postResults = replace_decimals(results)
            return {
                "Access-Control-Allow-Origin": "*",
                "statusCode": "200",
                "body": json.dumps(postResults),
            }

        except Exception as r:
            tb = traceback.format_exc()
            logger.error("GET Exception: {}".format(str(r)))
            logger.error("GET Exception Trace: {}".format(tb))
            return {
                "Access-Control-Allow-Origin": "*",
                "statusCode": "500",
                "body": "Exception Caught: {}".format(str(r)),
            }

    # else, something else
    return {
        "Access-Control-Allow-Origin": "*",
        "statusCode": 200,
        "body": "Thanks for playing!\n",
    }


def replace_decimals(obj):
    if isinstance(obj, Decimal):
        if obj % 1 == 0:
            return int(obj)
        else:
            return float(obj)
    else:
        return obj
