import os
import mysql.connector

def get_db():
    return mysql.connector.connect(
        host=os.getenv("gateway01.ap-southeast-1.prod.aws.tidbcloud.com"),
        user=os.getenv("2ny8YgVnFjBwAuU.root"),
        password=os.getenv("2KT8DkzAoEqt8cUj"),
        database=os.getenv("calibration_system"),
        port=int(os.getenv("4000", 4000))
    )