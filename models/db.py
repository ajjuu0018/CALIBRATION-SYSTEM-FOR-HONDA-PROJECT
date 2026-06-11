import mysql.connector

def get_db():
    return mysql.connector.connect(
        host="gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
        user="2ny8YgVnFjBwAuU.root",
        password="2KT8DkzAoEqt8cUj",
        database="calibration_system",
        port=4000
    )