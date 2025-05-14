import sys
import subprocess

# Check if pymongo is installed, install if needed
try:
    import pymongo
    from pymongo import MongoClient
except ImportError:
    print("Installing pymongo...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pymongo"])
    import pymongo
    from pymongo import MongoClient

from get_who_data import get_who_covid19
from datetime import datetime

# Connect to MongoDB
# Replace with your actual MongoDB connection string if needed
try:
    client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
    # Test the connection
    client.server_info()
    print("Successfully connected to MongoDB")
except pymongo.errors.ServerSelectionTimeoutError:
    print("Error: Could not connect to MongoDB server. Make sure MongoDB is running.")
    sys.exit(1)
except pymongo.errors.ConnectionFailure:
    print("Error: MongoDB connection failed. Please check your connection string.")
    sys.exit(1)

# Create database
db = client['WHO_covid19']

# Create time series collections
collections_config = [
    {
        'name': 'WHO_lastweek_positivity_world',
        'time_field': 'date',
        'data_key': 'WHO_weekly_positivity_rate_world_latest'
    },
    {
        'name': 'WHO_lastweek_positivity_countries',
        'time_field': 'date',
        'data_key': 'WHO_weekly_positivity_rate_countries_latest'
    },
    {
        'name': 'WHO_last28d_variants_prevalence',
        'time_field': 'date',
        'data_key': 'WHO_28d_variants_prevalence_latest'
    },
    {
        'name': 'GISAID_last28d_variants_submitted',
        'time_field': 'date',
        'data_key': 'GISAID_28d_variants_submitted_latest'
    },
    {
        'name': 'WHO_history_variants_prevalence',
        'time_field': 'date',
        'data_key': 'WHO_variants_prevalence_history'
    },
    {
        'name': 'WHO_history_positivity_world',
        'time_field': 'date',
        'data_key': 'WHO_weekly_positivity_rate_world_history'
    }
]

# Create time series collections and insert data
def setup_collections():
    # Get WHO data
    try:
        who_data = get_who_covid19()
        print("Successfully retrieved WHO COVID-19 data")
    except Exception as e:
        print(f"Error retrieving WHO data: {str(e)}")
        sys.exit(1)
    
    # Set up each collection
    for config in collections_config:
        collection_name = config['name']
        time_field = config['time_field']
        data_key = config['data_key']
        
        print(f"\nSetting up collection: {collection_name}")
        
        # Drop collection if it exists
        if collection_name in db.list_collection_names():
            db[collection_name].drop()
            print(f"Dropped existing collection: {collection_name}")
        
        try:
            # Create time series collection
            meta_field = None
            sample_data = who_data[data_key]
            # Check if data contains variant field for metaField
            if isinstance(sample_data, list) and sample_data and 'variant' in sample_data[0]:
                meta_field = 'variant'
            
            db.create_collection(
                collection_name,
                timeseries={
                    'timeField': time_field,
                    'metaField': meta_field,
                    'granularity': 'hours'
                }
            )
            print(f"Created time series collection: {collection_name}")
            
            # Insert data
            data = who_data[data_key]
            if isinstance(data, list):
                if data:
                    # Convert string dates to datetime objects if needed
                    for item in data:
                        if isinstance(item[time_field], str):
                            try:
                                item[time_field] = datetime.fromisoformat(item[time_field].replace('Z', '+00:00'))
                            except ValueError:
                                # Keep original if conversion fails
                                pass
                    
                    db[collection_name].insert_many(data)
                    print(f"Inserted {len(data)} documents into {collection_name}")
            else:
                # Convert string date to datetime object if needed
                if isinstance(data[time_field], str):
                    try:
                        data[time_field] = datetime.fromisoformat(data[time_field].replace('Z', '+00:00'))
                    except ValueError:
                        # Keep original if conversion fails
                        pass
                
                db[collection_name].insert_one(data)
                print(f"Inserted 1 document into {collection_name}")
        except Exception as e:
            print(f"Error setting up collection {collection_name}: {str(e)}")

# Verify collections and display sample data
def verify_collections():
    print("\n" + "="*50)
    print("VERIFICATION")
    print("="*50)
    
    # Check if collections were created
    collection_names = db.list_collection_names()
    print(f"Collections in database: {', '.join(collection_names)}")
    
    # Display sample data from each collection
    for collection_name in collection_names:
        print(f"\nSample data from {collection_name}:")
        try:
            # Get and display first document
            sample = db[collection_name].find_one()
            if sample:
                # Remove _id field for cleaner output
                if '_id' in sample:
                    del sample['_id']
                print(sample)
            else:
                print("No data found in collection")
                
            # Display count
            count = db[collection_name].count_documents({})
            print(f"Total documents: {count}")
        except Exception as e:
            print(f"Error retrieving sample data: {str(e)}")

if __name__ == '__main__':
    setup_collections()
    verify_collections()
    print("\nMongoDB time series collections setup complete!") 