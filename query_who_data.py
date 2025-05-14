import sys
import argparse
import json
from datetime import datetime, timedelta
import pprint

# Check if pymongo is installed, install if needed
try:
    import pymongo
    from pymongo import MongoClient
except ImportError:
    import subprocess
    print("Installing pymongo...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymongo"])
    import pymongo
    from pymongo import MongoClient

# MongoDB connection
try:
    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    # Test connection
    client.server_info()
except pymongo.errors.ServerSelectionTimeoutError:
    print("Error: Could not connect to MongoDB server. Make sure MongoDB is running.")
    sys.exit(1)
except pymongo.errors.ConnectionFailure:
    print("Error: MongoDB connection failed. Please check your connection string.")
    sys.exit(1)

# Use WHO_covid19 database
db = client['WHO_covid19']

def list_collections():
    """List all collections in the database"""
    collections = db.list_collection_names()
    if not collections:
        print("No collections found in the WHO_covid19 database.")
        return
    
    print("\nAvailable collections:")
    for i, coll in enumerate(collections, 1):
        count = db[coll].count_documents({})
        print(f"{i}. {coll} ({count} documents)")

def get_latest(collection_name):
    """Get latest data from a collection"""
    if collection_name not in db.list_collection_names():
        print(f"Collection '{collection_name}' not found.")
        return
    
    # Sort by date descending and get first record
    result = list(db[collection_name].find().sort("date", -1).limit(1))
    
    if not result:
        print(f"No data found in collection '{collection_name}'")
        return
    
    print(f"\nLatest data from {collection_name}:")
    for doc in result:
        # Convert ObjectId to string for JSON serialization
        doc["_id"] = str(doc["_id"])
        pprint.pprint(doc)

def get_variants(days=28):
    """Get variant prevalence data for the specified days"""
    collection_name = 'WHO_history_variants_prevalence'
    
    if collection_name not in db.list_collection_names():
        print(f"Collection '{collection_name}' not found.")
        return
    
    # Calculate the date threshold
    threshold_date = datetime.now() - timedelta(days=days)
    
    # Query for variants after the threshold date
    pipeline = [
        {"$match": {"date": {"$gte": threshold_date}}},
        {"$sort": {"date": -1, "variant": 1}},
        {"$group": {
            "_id": "$variant",
            "latest_date": {"$first": "$date"},
            "latest_prevalence": {"$first": "$prevalence"},
            "data_points": {"$sum": 1}
        }},
        {"$sort": {"latest_prevalence": -1}}
    ]
    
    result = list(db[collection_name].aggregate(pipeline))
    
    if not result:
        print(f"No variant data found in the last {days} days")
        return
    
    print(f"\nVariant prevalence data from the last {days} days:")
    for doc in result:
        variant = doc["_id"]
        prevalence = doc["latest_prevalence"]
        date = doc["latest_date"].strftime("%Y-%m-%d")
        print(f"{variant}: {prevalence} (as of {date})")

def get_countries_by_positivity(limit=10, ascending=False):
    """Get countries sorted by positivity rate"""
    collection_name = 'WHO_lastweek_positivity_countries'
    
    if collection_name not in db.list_collection_names():
        print(f"Collection '{collection_name}' not found.")
        return
    
    # Sort direction (1 for ascending, -1 for descending)
    sort_direction = 1 if ascending else -1
    
    # Get most recent data
    latest_data = list(db[collection_name].find().sort("date", -1).limit(1))
    
    if not latest_data:
        print("No country positivity rate data found.")
        return
    
    # Get the date of the most recent data
    latest_date = latest_data[0]["date"]
    
    # Query countries for that date, sorted by positivity rate
    pipeline = [
        {"$match": {"date": latest_date}},
        {"$addFields": {
            # Convert string percentage to numeric value for sorting
            "numeric_rate": {
                "$toDouble": {
                    "$replaceAll": {
                        "input": "$covid19_positivity_rate",
                        "find": "%",
                        "replacement": ""
                    }
                }
            }
        }},
        {"$sort": {"numeric_rate": sort_direction}},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "country": 1,
            "covid19_positivity_rate": 1
        }}
    ]
    
    result = list(db[collection_name].aggregate(pipeline))
    
    if not result:
        print("No country positivity rate data found.")
        return
    
    order = "lowest" if ascending else "highest"
    print(f"\nCountries with {order} COVID-19 positivity rates:")
    for i, doc in enumerate(result, 1):
        country = doc["country"]
        rate = doc["covid19_positivity_rate"]
        print(f"{i}. {country}: {rate}")

def get_positivity_history(limit=10):
    """Get historical positivity rate data for the world"""
    collection_name = 'WHO_history_positivity_world'
    
    if collection_name not in db.list_collection_names():
        print(f"Collection '{collection_name}' not found.")
        return
    
    # Get the most recent data points
    result = list(db[collection_name].find().sort("date", -1).limit(limit))
    
    if not result:
        print("No positivity rate history data found.")
        return
    
    # Display the data
    print(f"\nHistorical COVID-19 positivity rates for the world (last {limit} weeks):")
    for doc in sorted(result, key=lambda x: x["date"]):
        date = doc["date"].strftime("%Y-%m-%d")
        specimens_tested = doc.get("Number_of_specimens_tested_for_SARS-CoV-2", "N/A")
        positive_tests = doc.get("Number_of_specimens_tested_Positive_for_SARS-CoV-2", "N/A")
        positivity_rate = doc.get("Percentage_of_samples_testing_positive_for_SARS-CoV-2", "N/A")
        
        print(f"{date}: {positivity_rate} ({positive_tests}/{specimens_tested})")

def main():
    parser = argparse.ArgumentParser(description='Query WHO COVID-19 data from MongoDB')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List collections command
    subparsers.add_parser('list', help='List all collections')
    
    # Get latest data command
    latest_parser = subparsers.add_parser('latest', help='Get latest data from a collection')
    latest_parser.add_argument('collection', help='Collection name')
    
    # Get variant data command
    variant_parser = subparsers.add_parser('variants', help='Get variant prevalence data')
    variant_parser.add_argument('--days', type=int, default=28, help='Number of days to include (default: 28)')
    
    # Get country positivity rates command
    countries_parser = subparsers.add_parser('countries', help='Get countries by positivity rate')
    countries_parser.add_argument('--limit', type=int, default=10, help='Number of countries to display (default: 10)')
    countries_parser.add_argument('--ascending', action='store_true', help='Sort in ascending order (lowest first)')
    
    # Get positivity rate history command
    positivity_parser = subparsers.add_parser('positivity-history', help='Get historical positivity rate data')
    positivity_parser.add_argument('--limit', type=int, default=10, help='Number of weeks to display (default: 10)')
    
    args = parser.parse_args()
    
    if args.command == 'list' or not args.command:
        list_collections()
    elif args.command == 'latest':
        get_latest(args.collection)
    elif args.command == 'variants':
        get_variants(args.days)
    elif args.command == 'countries':
        get_countries_by_positivity(args.limit, args.ascending)
    elif args.command == 'positivity-history':
        get_positivity_history(args.limit)

if __name__ == '__main__':
    main() 